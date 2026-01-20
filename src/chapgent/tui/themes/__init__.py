"""Theme utilities for syntax highlighting.

This module provides mappings from Textual UI themes to Pygments syntax
highlighting themes, ensuring visual consistency throughout the TUI.
"""

from chapgent.tui.themes.syntax import (
    DEFAULT_DARK_THEME,
    DEFAULT_LIGHT_THEME,
    THEME_MAPPING,
    get_syntax_theme,
    is_dark_theme,
)

__all__ = [
    "DEFAULT_DARK_THEME",
    "DEFAULT_LIGHT_THEME",
    "THEME_MAPPING",
    "get_syntax_theme",
    "is_dark_theme",
]
