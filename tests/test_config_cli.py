"""Tests for the config CLI commands."""

import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from click.testing import CliRunner
from hypothesis import given, settings
from hypothesis import strategies as st

from pygent.cli import (
    VALID_CONFIG_KEYS,
    _convert_value,
    _format_toml_value,
    _get_config_paths,
    _write_default_config,
    _write_toml,
    _write_toml_section,
    cli,
)


class TestGetConfigPaths:
    """Tests for _get_config_paths helper."""

    def test_returns_tuple_of_paths(self):
        """Test that function returns tuple of two Path objects."""
        user_config, project_config = _get_config_paths()

        assert isinstance(user_config, Path)
        assert isinstance(project_config, Path)

    def test_user_config_path_structure(self):
        """Test user config path is in ~/.config/pygent/."""
        user_config, _ = _get_config_paths()

        assert user_config.name == "config.toml"
        assert user_config.parent.name == "pygent"
        assert user_config.parent.parent.name == ".config"

    def test_project_config_path_structure(self):
        """Test project config path is in .pygent/."""
        _, project_config = _get_config_paths()

        assert project_config.name == "config.toml"
        assert project_config.parent.name == ".pygent"


class TestValidConfigKeys:
    """Tests for VALID_CONFIG_KEYS constant."""

    def test_contains_llm_keys(self):
        """Test LLM config keys are present."""
        assert "llm.provider" in VALID_CONFIG_KEYS
        assert "llm.model" in VALID_CONFIG_KEYS
        assert "llm.max_tokens" in VALID_CONFIG_KEYS
        assert "llm.api_key" in VALID_CONFIG_KEYS

    def test_contains_permission_keys(self):
        """Test permission config keys are present."""
        assert "permissions.auto_approve_low_risk" in VALID_CONFIG_KEYS
        assert "permissions.session_override_allowed" in VALID_CONFIG_KEYS

    def test_contains_tui_keys(self):
        """Test TUI config keys are present."""
        assert "tui.theme" in VALID_CONFIG_KEYS
        assert "tui.show_tool_panel" in VALID_CONFIG_KEYS
        assert "tui.show_sidebar" in VALID_CONFIG_KEYS

    def test_contains_system_prompt_keys(self):
        """Test system prompt config keys are present."""
        assert "system_prompt.content" in VALID_CONFIG_KEYS
        assert "system_prompt.file" in VALID_CONFIG_KEYS
        assert "system_prompt.append" in VALID_CONFIG_KEYS
        assert "system_prompt.mode" in VALID_CONFIG_KEYS

    def test_is_frozen_set(self):
        """Test that VALID_CONFIG_KEYS is a set (for fast lookup)."""
        assert isinstance(VALID_CONFIG_KEYS, set)


class TestConvertValue:
    """Tests for _convert_value helper."""

    def test_converts_max_tokens_to_int(self):
        """Test integer conversion for max_tokens."""
        result = _convert_value("llm.max_tokens", "8192")
        assert result == 8192
        assert isinstance(result, int)

    def test_invalid_max_tokens_raises(self):
        """Test invalid integer raises ClickException."""
        import click

        with pytest.raises(click.ClickException) as exc_info:
            _convert_value("llm.max_tokens", "not_a_number")

        assert "Invalid integer" in str(exc_info.value)

    def test_converts_true_values_to_bool(self):
        """Test various truthy string values convert to True."""
        for value in ("true", "True", "TRUE", "1", "yes", "on"):
            result = _convert_value("tui.show_tool_panel", value)
            assert result is True

    def test_converts_false_values_to_bool(self):
        """Test various falsy string values convert to False."""
        for value in ("false", "False", "FALSE", "0", "no", "off"):
            result = _convert_value("tui.show_tool_panel", value)
            assert result is False

    def test_invalid_bool_raises(self):
        """Test invalid boolean value raises ClickException."""
        import click

        with pytest.raises(click.ClickException) as exc_info:
            _convert_value("tui.show_tool_panel", "maybe")

        assert "Invalid boolean" in str(exc_info.value)

    def test_validates_mode_values(self):
        """Test system_prompt.mode validation."""
        assert _convert_value("system_prompt.mode", "replace") == "replace"
        assert _convert_value("system_prompt.mode", "append") == "append"

    def test_invalid_mode_raises(self):
        """Test invalid mode value raises ClickException."""
        import click

        with pytest.raises(click.ClickException) as exc_info:
            _convert_value("system_prompt.mode", "invalid")

        assert "Invalid mode" in str(exc_info.value)

    def test_string_values_pass_through(self):
        """Test non-special keys return string as-is."""
        result = _convert_value("llm.model", "claude-3-5-haiku")
        assert result == "claude-3-5-haiku"
        assert isinstance(result, str)


