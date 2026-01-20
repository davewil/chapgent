"""Shared fixtures and helpers for TUI tests."""

from chapgent.tui.app import ChapgentApp


def get_binding(action: str) -> str:
    """Get the keybinding for a given action from ChapgentApp.BINDINGS.

    Args:
        action: The action name (e.g., "command_palette", "quit").

    Returns:
        The key combination string (e.g., "ctrl+p").

    Raises:
        ValueError: If no binding exists for the action.
    """
    for key, bound_action, *_ in ChapgentApp.BINDINGS:
        if bound_action == action:
            return key
    raise ValueError(f"No keybinding found for action: {action}")
