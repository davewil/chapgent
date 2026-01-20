"""Tests for syntax theme integration.

These tests focus on behavioral validation of the theme mapping system,
ensuring Textual themes correctly map to Pygments syntax highlighting themes.
"""

import pytest
from hypothesis import given
from hypothesis import settings as hypothesis_settings
from hypothesis import strategies as st

from chapgent.config.settings import VALID_THEMES
from chapgent.tui.themes import (
    DEFAULT_DARK_THEME,
    DEFAULT_LIGHT_THEME,
    THEME_MAPPING,
    get_syntax_theme,
    is_dark_theme,
)

# =============================================================================
# Theme Mapping Tests
# =============================================================================


class TestThemeMapping:
    """Tests for the THEME_MAPPING constant."""

    def test_all_valid_themes_have_mapping(self):
        """All themes in VALID_THEMES should have a mapping."""
        for theme in VALID_THEMES:
            # get_syntax_theme should return a value for all valid themes
            result = get_syntax_theme(theme)
            assert isinstance(result, str)
            assert len(result) > 0

    def test_mappings_are_strings(self):
        """All mappings should be strings."""
        for textual_theme, pygments_theme in THEME_MAPPING.items():
            assert isinstance(textual_theme, str)
            assert isinstance(pygments_theme, str)

    def test_known_mappings(self):
        """Test specific known mappings for correctness."""
        expected_mappings = {
            "textual-dark": "monokai",
            "textual-light": "friendly",
            "dracula": "dracula",
            "nord": "nord",
            "solarized-light": "solarized-light",
            "solarized-dark": "solarized-dark",
            "gruvbox": "gruvbox-dark",
        }
        for textual_theme, expected_pygments in expected_mappings.items():
            assert get_syntax_theme(textual_theme) == expected_pygments


# =============================================================================
# get_syntax_theme Tests
# =============================================================================


class TestGetSyntaxTheme:
    """Tests for the get_syntax_theme function."""

    @pytest.mark.parametrize(
        "textual_theme,expected_pygments",
        [
            ("textual-dark", "monokai"),
            ("textual-light", "friendly"),
            ("dracula", "dracula"),
            ("nord", "nord"),
            ("monokai", "monokai"),
        ],
    )
    def test_direct_mappings(self, textual_theme, expected_pygments):
        """Direct mappings should return the correct Pygments theme."""
        assert get_syntax_theme(textual_theme) == expected_pygments

    def test_unknown_dark_theme_returns_default_dark(self):
        """Unknown themes without 'light' indicator should return dark fallback."""
        result = get_syntax_theme("unknown-dark-theme")
        assert result == DEFAULT_DARK_THEME

    def test_unknown_light_theme_returns_default_light(self):
        """Unknown themes with 'light' indicator should return light fallback."""
        result = get_syntax_theme("some-light-theme")
        assert result == DEFAULT_LIGHT_THEME

    def test_case_sensitivity(self):
        """Theme lookup should be case-sensitive for direct mappings."""
        # Uppercase version won't be in direct mapping
        result = get_syntax_theme("TEXTUAL-DARK")
        # Should fall back to heuristic - no 'light' indicator, so dark
        assert result == DEFAULT_DARK_THEME


# =============================================================================
# is_dark_theme Tests
# =============================================================================


class TestIsDarkTheme:
    """Tests for the is_dark_theme function."""

    @pytest.mark.parametrize(
        "theme,expected_is_dark",
        [
            # Dark themes
            ("textual-dark", True),
            ("dracula", True),
            ("nord", True),
            ("monokai", True),
            ("tokyo-night", True),
            ("rose-pine", True),
            ("gruvbox", True),
            ("solarized-dark", True),
            # Light themes
            ("textual-light", False),
            ("solarized-light", False),
        ],
    )
    def test_theme_classification(self, theme, expected_is_dark):
        """Themes should be correctly classified as dark or light."""
        assert is_dark_theme(theme) == expected_is_dark

    def test_case_insensitive_light_detection(self):
        """Light theme detection should be case-insensitive."""
        assert is_dark_theme("TEXTUAL-LIGHT") is False
        assert is_dark_theme("Solarized-Light") is False

    def test_unknown_theme_defaults_to_dark(self):
        """Unknown themes without light indicator should be considered dark."""
        assert is_dark_theme("my-custom-theme") is True


# =============================================================================
# Default Constants Tests
# =============================================================================


