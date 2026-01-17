from typing import Literal

from pydantic import BaseModel

# Default base system prompt
DEFAULT_SYSTEM_PROMPT = """You are a helpful coding assistant.

You help with software engineering tasks including writing code, debugging,
explaining concepts, and performing file operations. You have access to tools
that let you read and modify files, run shell commands, search code, and more.

Be concise and direct in your responses. Follow the coding conventions and
style of the existing codebase when making changes."""


class LLMSettings(BaseModel):
    provider: str = "anthropic"
    model: str = "claude-sonnet-4-20250514"
    max_tokens: int = 4096
    api_key: str | None = None  # Falls back to env var


class PermissionSettings(BaseModel):
    auto_approve_low_risk: bool = True
    session_override_allowed: bool = True


class TUISettings(BaseModel):
    theme: str = "textual-dark"
    show_tool_panel: bool = True
    show_sidebar: bool = True


class SystemPromptSettings(BaseModel):
    """System prompt configuration.

    Supports multiple modes for customizing the system prompt:
    - content: Direct prompt content (replaces or appends based on mode)
    - file: Path to a file containing the prompt (supports ~ expansion)
    - append: Additional content to append to the base prompt
    - mode: "replace" or "append" - how to combine custom content with base

    Priority:
    1. If 'file' is set, load content from that file
    2. Otherwise use 'content' if set
    3. In 'append' mode, the custom content is added after the base prompt
    4. In 'replace' mode, the custom content replaces the base prompt entirely

    Template variables (like {project_name}) are resolved at runtime.
    """

    content: str | None = None
    file: str | None = None  # Path to prompt file (supports ~ expansion)
    append: str | None = None  # Additional content to append
    mode: Literal["replace", "append"] = "append"


class Settings(BaseModel):
    llm: LLMSettings = LLMSettings()
    permissions: PermissionSettings = PermissionSettings()
    tui: TUISettings = TUISettings()
    system_prompt: SystemPromptSettings = SystemPromptSettings()
