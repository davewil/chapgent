from unittest.mock import patch

from click.testing import CliRunner
from pygent.cli import cli


def test_cli_structure():
    """Test that the CLI has the expected structure."""
    runner = CliRunner()
    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0
    assert "Pygent - AI-powered coding agent" in result.output
    assert "chat" in result.output
    assert "sessions" in result.output
    assert "resume" in result.output
    assert "config" in result.output


@patch("pygent.cli.PygentApp")
@patch("pygent.cli.Agent")
@patch("pygent.cli.LLMProvider")
@patch("pygent.cli.ToolRegistry")
@patch("pygent.cli.SessionStorage")
@patch("pygent.cli.PermissionManager")
def test_cli_chat_startup(mock_permissions, mock_storage, mock_registry, mock_provider, mock_agent, mock_app):
    """Test that the chat command initializes components and starts the app."""
    runner = CliRunner()

    # Run the chat command
    result = runner.invoke(cli, ["chat"])

    if result.exit_code != 0:
        print(result.output)

    assert result.exit_code == 0

    # Verify initialization
    mock_provider.assert_called()
    mock_registry.assert_called()
    mock_storage.assert_called()
    mock_permissions.assert_called()

    # Verify Agent initialization
    mock_agent.assert_called()

    # Verify App initialization and run
    mock_app.assert_called()
    mock_app.return_value.run.assert_called()
