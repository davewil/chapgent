from textual.app import App, ComposeResult
from textual.widgets import Footer, Header

from pygent.tui.widgets import ConversationPanel, MessageInput, ToolPanel


class PygentApp(App):
    """Main Textual application for Pygent."""

    CSS_PATH = "styles.tcss"

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+n", "new_session", "New Session"),
        ("ctrl+s", "save_session", "Save"),
        ("ctrl+p", "toggle_permissions", "Toggle Permissions"),
    ]

    def compose(self) -> ComposeResult:
        """Create child widgets for the app."""
        yield Header()
        yield ConversationPanel()
        yield ToolPanel()
        yield MessageInput()
        yield Footer()


if __name__ == "__main__":
    app = PygentApp()
    app.run()
