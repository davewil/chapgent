from dataclasses import dataclass
from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Pretty, Static


@dataclass
class PaletteCommand:
    """A command that can be executed from the command palette.

    Attributes:
        id: Unique identifier for the command (used as action name).
        name: Human-readable name displayed in the palette.
        description: Short description of what the command does.
        shortcut: Optional keyboard shortcut (for display only).
    """

    id: str
    name: str
    description: str
    shortcut: str | None = None

    def matches(self, query: str) -> bool:
        """Check if this command matches a fuzzy search query.

        Args:
            query: The search query (case-insensitive).

        Returns:
            True if the command matches the query.
        """
        if not query:
            return True

        query_lower = query.lower()
        name_lower = self.name.lower()
        desc_lower = self.description.lower()

        # Check if query is a substring of name or description
        if query_lower in name_lower or query_lower in desc_lower:
            return True

        # Fuzzy match: check if all characters appear in order
        return _fuzzy_match(query_lower, name_lower)


def _fuzzy_match(query: str, text: str) -> bool:
    """Check if all characters in query appear in text in order.

    Args:
        query: The search query.
        text: The text to search in.

    Returns:
        True if all characters match in order.
    """
    query_idx = 0
    for char in text:
        if query_idx < len(query) and char == query[query_idx]:
            query_idx += 1
    return query_idx == len(query)


# Default commands available in the command palette
DEFAULT_COMMANDS: list[PaletteCommand] = [
    PaletteCommand(
        id="new_session",
        name="New Session",
        description="Start a new conversation session",
        shortcut="Ctrl+N",
    ),
    PaletteCommand(
        id="save_session",
        name="Save Session",
        description="Save the current session",
        shortcut="Ctrl+S",
    ),
    PaletteCommand(
        id="toggle_sidebar",
        name="Toggle Sidebar",
        description="Show or hide the sessions sidebar",
        shortcut="Ctrl+B",
    ),
    PaletteCommand(
        id="toggle_permissions",
        name="Toggle Permissions",
        description="Toggle auto-approve for medium risk tools",
        shortcut="Ctrl+P",
    ),
    PaletteCommand(
        id="toggle_tools",
        name="Toggle Tool Panel",
        description="Show or hide the tool panel",
        shortcut="Ctrl+T",
    ),
    PaletteCommand(
        id="clear",
        name="Clear Conversation",
        description="Clear the current conversation",
        shortcut="Ctrl+L",
    ),
    PaletteCommand(
        id="quit",
        name="Quit",
        description="Exit the application",
        shortcut="Ctrl+C",
    ),
]


class ConversationPanel(Static):
    """Display for the conversation history."""

    BORDER_TITLE = "💬 Conversation"

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="conversation-messages")

    def append_user_message(self, content: str) -> None:
        """Append a user message to the conversation."""
        scroll = self.query_one("#conversation-messages", VerticalScroll)
        scroll.mount(Static(f"👤 You: {content}", classes="user-message"))
        scroll.scroll_end(animate=False)

    def append_assistant_message(self, content: str) -> None:
        """Append an assistant message to the conversation."""
        scroll = self.query_one("#conversation-messages", VerticalScroll)
        scroll.mount(Static(f"🤖 Agent: {content}", classes="agent-message"))
        scroll.scroll_end(animate=False)

    def clear(self) -> None:
        """Clear the conversation history."""
        scroll = self.query_one("#conversation-messages", VerticalScroll)
        scroll.query("*").remove()


class ToolResultItem(Static):
    """Widget to display a tool result."""

    def __init__(self, content: str, tool_name: str, result: str, **kwargs: Any):
        super().__init__(content, **kwargs)
        self.tool_name = tool_name
        self.result = result


class ToolPanel(Static):
    """Display for tool activity."""

    BORDER_TITLE = "🔧 Tools"

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="tool-output")

    def append_tool_call(self, tool_name: str, tool_id: str) -> None:
        """Append a tool call to the panel."""
        scroll = self.query_one("#tool-output", VerticalScroll)
        scroll.mount(Static(f"⏳ Running: {tool_name}", classes="tool-call"))
        scroll.scroll_end(animate=False)

    def append_tool_result(self, tool_name: str, result: str) -> None:
        """Append a tool result to the panel."""
        # Truncate long results for display
        display_result = result[:200] + "..." if len(result) > 200 else result
        item = ToolResultItem(f"✅ {tool_name}: {display_result}", tool_name, result, classes="tool-result")
        scroll = self.query_one("#tool-output", VerticalScroll)
        scroll.mount(item)
        scroll.scroll_end(animate=False)

    def clear(self) -> None:
        """Clear the tool activity."""
        scroll = self.query_one("#tool-output", VerticalScroll)
        scroll.query("*").remove()


