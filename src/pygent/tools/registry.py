from __future__ import annotations

from typing import Any

from pygent.tools.base import ToolDefinition


class ToolRegistry:
    """Central registry for all available tools.

    Provides lookup by name and serialization for LLM.
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool: ToolDefinition) -> None:
        """Register a tool definition.

        Args:
            tool: The tool definition to register.
        """
        self._tools[tool.name] = tool

    def get(self, name: str) -> ToolDefinition | None:
        """Get a tool definition by name.

        Args:
            name: The name of the tool to retrieve.

        Returns:
            The tool definition if found, None otherwise.
        """
        return self._tools.get(name)

    def list_definitions(self) -> list[dict[str, Any]]:
        """List all tool definitions for LLM consumption.

        Returns:
            A list of dictionary representations of the tools.
        """
        return [
            {
                "name": tool.name,
                "description": tool.description,
                "input_schema": tool.input_schema,
            }
            for tool in self._tools.values()
        ]
