import pytest
from textual.widgets import Footer, Header

from chapgent.tui.app import ChapgentApp
from chapgent.tui.widgets import ConversationPanel, MessageInput, SessionsSidebar, ToolPanel
from tests.test_tui.conftest import get_binding


@pytest.mark.asyncio
async def test_app_startup():
    """Test that the app starts execution and shows key widgets."""
    app = ChapgentApp()
    async with app.run_test():
        # Check if the app is running
        assert app.is_running

        # Check for main layout components
        assert app.query_one(Header)
        assert app.query_one(Footer)
        assert app.query_one(SessionsSidebar)
        assert app.query_one(ConversationPanel)
        assert app.query_one(ToolPanel)
        assert app.query_one(MessageInput)


@pytest.mark.asyncio
async def test_app_quit_binding():
    """Test that the quit binding works."""
    app = ChapgentApp()
    async with app.run_test() as pilot:
        await pilot.press(get_binding("quit"))
        assert not app.is_running