class MessageInput(Input):
    """Input widget for user messages."""

    def on_mount(self) -> None:
        self.placeholder = "Type your message..."


class PermissionPrompt(ModalScreen[bool]):
    """Modal to ask for permission."""

    def __init__(self, tool_name: str, args: dict[str, Any]):
        super().__init__()
        self.tool_name = tool_name
        self.args = args

    def compose(self) -> ComposeResult:
        yield Static(f"Allow execution of tool '{self.tool_name}'?")
        yield Pretty(self.args)
        with Horizontal(classes="buttons"):
            yield Button("Yes", variant="success", id="btn-yes")
            yield Button("No", variant="error", id="btn-no")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "btn-yes":
            self.dismiss(True)
        else:
            self.dismiss(False)


class CommandPaletteItem(Static):
    """Widget to display a single command in the command palette."""

    def __init__(
        self,
        command: PaletteCommand,
        is_selected: bool = False,
        **kwargs: Any,
    ):
        """Initialize a command palette item.

        Args:
            command: The command to display.
            is_selected: Whether this item is currently selected.
            **kwargs: Additional arguments passed to Static.
        """
        # Format: name (shortcut) - description
        shortcut_str = f" ({command.shortcut})" if command.shortcut else ""
        display_text = f"{command.name}{shortcut_str}"

        # Add CSS classes
        classes = kwargs.pop("classes", "")
        if is_selected:
            classes = f"{classes} palette-item-selected".strip()
        else:
            classes = f"{classes} palette-item".strip()

        super().__init__(display_text, classes=classes, **kwargs)
        self.command = command
        self.is_selected = is_selected

    def set_selected(self, selected: bool) -> None:
        """Update the selected state of this item.

        Args:
            selected: Whether to select this item.
        """
        self.is_selected = selected
        if selected:
            self.add_class("palette-item-selected")
            self.remove_class("palette-item")
        else:
            self.add_class("palette-item")
            self.remove_class("palette-item-selected")


