"""Syntax highlighting themes mapped to Textual themes.

This module provides mappings from Textual UI themes to Pygments syntax
highlighting themes. Each Textual theme maps to a complementary Pygments
theme for consistent visual appearance.

The mappings ensure that code blocks use colors that work well with the
overall application theme (dark themes get dark syntax themes, etc.).
"""

# Mapping from Textual theme to Pygments theme
# These mappings provide complementary syntax highlighting colors
THEME_MAPPING: dict[str, str] = {
    # Dark themes
    "textual-dark": "monokai",
    "textual-ansi": "native",
    "nord": "nord",
    "gruvbox": "gruvbox-dark",
    "dracula": "dracula",
    "monokai": "monokai",
    "solarized-dark": "solarized-dark",
    "tokyo-night": "monokai",  # No exact match, monokai is a good dark fallback
    "rose-pine": "monokai",  # No exact match, monokai is a good dark fallback
    # Light themes
    "textual-light": "friendly",
    "solarized-light": "solarized-light",
}

# Default fallback themes when no mapping exists
DEFAULT_DARK_THEME = "monokai"
DEFAULT_LIGHT_THEME = "friendly"

# Theme indicators for light theme detection
LIGHT_THEME_INDICATORS = frozenset(
    {
        "light",
        "solarized-light",
    }
)


def get_syntax_theme(textual_theme: str) -> str:
    """Get the Pygments theme for a Textual theme.

    This function looks up the corresponding Pygments syntax highlighting
    theme for a given Textual UI theme. If no direct mapping exists, it
    uses heuristics based on the theme name to return an appropriate fallback.

    Args:
        textual_theme: Name of the Textual theme (e.g., "textual-dark", "nord").

    Returns:
        Corresponding Pygments theme name (e.g., "monokai", "friendly").

    Examples:
        >>> get_syntax_theme("textual-dark")
        'monokai'
        >>> get_syntax_theme("solarized-light")
        'solarized-light'
        >>> get_syntax_theme("unknown-dark-theme")
        'monokai'
    """
    # Direct mapping lookup
    if textual_theme in THEME_MAPPING:
        return THEME_MAPPING[textual_theme]

    # Heuristic: check if theme name indicates light or dark
    if is_dark_theme(textual_theme):
        return DEFAULT_DARK_THEME
    return DEFAULT_LIGHT_THEME


def is_dark_theme(textual_theme: str) -> bool:
    """Check if a Textual theme is a dark theme.

    This function determines whether a theme is dark by checking for
    light theme indicators in the theme name. Themes are assumed to be
    dark unless they explicitly indicate being light.

    Args:
        textual_theme: Name of the Textual theme.

    Returns:
        True if the theme is dark (default), False if light.

    Examples:
        >>> is_dark_theme("textual-dark")
        True
        >>> is_dark_theme("textual-light")
        False
        >>> is_dark_theme("solarized-light")
        False
        >>> is_dark_theme("nord")
        True
    """
    theme_lower = textual_theme.lower()
    return not any(indicator in theme_lower for indicator in LIGHT_THEME_INDICATORS)
