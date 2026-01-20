"""Behavioral tests for parallel tool execution.

Tests verify user-facing behavior:
- Parallel reads execute concurrently
- Write operations execute sequentially
- Mixed read/write operations batch correctly
- Errors and permission denials are handled
- Results maintain order
"""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Any
from unittest.mock import MagicMock

import pytest

from chapgent.core.parallel import execute_tools_parallel
from chapgent.tools.base import ToolCategory, ToolDefinition, ToolRisk

# =============================================================================
# Test Fixtures
# =============================================================================


@dataclass
class MockToolUseBlock:
    """Mock for ToolUseBlock from providers."""

    id: str
    name: str
    input: dict[str, Any]


def make_tool_use(name: str, **kwargs: Any) -> Any:
    """Create a mock tool use block."""
    return MockToolUseBlock(id=f"{name}_id", name=name, input=kwargs)


def make_tool_def(
    name: str,
    return_value: str = "success",
    read_only: bool = False,
    func: Any = None,
) -> ToolDefinition:
    """Create a mock tool definition."""

    async def mock_func(**kwargs: Any) -> str:
        return return_value

    return ToolDefinition(
        name=name,
        description=f"Mock {name} tool",
        input_schema={"type": "object", "properties": {}},
        risk=ToolRisk.LOW,
        category=ToolCategory.FILESYSTEM,
        function=func or mock_func,
        read_only=read_only,
        cacheable=read_only,
    )


def make_mock_agent(allowed: bool = True, cached_result: str | None = None) -> MagicMock:
    """Create a mock agent with permissions and cache."""
    agent = MagicMock()

    async def check_permission(**kwargs: Any) -> bool:
        return allowed

    agent.permissions = MagicMock()
    agent.permissions.check = check_permission

    async def cache_get(tool_name: str, args: dict[str, Any], cacheable: bool = True) -> str | None:
        if not cacheable:
            return None
        return cached_result

    async def cache_set(tool_name: str, args: dict[str, Any], result: str, cacheable: bool = True) -> None:
        pass

    agent.tool_cache = MagicMock()
    agent.tool_cache.get = cache_get
    agent.tool_cache.set = cache_set

    return agent


# =============================================================================
# Parallel Reads - Non-conflicting read operations execute concurrently
# =============================================================================


class TestParallelReads:
    """Non-conflicting read operations execute in parallel."""

    @pytest.mark.asyncio
    async def test_multiple_reads_execute_concurrently(self):
        """Multiple read operations on different files run in parallel."""
        tools = []
        for i in range(3):
            tool_use = make_tool_use("read_file", path=f"/tmp/file{i}.txt")
            tool_def = make_tool_def("read_file", return_value=f"content_{i}", read_only=True)
            tools.append((tool_use, tool_def))

        agent = make_mock_agent(allowed=True)
        results = await execute_tools_parallel(tools, agent)

        assert len(results) == 3
        assert all(not r.is_error for r in results)
        # Results in order
        assert [r.result for r in results] == ["content_0", "content_1", "content_2"]

    @pytest.mark.asyncio
    async def test_parallel_execution_is_faster_than_sequential(self):
        """Parallel reads complete faster than sequential execution would."""
        import time

        sleep_time = 0.05  # 50ms per operation

        async def slow_read(**kwargs: Any) -> str:
            await asyncio.sleep(sleep_time)
            return "done"

        tools = []
        for i in range(3):
            tool_use = make_tool_use("read_file", path=f"/tmp/file{i}.txt")
            tool_def = make_tool_def("read_file", read_only=True, func=slow_read)
            tools.append((tool_use, tool_def))

        agent = make_mock_agent(allowed=True)

        start = time.time()
        results = await execute_tools_parallel(tools, agent)
        elapsed = time.time() - start

        # Parallel should take ~1x sleep_time, not 3x
        assert elapsed < sleep_time * 2
        assert len(results) == 3


# =============================================================================
# Sequential Writes - Write operations execute one at a time
# =============================================================================