class TestFormatTomlValue:
    """Tests for _format_toml_value helper."""

    def test_formats_true(self):
        """Test True formats as 'true'."""
        assert _format_toml_value(True) == "true"

    def test_formats_false(self):
        """Test False formats as 'false'."""
        assert _format_toml_value(False) == "false"

    def test_formats_int(self):
        """Test integer formats as string."""
        assert _format_toml_value(4096) == "4096"

    def test_formats_string_with_quotes(self):
        """Test string wrapped in quotes."""
        assert _format_toml_value("hello") == '"hello"'

    def test_escapes_quotes_in_string(self):
        """Test quotes are escaped."""
        assert _format_toml_value('say "hello"') == '"say \\"hello\\""'

    def test_escapes_backslashes(self):
        """Test backslashes are escaped."""
        assert _format_toml_value("path\\to\\file") == '"path\\\\to\\\\file"'


class TestWriteTomlSection:
    """Tests for _write_toml_section helper."""

    def test_writes_simple_values(self):
        """Test writing simple key-value pairs."""
        lines: list[str] = []
        data = {"model": "claude", "tokens": 4096}
        _write_toml_section(lines, data, ["llm"])

        output = "\n".join(lines)
        assert "[llm]" in output
        assert 'model = "claude"' in output
        assert "tokens = 4096" in output

    def test_writes_nested_sections(self):
        """Test writing nested sections."""
        lines: list[str] = []
        data = {
            "llm": {"model": "claude"},
            "tui": {"theme": "dark"},
        }
        _write_toml_section(lines, data, [])

        output = "\n".join(lines)
        assert "[llm]" in output
        assert "[tui]" in output
        assert 'model = "claude"' in output
        assert 'theme = "dark"' in output

    def test_empty_data_produces_no_output(self):
        """Test empty data produces no output."""
        lines: list[str] = []
        _write_toml_section(lines, {}, [])
        assert lines == []


class TestWriteToml:
    """Tests for _write_toml helper."""

    def test_writes_valid_toml(self, tmp_path):
        """Test writes valid TOML that can be read back."""
        path = tmp_path / "test.toml"
        data = {
            "llm": {"model": "claude", "max_tokens": 4096},
            "tui": {"show_tool_panel": True},
        }

        _write_toml(path, data)

        # Read it back with tomllib
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib  # type: ignore

        with open(path, "rb") as f:
            loaded = tomllib.load(f)

        assert loaded["llm"]["model"] == "claude"
        assert loaded["llm"]["max_tokens"] == 4096
        assert loaded["tui"]["show_tool_panel"] is True


class TestWriteDefaultConfig:
    """Tests for _write_default_config helper."""

    def test_creates_config_file(self, tmp_path):
        """Test creates config file with content."""
        path = tmp_path / "config.toml"
        _write_default_config(path)

        assert path.exists()
        content = path.read_text()
        assert "[llm]" in content
        assert "[permissions]" in content
        assert "[tui]" in content
        assert "[system_prompt]" in content

    def test_contains_commented_defaults(self, tmp_path):
        """Test contains commented default values."""
        path = tmp_path / "config.toml"
        _write_default_config(path)

        content = path.read_text()
        # All values should be commented out
        assert '# provider = "anthropic"' in content
        assert "# model = " in content
        assert "# max_tokens = " in content


