from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.screen import ModalScreen
from textual.widgets import Input, Pretty, Static


class ConversationPanel(Static):
    """Display for the conversation history."""

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="conversation-messages")

    def append_user_message(self, content: str) -> None:
        """Append a user message to the conversation."""
        self.query_one("#conversation-messages").mount(Static(f"User: {content}", classes="user-message"))

    def append_assistant_message(self, content: str) -> None:
        """Append an assistant message to the conversation."""
        self.query_one("#conversation-messages").mount(Static(f"Agent: {content}", classes="agent-message"))


class ToolPanel(Static):
    """Display for tool activity."""

    def compose(self) -> ComposeResult:
        yield VerticalScroll(id="tool-output")

    def append_tool_call(self, tool_name: str, tool_id: str) -> None:
        """Append a tool call to the panel."""
        self.query_one("#tool-output").mount(Static(f"Running: {tool_name} ({tool_id})", classes="tool-call"))

    def append_tool_result(self, tool_name: str, result: str) -> None:
        """Append a tool result to the panel."""
        self.query_one("#tool-output").mount(Static(f"Result ({tool_name}): {result}", classes="tool-result"))


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