class TestSequentialWrites:
    """Write operations execute sequentially to prevent conflicts."""

    @pytest.mark.asyncio
    async def test_writes_execute_in_order(self):
        """Write operations execute in the order they were requested."""
        execution_order: list[int] = []

        def make_tracking_func(idx: int) -> Any:
            async def func(**kwargs: Any) -> str:
                execution_order.append(idx)
                return f"result_{idx}"

            return func

        tools = []
        for i in range(3):
            tool_use = make_tool_use("edit_file", file_path=f"/tmp/file{i}.txt")
            tool_def = make_tool_def("edit_file", func=make_tracking_func(i))
            tools.append((tool_use, tool_def))

        agent = make_mock_agent(allowed=True)
        results = await execute_tools_parallel(tools, agent)

        assert execution_order == [0, 1, 2]
        assert len(results) == 3

    @pytest.mark.asyncio
    async def test_mixed_read_write_preserves_order(self):
        """Mixed read/write operations execute correctly with writes sequential."""
        tool_use1 = make_tool_use("read_file", path="/tmp/a.txt")
        tool_def1 = make_tool_def("read_file", return_value="a", read_only=True)

        tool_use2 = make_tool_use("edit_file", file_path="/tmp/b.txt")
        tool_def2 = make_tool_def("edit_file", return_value="edited")

        tool_use3 = make_tool_use("read_file", path="/tmp/c.txt")
        tool_def3 = make_tool_def("read_file", return_value="c", read_only=True)

        agent = make_mock_agent(allowed=True)
        results = await execute_tools_parallel(
            [(tool_use1, tool_def1), (tool_use2, tool_def2), (tool_use3, tool_def3)],
            agent,
        )

        assert len(results) == 3
        assert results[0].result == "a"
        assert results[1].result == "edited"
        assert results[2].result == "c"


# =============================================================================
# Error Handling - Permission denied and execution errors
# =============================================================================


class TestErrorHandling:
    """Errors are handled gracefully without breaking batch execution."""

    @pytest.mark.asyncio
    async def test_permission_denied_returns_error_result(self):
        """Permission denied returns error result, doesn't raise."""
        tool_use = make_tool_use("edit_file", file_path="/tmp/test.txt")
        tool_def = make_tool_def("edit_file")

        agent = make_mock_agent(allowed=False)
        results = await execute_tools_parallel([(tool_use, tool_def)], agent)

        assert len(results) == 1
        assert results[0].is_error is True
        assert "Permission denied" in results[0].result

    @pytest.mark.asyncio
    async def test_execution_error_captured_in_result(self):
        """Tool execution errors are captured in result, not raised."""

        async def failing_func(**kwargs: Any) -> str:
            raise FileNotFoundError("File not found")

        tool_use = make_tool_use("read_file", path="/tmp/nonexistent.txt")
        tool_def = make_tool_def("read_file", func=failing_func, read_only=True)

        agent = make_mock_agent(allowed=True)
        results = await execute_tools_parallel([(tool_use, tool_def)], agent)

        assert len(results) == 1
        assert results[0].is_error is True
        assert "File not found" in results[0].result

    @pytest.mark.asyncio
    async def test_one_failure_doesnt_affect_others(self):
        """One tool failing doesn't prevent others from completing."""

        async def failing_func(**kwargs: Any) -> str:
            raise RuntimeError("Tool crashed")

        tool_use1 = make_tool_use("read_file", path="/tmp/good.txt")
        tool_def1 = make_tool_def("read_file", return_value="good", read_only=True)

        tool_use2 = make_tool_use("bad_tool", path="/tmp/bad.txt")
        tool_def2 = make_tool_def("bad_tool", func=failing_func, read_only=True)

        tool_use3 = make_tool_use("read_file", path="/tmp/also_good.txt")
        tool_def3 = make_tool_def("read_file", return_value="also good", read_only=True)

        agent = make_mock_agent(allowed=True)
        results = await execute_tools_parallel(
            [(tool_use1, tool_def1), (tool_use2, tool_def2), (tool_use3, tool_def3)],
            agent,
        )

        assert len(results) == 3
        assert results[0].result == "good"
        assert results[0].is_error is False
        assert results[1].is_error is True
        assert results[2].result == "also good"
        assert results[2].is_error is False


# =============================================================================
# Caching - Cached results are returned without re-execution
# =============================================================================


class TestCaching:
    """Cached results are returned when available."""

    @pytest.mark.asyncio
    async def test_cached_result_marked_as_cached(self):
        """Results from cache have was_cached=True."""
        tool_use = make_tool_use("read_file", path="/tmp/cached.txt")
        tool_def = make_tool_def("read_file", return_value="fresh", read_only=True)

        agent = make_mock_agent(allowed=True, cached_result="cached content")
        results = await execute_tools_parallel([(tool_use, tool_def)], agent)

        assert len(results) == 1
        assert results[0].result == "cached content"
        assert results[0].was_cached is True


# =============================================================================
# Edge Cases - Empty input and single tool
# =============================================================================


class TestEdgeCases:
    """Edge cases are handled correctly."""

    @pytest.mark.asyncio
    async def test_empty_tool_list_returns_empty(self):
        """Empty tool list returns empty results."""
        agent = make_mock_agent()
        results = await execute_tools_parallel([], agent)
        assert results == []

    @pytest.mark.asyncio
    async def test_single_tool_executes(self):
        """Single tool executes and returns result."""
        tool_use = make_tool_use("read_file", path="/tmp/single.txt")
        tool_def = make_tool_def("read_file", return_value="single", read_only=True)

        agent = make_mock_agent(allowed=True)
        results = await execute_tools_parallel([(tool_use, tool_def)], agent)

        assert len(results) == 1
        assert results[0].result == "single"