class CommandPalette(ModalScreen[str | None]):
    """Modal command palette for quick command access.

    Features:
    - Fuzzy search input
    - List of available commands
    - Keyboard navigation (up/down arrows)
    - Enter to execute selected command
    - Escape to dismiss
    """

    BINDINGS = [
        ("escape", "dismiss_palette", "Close"),
        ("up", "move_up", "Previous"),
        ("down", "move_down", "Next"),
        ("enter", "select_command", "Execute"),
    ]

    def __init__(
        self,
        commands: list[PaletteCommand] | None = None,
        **kwargs: Any,
    ):
        """Initialize the command palette.

        Args:
            commands: List of commands to display. Uses DEFAULT_COMMANDS if None.
            **kwargs: Additional arguments passed to ModalScreen.
        """
        super().__init__(**kwargs)
        self.commands = commands if commands is not None else DEFAULT_COMMANDS.copy()
        self.filtered_commands: list[PaletteCommand] = []
        self.selected_index = 0

    def compose(self) -> ComposeResult:
        """Create child widgets for the palette."""
        yield Static("Command Palette", id="palette-title")
        yield Input(placeholder="Type to search commands...", id="palette-input")
        yield VerticalScroll(id="palette-commands")

    def on_mount(self) -> None:
        """Handle mount event."""
        self._update_command_list("")
        self.query_one("#palette-input", Input).focus()

    def on_input_changed(self, event: Input.Changed) -> None:
        """Handle input changes for filtering."""
        self._update_command_list(event.value)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle enter pressed in the input field."""
        self.action_select_command()

    def _update_command_list(self, query: str) -> None:
        """Update the list of displayed commands based on the query.

        Args:
            query: The search query.
        """
        # Filter commands based on query
        self.filtered_commands = [cmd for cmd in self.commands if cmd.matches(query)]
        self.selected_index = 0 if self.filtered_commands else -1

        # Clear and rebuild the command list
        scroll = self.query_one("#palette-commands", VerticalScroll)
        scroll.query(CommandPaletteItem).remove()

        for i, cmd in enumerate(self.filtered_commands):
            item = CommandPaletteItem(command=cmd, is_selected=(i == 0))
            scroll.mount(item)

    def action_dismiss_palette(self) -> None:
        """Dismiss the palette without selecting a command."""
        self.dismiss(None)

    def action_move_up(self) -> None:
        """Move selection up."""
        if not self.filtered_commands:
            return

        self._set_selected(max(0, self.selected_index - 1))

    def action_move_down(self) -> None:
        """Move selection down."""
        if not self.filtered_commands:
            return

        self._set_selected(min(len(self.filtered_commands) - 1, self.selected_index + 1))

    def _set_selected(self, new_index: int) -> None:
        """Update the selected item.

        Args:
            new_index: The new selected index.
        """
        scroll = self.query_one("#palette-commands", VerticalScroll)
        items = list(scroll.query(CommandPaletteItem))

        if 0 <= self.selected_index < len(items):
            items[self.selected_index].set_selected(False)

        self.selected_index = new_index

        if 0 <= new_index < len(items):
            items[new_index].set_selected(True)
            # Scroll to keep selected item visible
            items[new_index].scroll_visible()

    def action_select_command(self) -> None:
        """Execute the selected command."""
        if 0 <= self.selected_index < len(self.filtered_commands):
            command = self.filtered_commands[self.selected_index]
            self.dismiss(command.id)
        else:
            self.dismiss(None)

    def on_click(self, event: Any) -> None:
        """Handle click events on command items."""
        # Find if click was on a CommandPaletteItem
        scroll = self.query_one("#palette-commands", VerticalScroll)
        items = list(scroll.query(CommandPaletteItem))

        for i, item in enumerate(items):
            # Check if this widget was clicked (approximate using geometry)
            if item.is_mouse_over:
                self._set_selected(i)
                self.action_select_command()
                return


class SessionItem(Static):
    """Widget to display a single session item in the sidebar."""

    def __init__(self, session_id: str, message_count: int, is_active: bool = False, **kwargs: Any):
        """Initialize a session item.

        Args:
            session_id: The session ID.
            message_count: Number of messages in the session.
            is_active: Whether this is the currently active session.
            **kwargs: Additional arguments passed to Static.
        """
        # Display format: arrow for active, truncated ID, message count
        prefix = "▸ " if is_active else "  "
        display_text = f"{prefix}{session_id[:8]}… ({message_count} msgs)"

        # Add CSS class for active styling
        classes = kwargs.pop("classes", "")
        if is_active:
            classes = f"{classes} session-active".strip()

        super().__init__(display_text, classes=classes, **kwargs)
        self.session_id = session_id
        self.is_active = is_active
        self.message_count = message_count


class SessionsSidebar(Static):
    """Sidebar widget showing saved sessions.

    Features:
    - List recent sessions with truncated IDs
    - Shows message count per session
    - Highlights active session
    - Click to switch between sessions
    """

    BORDER_TITLE = "📋 Sessions"

    def compose(self) -> ComposeResult:
        """Create child widgets for the sidebar."""
        yield VerticalScroll(id="sessions-list")

    def add_session(
        self,
        session_id: str,
        message_count: int = 0,
        is_active: bool = False,
    ) -> None:
        """Add a session to the sidebar list.

        Args:
            session_id: The session ID.
            message_count: Number of messages in the session.
            is_active: Whether this is the currently active session.
        """
        scroll = self.query_one("#sessions-list", VerticalScroll)
        item = SessionItem(
            session_id=session_id,
            message_count=message_count,
            is_active=is_active,
            classes="session-item",
        )
        scroll.mount(item)

    def update_active_session(self, active_session_id: str) -> None:
        """Update which session is marked as active.

        Args:
            active_session_id: The ID of the currently active session.
        """
        scroll = self.query_one("#sessions-list", VerticalScroll)

        # Check if the new active session exists in the list
        session_exists = any(item.session_id == active_session_id for item in scroll.query(SessionItem))

        # Only update if the session exists (don't deactivate all if session not found)
        if not session_exists:
            return

        for item in scroll.query(SessionItem):
            was_active = item.is_active
            is_now_active = item.session_id == active_session_id

            if was_active != is_now_active:
                item.is_active = is_now_active
                # Update display text
                prefix = "▸ " if is_now_active else "  "
                item.update(f"{prefix}{item.session_id[:8]}… ({item.message_count} msgs)")

                # Update CSS classes
                if is_now_active:
                    item.add_class("session-active")
                else:
                    item.remove_class("session-active")

    def clear(self) -> None:
        """Clear all sessions from the sidebar."""
        scroll = self.query_one("#sessions-list", VerticalScroll)
        scroll.query(SessionItem).remove()

    def get_session_count(self) -> int:
        """Get the number of sessions in the sidebar.

        Returns:
            Number of session items.
        """
        scroll = self.query_one("#sessions-list", VerticalScroll)
        return len(scroll.query(SessionItem))