class TestConfigPathCommand:
    """Tests for 'config path' command."""

    def test_shows_user_config_path(self, tmp_path, monkeypatch):
        """Test displays user config path."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "path"])

        assert result.exit_code == 0
        assert "User config:" in result.output
        assert "config.toml" in result.output

    def test_shows_project_config_path(self, tmp_path, monkeypatch):
        """Test displays project config path."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "path"])

        assert result.exit_code == 0
        assert "Project config:" in result.output
        assert ".pygent" in result.output

    def test_shows_exists_status(self, tmp_path, monkeypatch):
        """Test shows [exists] when config files exist."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create user config
        user_config = tmp_path / ".config" / "pygent" / "config.toml"
        user_config.parent.mkdir(parents=True)
        user_config.write_text("[llm]\n")

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "path"])

        assert "[exists]" in result.output

    def test_shows_not_found_status(self, tmp_path, monkeypatch):
        """Test shows [not found] when config files don't exist."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "path"])

        assert "[not found]" in result.output

    def test_shows_priority_info(self):
        """Test shows priority information."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "path"])

        assert result.exit_code == 0
        assert "Priority" in result.output
        assert "Environment variables" in result.output


class TestConfigInitCommand:
    """Tests for 'config init' command."""

    def test_creates_user_config(self, tmp_path, monkeypatch):
        """Test creates user config file."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "init"])

        assert result.exit_code == 0
        assert "Created user config" in result.output

        user_config = tmp_path / ".config" / "pygent" / "config.toml"
        assert user_config.exists()

    def test_creates_project_config_with_flag(self, tmp_path, monkeypatch):
        """Test --project flag creates project config."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "init", "--project"])

        assert result.exit_code == 0
        assert "Created project config" in result.output

        project_config = tmp_path / ".pygent" / "config.toml"
        assert project_config.exists()

    def test_fails_if_exists_without_force(self, tmp_path, monkeypatch):
        """Test fails if config already exists."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create existing config
        user_config = tmp_path / ".config" / "pygent" / "config.toml"
        user_config.parent.mkdir(parents=True)
        user_config.write_text("existing content")

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "init"])

        assert result.exit_code == 1
        assert "already exists" in result.output

    def test_force_overwrites_existing(self, tmp_path, monkeypatch):
        """Test --force overwrites existing config."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create existing config
        user_config = tmp_path / ".config" / "pygent" / "config.toml"
        user_config.parent.mkdir(parents=True)
        user_config.write_text("old content")

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "init", "--force"])

        assert result.exit_code == 0
        assert "Created user config" in result.output

        # Should have new default content
        content = user_config.read_text()
        assert "old content" not in content
        assert "[llm]" in content


class TestConfigEditCommand:
    """Tests for 'config edit' command."""

    def test_opens_editor(self, tmp_path, monkeypatch):
        """Test opens editor with config file."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("EDITOR", "echo")  # echo will just print the path

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "edit"])

        assert result.exit_code == 0

    def test_creates_config_if_not_exists(self, tmp_path, monkeypatch):
        """Test creates config file before editing."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("EDITOR", "echo")

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "edit"])

        assert result.exit_code == 0
        assert "Created" in result.output

        user_config = tmp_path / ".config" / "pygent" / "config.toml"
        assert user_config.exists()

    def test_project_flag_edits_project_config(self, tmp_path, monkeypatch):
        """Test --project flag edits project config."""
        monkeypatch.chdir(tmp_path)
        monkeypatch.setenv("EDITOR", "echo")

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "edit", "--project"])

        assert result.exit_code == 0

        project_config = tmp_path / ".pygent" / "config.toml"
        assert project_config.exists()

    def test_editor_not_found_error(self, tmp_path, monkeypatch):
        """Test error when editor not found."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.setenv("EDITOR", "nonexistent_editor_12345")

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "edit"])

        assert result.exit_code == 1
        assert "not found" in result.output

    def test_uses_visual_fallback(self, tmp_path, monkeypatch):
        """Test falls back to VISUAL if EDITOR not set."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)
        monkeypatch.delenv("EDITOR", raising=False)
        monkeypatch.setenv("VISUAL", "echo")

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "edit"])

        assert result.exit_code == 0


class TestConfigSetCommand:
    """Tests for 'config set' command."""

    def test_sets_string_value(self, tmp_path, monkeypatch):
        """Test setting a string value."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "llm.model", "claude-3-5-haiku"])

        assert result.exit_code == 0
        assert "Set llm.model = claude-3-5-haiku" in result.output

        # Verify file was created and has correct value
        config_path = tmp_path / ".config" / "pygent" / "config.toml"
        assert config_path.exists()

        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib  # type: ignore

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        assert data["llm"]["model"] == "claude-3-5-haiku"

    def test_sets_integer_value(self, tmp_path, monkeypatch):
        """Test setting an integer value."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "llm.max_tokens", "8192"])

        assert result.exit_code == 0
        assert "Set llm.max_tokens = 8192" in result.output

    def test_sets_boolean_value(self, tmp_path, monkeypatch):
        """Test setting a boolean value."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "tui.show_tool_panel", "false"])

        assert result.exit_code == 0
        assert "Set tui.show_tool_panel = False" in result.output

    def test_invalid_key_fails(self, tmp_path, monkeypatch):
        """Test invalid config key fails with error."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "invalid.key", "value"])

        assert result.exit_code == 1
        assert "Invalid config key" in result.output

    def test_project_flag_sets_project_config(self, tmp_path, monkeypatch):
        """Test --project flag sets in project config."""
        monkeypatch.chdir(tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "llm.model", "test", "--project"])

        assert result.exit_code == 0
        assert "project config" in result.output

        project_config = tmp_path / ".pygent" / "config.toml"
        assert project_config.exists()

    def test_preserves_existing_values(self, tmp_path, monkeypatch):
        """Test setting value preserves other existing values."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        # Create existing config
        config_path = tmp_path / ".config" / "pygent" / "config.toml"
        config_path.parent.mkdir(parents=True)
        config_path.write_text('[llm]\nmodel = "existing"\n')

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "llm.max_tokens", "8192"])

        assert result.exit_code == 0

        # Read back and verify both values exist
        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib  # type: ignore

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        assert data["llm"]["model"] == "existing"
        assert data["llm"]["max_tokens"] == 8192


