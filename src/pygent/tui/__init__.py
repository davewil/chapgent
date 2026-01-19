"""TUI module for Pygent."""

from pygent.tui.app import PygentApp
from pygent.tui.commands import (
    SLASH_COMMANDS,
    SlashCommand,
    format_command_list,
    get_command_help,
    get_slash_command,
    list_slash_commands,
    parse_slash_command,
)
from pygent.tui.widgets import (
    CommandPalette,
    CommandPaletteItem,
    ConversationPanel,
    MessageInput,
    PaletteCommand,
    PermissionPrompt,
    SessionItem,
    SessionsSidebar,
    ToolPanel,
    ToolProgressItem,
    ToolResultItem,
    ToolStatus,
)

__all__ = [
    # App
    "PygentApp",
    # Commands
    "SLASH_COMMANDS",
    "SlashCommand",
    "format_command_list",
    "get_command_help",
    "get_slash_command",
    "list_slash_commands",
    "parse_slash_command",
    # Widgets
    "CommandPalette",
    "CommandPaletteItem",
    "ConversationPanel",
    "MessageInput",
    "PaletteCommand",
    "PermissionPrompt",
    "SessionItem",
    "SessionsSidebar",
    "ToolPanel",
    "ToolProgressItem",
    "ToolResultItem",
    "ToolStatus",
]
