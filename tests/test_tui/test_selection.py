"""Tests for message selection and clipboard functionality.

These tests verify the ability to select messages in the conversation panel
and copy their content to the clipboard.
"""

import pytest

from chapgent.tui.app import ChapgentApp
from chapgent.tui.markdown import MarkdownMessage
from chapgent.tui.widgets import ConversationPanel

# =============================================================================
# MarkdownMessage Selection Tests
# =============================================================================


class TestMarkdownMessageSelection:
    """Tests for MarkdownMessage selection state."""

    def test_message_not_selected_by_default(self):
        """Test that messages are not selected by default."""
        msg = MarkdownMessage("Hello", role="user")
        assert msg.selected is False

    def test_message_selection_toggle(self):
        """Test toggling selection state."""
        msg = MarkdownMessage("Hello", role="user")

        msg.selected = True
        assert msg.selected is True

        msg.selected = False
        assert msg.selected is False

    def test_selected_adds_css_class(self):
        """Test that selecting adds the 'selected' CSS class."""
        msg = MarkdownMessage("Hello", role="user")

        msg.selected = True
        assert "selected" in msg.classes

    def test_deselected_removes_css_class(self):
        """Test that deselecting removes the 'selected' CSS class."""
        msg = MarkdownMessage("Hello", role="user")

        msg.selected = True
        msg.selected = False
        assert "selected" not in msg.classes

    def test_selection_preserves_role_class(self):
        """Test that selection doesn't affect role CSS class."""
        msg = MarkdownMessage("Hello", role="user")

        msg.selected = True
        assert "user-message" in msg.classes
        assert "selected" in msg.classes

        msg.selected = False
        assert "user-message" in msg.classes


# =============================================================================
# ConversationPanel Selection Management Tests
# =============================================================================


class TestConversationPanelSelection:
    """Tests for ConversationPanel selection management."""

    @pytest.mark.asyncio
    async def test_get_selected_messages_empty(self):
        """Test getting selected messages when none are selected."""
        app = ChapgentApp()
        async with app.run_test(size=(100, 50)) as pilot:
            panel = app.query_one(ConversationPanel)

            # Add messages without selecting
            panel.append_user_message("User message")
            panel.append_assistant_message("Agent message")
            await pilot.pause()

            selected = panel.get_selected_messages()
            assert selected == []

    @pytest.mark.asyncio
    async def test_get_selected_messages_with_selection(self):
        """Test getting selected messages when some are selected."""
        app = ChapgentApp()
        async with app.run_test(size=(100, 50)) as pilot:
            panel = app.query_one(ConversationPanel)

            panel.append_user_message("User message")
            panel.append_assistant_message("Agent message")
            await pilot.pause()

            # Select the first message
            messages = list(panel.query_one("#conversation-messages").query(MarkdownMessage))
            messages[0].selected = True
            await pilot.pause()

            selected = panel.get_selected_messages()
            assert len(selected) == 1
            assert selected[0].content == "User message"

    @pytest.mark.asyncio
    async def test_get_selected_content_empty(self):
        """Test getting content when no messages are selected."""
        app = ChapgentApp()
        async with app.run_test(size=(100, 50)) as pilot:
            panel = app.query_one(ConversationPanel)

            panel.append_user_message("User message")
            await pilot.pause()

            content = panel.get_selected_content()
            assert content == ""

    @pytest.mark.asyncio
    async def test_get_selected_content_single_message(self):
        """Test getting content of a single selected message."""
        app = ChapgentApp()
        async with app.run_test(size=(100, 50)) as pilot:
            panel = app.query_one(ConversationPanel)

            panel.append_user_message("Hello world")
            await pilot.pause()

            # Select the message
            messages = list(panel.query_one("#conversation-messages").query(MarkdownMessage))
            messages[0].selected = True

            content = panel.get_selected_content()
            assert "You: Hello world" in content

    @pytest.mark.asyncio
    async def test_get_selected_content_multiple_messages(self):
        """Test getting content of multiple selected messages."""
        app = ChapgentApp()
        async with app.run_test(size=(100, 50)) as pilot:
            panel = app.query_one(ConversationPanel)

            panel.append_user_message("User says hello")
            panel.append_assistant_message("Agent responds")
            await pilot.pause()

            # Select both messages
            messages = list(panel.query_one("#conversation-messages").query(MarkdownMessage))
            for msg in messages:
                msg.selected = True

            content = panel.get_selected_content()
            assert "You: User says hello" in content
            assert "Agent: Agent responds" in content

    @pytest.mark.asyncio
    async def test_clear_selection(self):
        """Test clearing all selections."""
        app = ChapgentApp()
        async with app.run_test(size=(100, 50)) as pilot:
            panel = app.query_one(ConversationPanel)

            panel.append_user_message("Message 1")
            panel.append_assistant_message("Message 2")
            await pilot.pause()

            # Select all
            messages = list(panel.query_one("#conversation-messages").query(MarkdownMessage))
            for msg in messages:
                msg.selected = True

            # Clear selection
            panel.clear_selection()

            for msg in messages:
                assert msg.selected is False

    @pytest.mark.asyncio
    async def test_select_all(self):
        """Test selecting all messages."""
        app = ChapgentApp()
        async with app.run_test(size=(100, 50)) as pilot:
            panel = app.query_one(ConversationPanel)

            panel.append_user_message("Message 1")
            panel.append_assistant_message("Message 2")
            panel.append_user_message("Message 3")
            await pilot.pause()

            panel.select_all()

            messages = list(panel.query_one("#conversation-messages").query(MarkdownMessage))
            for msg in messages:
                assert msg.selected is True


# =============================================================================
# Copy Action Tests
# =============================================================================


class TestCopyAction:
    """Tests for the copy to clipboard action."""

    @pytest.mark.asyncio
    async def test_copy_action_with_selection(self):
        """Test copy action when messages are selected."""
        app = ChapgentApp()
        async with app.run_test(size=(100, 50)) as pilot:
            panel = app.query_one(ConversationPanel)

            panel.append_user_message("Test message")
            await pilot.pause()

            # Select the message
            messages = list(panel.query_one("#conversation-messages").query(MarkdownMessage))
            messages[0].selected = True

            # Execute copy action
            app.action_copy_selection()
            await pilot.pause()

            # Should show success notification (can't verify clipboard content directly)

    @pytest.mark.asyncio
    async def test_copy_action_without_selection(self):
        """Test copy action when no messages are selected."""
        app = ChapgentApp()
        async with app.run_test(size=(100, 50)) as pilot:
            panel = app.query_one(ConversationPanel)

            panel.append_user_message("Test message")
            await pilot.pause()

            # Don't select anything, execute copy action
            app.action_copy_selection()
            await pilot.pause()

            # Should show warning notification


# =============================================================================
# Click Selection Tests
# =============================================================================


class TestClickSelection:
    """Tests for click-to-select behavior."""

    @pytest.mark.asyncio
    async def test_click_toggles_selection(self):
        """Test that clicking a message toggles its selection."""
        app = ChapgentApp()
        async with app.run_test(size=(100, 50)) as pilot:
            panel = app.query_one(ConversationPanel)

            panel.append_user_message("Click me")
            await pilot.pause()

            messages = list(panel.query_one("#conversation-messages").query(MarkdownMessage))
            msg = messages[0]

            # Initially not selected
            assert msg.selected is False

            # Click to select
            await pilot.click(msg)
            await pilot.pause()
            assert msg.selected is True

            # Click again to deselect
            await pilot.click(msg)
            await pilot.pause()
            assert msg.selected is False
