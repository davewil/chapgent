from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Pretty, Static


class ConversationPanel(Static):
    """Display for the conversation history."""

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="conversation-messages")


class ToolPanel(Static):
    """Display for tool activity."""

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="tool-output")


class MessageInput(Input):
    """Input widget for user messages."""

    def on_mount(self) -> None:
        self.placeholder = "Type your message..."


class PermissionPrompt(ModalScreen[bool]):
    """Modal to ask for permission."""

    def __init__(self, tool_name: str, args: dict):
        super().__init__()
        self.tool_name = tool_name
        self.args = args

    def compose(self) -> ComposeResult:
        yield Static(f"Allow execution of tool '{self.tool_name}'?")
        yield Pretty(self.args)
        # In a real impl we'd have buttons here, for now just basic structure