class TestDefaultConstants:
    """Tests for default theme constants."""

    def test_default_dark_theme_is_valid_pygments(self):
        """Default dark theme should be a valid Pygments theme name."""
        assert isinstance(DEFAULT_DARK_THEME, str)
        assert len(DEFAULT_DARK_THEME) > 0
        assert DEFAULT_DARK_THEME == "monokai"

    def test_default_light_theme_is_valid_pygments(self):
        """Default light theme should be a valid Pygments theme name."""
        assert isinstance(DEFAULT_LIGHT_THEME, str)
        assert len(DEFAULT_LIGHT_THEME) > 0
        assert DEFAULT_LIGHT_THEME == "friendly"


# =============================================================================
# Property-Based Tests
# =============================================================================


class TestPropertyBased:
    """Property-based tests using Hypothesis."""

    @given(st.sampled_from(list(VALID_THEMES)))
    @hypothesis_settings(max_examples=20)
    def test_all_valid_themes_return_string(self, theme: str):
        """get_syntax_theme should return a non-empty string for all valid themes."""
        result = get_syntax_theme(theme)
        assert isinstance(result, str)
        assert len(result) > 0

    @given(st.sampled_from(list(VALID_THEMES)))
    @hypothesis_settings(max_examples=20)
    def test_is_dark_theme_returns_bool(self, theme: str):
        """is_dark_theme should return a boolean for all valid themes."""
        result = is_dark_theme(theme)
        assert isinstance(result, bool)

    @given(st.text(min_size=1, max_size=50))
    @hypothesis_settings(max_examples=30)
    def test_get_syntax_theme_never_raises(self, theme: str):
        """get_syntax_theme should never raise for any string input."""
        result = get_syntax_theme(theme)
        assert isinstance(result, str)

    @given(st.text(min_size=1, max_size=50))
    @hypothesis_settings(max_examples=30)
    def test_is_dark_theme_never_raises(self, theme: str):
        """is_dark_theme should never raise for any string input."""
        result = is_dark_theme(theme)
        assert isinstance(result, bool)


# =============================================================================
# Edge Cases Tests
# =============================================================================


class TestEdgeCases:
    """Tests for edge cases and boundary conditions."""

    def test_empty_theme_name(self):
        """Empty string should be handled gracefully."""
        result = get_syntax_theme("")
        # No 'light' in empty string, so dark
        assert result == DEFAULT_DARK_THEME

    def test_whitespace_theme_name(self):
        """Whitespace-only theme name should be handled gracefully."""
        result = get_syntax_theme("   ")
        assert result == DEFAULT_DARK_THEME

    def test_theme_with_light_substring(self):
        """Themes containing 'light' substring should be detected as light."""
        assert is_dark_theme("highlight-mode") is False  # contains 'light'
        assert get_syntax_theme("highlight-mode") == DEFAULT_LIGHT_THEME

    def test_theme_with_unicode(self):
        """Unicode theme names should be handled gracefully."""
        result = get_syntax_theme("theme-\u2605-stars")
        assert isinstance(result, str)

    def test_light_indicator_at_different_positions(self):
        """Light indicator should work regardless of position."""
        assert is_dark_theme("light-theme") is False
        assert is_dark_theme("my-light") is False
        assert is_dark_theme("lightweight") is False  # contains 'light'


# =============================================================================
# Integration Tests
# =============================================================================


class TestIntegration:
    """Integration tests for theme system with markdown rendering."""

    def test_syntax_theme_with_markdown_config(self):
        """Syntax theme should be usable with MarkdownConfig."""
        from chapgent.tui.markdown import MarkdownConfig

        for textual_theme in ["textual-dark", "textual-light", "nord"]:
            syntax_theme = get_syntax_theme(textual_theme)
            config = MarkdownConfig(code_theme=syntax_theme)
            assert config.code_theme == syntax_theme

    def test_syntax_theme_consistency_for_all_valid_themes(self):
        """All valid themes should produce consistent dark/light classification."""
        dark_themes = [t for t in VALID_THEMES if is_dark_theme(t)]
        light_themes = [t for t in VALID_THEMES if not is_dark_theme(t)]

        # Dark themes should get dark syntax themes
        for theme in dark_themes:
            syntax = get_syntax_theme(theme)
            # Should not be the light default unless explicitly mapped
            if theme not in THEME_MAPPING:
                assert syntax == DEFAULT_DARK_THEME

        # Light themes should get light syntax themes
        for theme in light_themes:
            syntax = get_syntax_theme(theme)
            # Should not be the dark default unless explicitly mapped
            if theme not in THEME_MAPPING:
                assert syntax == DEFAULT_LIGHT_THEME
