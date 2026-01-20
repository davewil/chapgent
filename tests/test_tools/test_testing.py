"""Behavioral tests for testing tools.

Tests verify user-facing behavior:
- Framework detection from project config files
- Running tests and getting results
- Test output parsing for different frameworks
- Error handling for timeouts, missing runners
"""

import asyncio
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from chapgent.context.models import TestFramework
from chapgent.tools.testing import detect_test_framework, parse_test_output, run_tests

# =============================================================================
# Framework Detection - Detect test framework from project files
# =============================================================================


class TestFrameworkDetection:
    """User's test framework is detected from project configuration."""

    __test__ = True

    @pytest.mark.asyncio
    async def test_detects_pytest_from_pyproject_toml(self, tmp_path: Path):
        """Detect pytest from pyproject.toml."""
        (tmp_path / "pyproject.toml").write_text('[tool.pytest.ini_options]\naddopts = "-v"')
        assert await detect_test_framework(tmp_path) == TestFramework.PYTEST

    @pytest.mark.asyncio
    async def test_detects_pytest_from_test_files(self, tmp_path: Path):
        """Detect pytest from test_*.py files in tests/ directory."""
        (tmp_path / "tests").mkdir()
        (tmp_path / "tests" / "test_example.py").write_text("def test_foo(): pass")
        assert await detect_test_framework(tmp_path) == TestFramework.PYTEST

    @pytest.mark.asyncio
    async def test_detects_jest_from_package_json(self, tmp_path: Path):
        """Detect Jest from package.json devDependencies."""
        (tmp_path / "package.json").write_text('{"devDependencies": {"jest": "^29.0.0"}}')
        assert await detect_test_framework(tmp_path) == TestFramework.JEST

    @pytest.mark.asyncio
    async def test_detects_vitest_over_jest(self, tmp_path: Path):
        """Vitest takes precedence over Jest when both present."""
        (tmp_path / "package.json").write_text('{"devDependencies": {"vitest": "^1.0.0", "jest": "^29.0.0"}}')
        assert await detect_test_framework(tmp_path) == TestFramework.VITEST

    @pytest.mark.asyncio
    async def test_detects_go_test_from_go_mod(self, tmp_path: Path):
        """Detect go test from go.mod file."""
        (tmp_path / "go.mod").write_text("module example.com/project")
        assert await detect_test_framework(tmp_path) == TestFramework.GO_TEST

    @pytest.mark.asyncio
    async def test_detects_cargo_test_from_cargo_toml(self, tmp_path: Path):
        """Detect cargo test from Cargo.toml file."""
        (tmp_path / "Cargo.toml").write_text('[package]\nname = "myproject"')
        assert await detect_test_framework(tmp_path) == TestFramework.CARGO_TEST

    @pytest.mark.asyncio
    async def test_returns_unknown_when_no_framework(self, tmp_path: Path):
        """Return UNKNOWN when no framework can be detected."""
        assert await detect_test_framework(tmp_path) == TestFramework.UNKNOWN

    @pytest.mark.asyncio
    async def test_handles_invalid_package_json(self, tmp_path: Path):
        """Handle malformed package.json gracefully."""
        (tmp_path / "package.json").write_text("{invalid json")
        assert await detect_test_framework(tmp_path) == TestFramework.UNKNOWN


# =============================================================================
# Test Output Parsing - Parse output from different test runners
# =============================================================================


class TestOutputParsing:
    """Test output is parsed correctly for different frameworks."""

    __test__ = True

    @pytest.mark.asyncio
    async def test_parses_pytest_passed(self):
        """Parse pytest output showing passed tests."""
        output = """
============================= test session starts ==============================
tests/test_foo.py::test_one PASSED
tests/test_foo.py::test_two PASSED
============================== 2 passed in 0.12s ===============================
"""
        summary = await parse_test_output(output, TestFramework.PYTEST)
        assert summary.passed == 2
        assert summary.failed == 0
        assert summary.duration == 0.12

    @pytest.mark.asyncio
    async def test_parses_pytest_failed(self):
        """Parse pytest output showing failures."""
        output = """
tests/test_foo.py::test_pass PASSED
tests/test_foo.py::test_fail FAILED
=========================== 1 passed, 1 failed in 0.23s ========================
"""
        summary = await parse_test_output(output, TestFramework.PYTEST)
        assert summary.passed == 1
        assert summary.failed == 1

    @pytest.mark.asyncio
    async def test_parses_pytest_skipped(self):
        """Parse pytest output with skipped tests."""
        output = """
tests/test_foo.py::test_one PASSED
tests/test_foo.py::test_skip SKIPPED
========================= 1 passed, 1 skipped in 0.05s =========================
"""
        summary = await parse_test_output(output, TestFramework.PYTEST)
        assert summary.passed == 1
        assert summary.skipped == 1

    @pytest.mark.asyncio
    async def test_parses_jest_output(self):
        """Parse Jest output."""
        output = """
 PASS  src/test.js
  ✓ should pass (5 ms)
  ✕ should fail (10 ms)
Tests:  1 failed, 1 passed, 2 total
Time:   2.5s
"""
        summary = await parse_test_output(output, TestFramework.JEST)
        assert summary.passed == 1
        assert summary.failed == 1
        assert summary.total == 2

    @pytest.mark.asyncio
    async def test_parses_go_test_output(self):
        """Parse go test output."""
        output = """
=== RUN   TestOne
--- PASS: TestOne (0.00s)
=== RUN   TestTwo
--- FAIL: TestTwo (0.01s)
FAIL    example.com/project     0.02s
"""
        summary = await parse_test_output(output, TestFramework.GO_TEST)
        assert summary.passed == 1
        assert summary.failed == 1

    @pytest.mark.asyncio
    async def test_parses_cargo_test_output(self):
        """Parse cargo test output."""
        output = """
running 2 tests
test module::test_one ... ok
test module::test_two ... FAILED
test result: FAILED. 1 passed; 1 failed; 0 ignored; finished in 0.15s
"""
        summary = await parse_test_output(output, TestFramework.CARGO_TEST)
        assert summary.passed == 1
        assert summary.failed == 1

    @pytest.mark.asyncio
    async def test_parses_unittest_output(self):
        """Parse unittest output."""
        output = """
test_one (test_module.TestClass) ... ok
test_two (test_module.TestClass) ... FAIL
----------------------------------------------------------------------
Ran 2 tests in 0.001s
FAILED (failures=1)
"""
        summary = await parse_test_output(output, TestFramework.UNITTEST)
        assert summary.passed == 1
        assert summary.failed == 1

    @pytest.mark.asyncio
    async def test_unknown_framework_returns_raw_output(self):
        """Unknown framework returns raw output without parsing."""
        output = "some test output"
        summary = await parse_test_output(output, TestFramework.UNKNOWN)
        assert summary.raw_output == output
        assert summary.total == 0