class TestConfigShowCommand:
    """Tests for 'config show' command."""

    @patch("pygent.cli.load_config")
    def test_shows_all_settings(self, mock_load_config):
        """Test shows all configuration settings."""
        from pygent.config.settings import Settings

        mock_load_config.return_value = Settings()

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "show"])

        assert result.exit_code == 0
        assert "LLM" in result.output
        assert "Permissions" in result.output
        assert "TUI" in result.output

    @patch("pygent.cli.load_config")
    def test_shows_custom_values(self, mock_load_config):
        """Test shows custom configuration values."""
        from pygent.config.settings import LLMSettings, Settings

        mock_load_config.return_value = Settings(llm=LLMSettings(model="custom-model", max_tokens=8192))

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "show"])

        assert result.exit_code == 0
        assert "custom-model" in result.output
        assert "8192" in result.output


class TestPropertyBased:
    """Property-based tests using hypothesis."""

    @given(st.text(alphabet=st.characters(codec="utf-8", categories=["L", "N", "P", "S"]), min_size=0, max_size=50))
    @settings(max_examples=50)
    def test_format_toml_value_roundtrip(self, value):
        """Test formatting then parsing gives back original value."""
        formatted = _format_toml_value(value)

        # Should be a valid TOML string
        assert formatted.startswith('"')
        assert formatted.endswith('"')

        # The value should be recoverable (basic check)
        # Unquote and unescape
        inner = formatted[1:-1]
        unescaped = inner.replace('\\"', '"').replace("\\\\", "\\")
        assert unescaped == value

    @given(st.integers(min_value=0, max_value=100000))
    def test_format_toml_value_integer(self, value):
        """Test integer formatting."""
        formatted = _format_toml_value(value)
        assert formatted == str(value)

    @given(st.booleans())
    def test_format_toml_value_boolean(self, value):
        """Test boolean formatting."""
        formatted = _format_toml_value(value)
        assert formatted == ("true" if value else "false")

    @given(
        st.dictionaries(
            keys=st.text(alphabet="abcdefghijklmnopqrstuvwxyz_", min_size=1, max_size=10),
            values=st.one_of(
                st.text(min_size=0, max_size=20),
                st.integers(min_value=0, max_value=10000),
                st.booleans(),
            ),
            min_size=0,
            max_size=5,
        )
    )
    @settings(max_examples=30)
    def test_write_toml_section_produces_valid_output(self, data):
        """Test _write_toml_section produces valid TOML structure."""
        lines: list[str] = []
        _write_toml_section(lines, data, ["test"])

        output = "\n".join(lines)

        # If data is not empty, should have section header
        if data:
            assert "[test]" in output

        # Each key should appear
        for key in data:
            assert key in output


