from typing import Any

from textual.app import ComposeResult
from textual.containers import Horizontal, VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Pretty, Static


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