# =============================================================================
# Running Tests - Execute tests and get results
# =============================================================================


class TestRunTests:
    """User can run tests and get formatted results."""

    __test__ = True

    @pytest.mark.asyncio
    async def test_runs_tests_successfully(self, tmp_path: Path):
        """Run tests and get passing result."""
        (tmp_path / "pyproject.toml").write_text("[tool.pytest]")

        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"============================== 2 passed in 0.05s ==============================", b"")
        )
        mock_process.returncode = 0
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_process)):
            result = await run_tests(working_dir=str(tmp_path))

        assert "PASSED" in result
        assert "2 passed" in result

    @pytest.mark.asyncio
    async def test_runs_tests_with_failures(self, tmp_path: Path):
        """Run tests and get failure result."""
        (tmp_path / "pyproject.toml").write_text("[tool.pytest]")

        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(
            return_value=(b"tests/test_foo.py::test_fail FAILED\n=== 1 passed, 1 failed in 0.1s ===", b"")
        )
        mock_process.returncode = 1
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_process)):
            result = await run_tests(working_dir=str(tmp_path))

        assert "FAILED" in result
        assert "1 failed" in result

    @pytest.mark.asyncio
    async def test_specifies_framework_explicitly(self, tmp_path: Path):
        """User can specify framework explicitly."""
        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(b"Ran 1 tests in 0.001s\n\nOK", b""))
        mock_process.returncode = 0
        mock_process.wait = AsyncMock()

        with patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_process)):
            result = await run_tests(framework="unittest", working_dir=str(tmp_path))

        assert "PASSED" in result


# =============================================================================
# Error Handling - Handle various error conditions
# =============================================================================


class TestErrorHandling:
    """Errors are handled gracefully with helpful messages."""

    __test__ = True

    @pytest.mark.asyncio
    async def test_unknown_framework_error(self, tmp_path: Path):
        """Error message when no framework detected."""
        result = await run_tests(working_dir=str(tmp_path))
        assert "Could not detect test framework" in result

    @pytest.mark.asyncio
    async def test_invalid_framework_error(self, tmp_path: Path):
        """Error message when invalid framework specified."""
        result = await run_tests(framework="invalid_framework", working_dir=str(tmp_path))
        assert "Unknown test framework" in result

    @pytest.mark.asyncio
    async def test_timeout_error(self, tmp_path: Path):
        """Error message when tests timeout."""
        (tmp_path / "pyproject.toml").write_text("[tool.pytest]")

        mock_process = MagicMock()
        mock_process.communicate = AsyncMock(return_value=(b"", b""))
        mock_process.returncode = None
        mock_process.kill = MagicMock()
        mock_process.wait = AsyncMock()

        with (
            patch("asyncio.create_subprocess_exec", AsyncMock(return_value=mock_process)),
            patch("asyncio.wait_for", side_effect=asyncio.TimeoutError),
        ):
            result = await run_tests(working_dir=str(tmp_path), timeout=1)

        assert "timed out" in result

    @pytest.mark.asyncio
    async def test_missing_runner_error(self, tmp_path: Path):
        """Error message when test runner not found."""
        (tmp_path / "pyproject.toml").write_text("[tool.pytest]")

        with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
            result = await run_tests(working_dir=str(tmp_path))

        assert "not found" in result

    @pytest.mark.asyncio
    async def test_execution_error(self, tmp_path: Path):
        """Error message when execution fails."""
        (tmp_path / "pyproject.toml").write_text("[tool.pytest]")

        with patch("asyncio.create_subprocess_exec", side_effect=OSError("Permission denied")):
            result = await run_tests(working_dir=str(tmp_path))

        assert "Error running tests" in result
        assert "Permission denied" in result