class TestEdgeCases:
    """Edge case tests."""

    def test_set_empty_string_value(self, tmp_path, monkeypatch):
        """Test setting an empty string value."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "llm.model", ""])

        assert result.exit_code == 0

    def test_set_value_with_spaces(self, tmp_path, monkeypatch):
        """Test setting a value containing spaces."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "system_prompt.content", "hello world"])

        assert result.exit_code == 0
        assert "hello world" in result.output

    def test_set_value_with_special_chars(self, tmp_path, monkeypatch):
        """Test setting a value with special characters."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "system_prompt.content", "path/to/file"])

        assert result.exit_code == 0

    def test_config_help_shows_all_subcommands(self):
        """Test config --help lists all subcommands."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "--help"])

        assert result.exit_code == 0
        assert "show" in result.output
        assert "path" in result.output
        assert "edit" in result.output
        assert "init" in result.output
        assert "set" in result.output

    def test_config_set_help_shows_examples(self):
        """Test 'config set --help' shows usage examples."""
        runner = CliRunner()
        result = runner.invoke(cli, ["config", "set", "--help"])

        assert result.exit_code == 0
        assert "KEY" in result.output
        assert "VALUE" in result.output


class TestIntegration:
    """Integration tests for config CLI commands."""

    def test_init_then_set_then_show(self, tmp_path, monkeypatch):
        """Test full workflow: init, set value, show config."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()

        # Init
        result = runner.invoke(cli, ["config", "init"])
        assert result.exit_code == 0

        # Set value
        result = runner.invoke(cli, ["config", "set", "llm.model", "test-model"])
        assert result.exit_code == 0

        # Show
        with patch("pygent.cli.load_config") as mock_load:
            from pygent.config.settings import LLMSettings, Settings

            mock_load.return_value = Settings(llm=LLMSettings(model="test-model"))
            result = runner.invoke(cli, ["config", "show"])

        assert result.exit_code == 0
        assert "test-model" in result.output

    def test_multiple_sets_accumulate(self, tmp_path, monkeypatch):
        """Test multiple set commands accumulate values."""
        monkeypatch.setattr(Path, "home", lambda: tmp_path)

        runner = CliRunner()

        # Set multiple values
        runner.invoke(cli, ["config", "set", "llm.model", "model1"])
        runner.invoke(cli, ["config", "set", "llm.max_tokens", "8192"])
        runner.invoke(cli, ["config", "set", "tui.theme", "dark"])

        # Read back
        config_path = tmp_path / ".config" / "pygent" / "config.toml"

        if sys.version_info >= (3, 11):
            import tomllib
        else:
            import tomli as tomllib  # type: ignore

        with open(config_path, "rb") as f:
            data = tomllib.load(f)

        assert data["llm"]["model"] == "model1"
        assert data["llm"]["max_tokens"] == 8192
        assert data["tui"]["theme"] == "dark"
