"""Tests for the error recovery system."""

from __future__ import annotations

import json

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st
from pygent.core.recovery import (
    ERROR_PATTERNS,
    MESSAGE_PATTERNS,
    ErrorRecovery,
    ErrorType,
    RecoveryAction,
)


class TestErrorType:
    """Tests for ErrorType enum."""

    def test_error_type_values(self) -> None:
        """Test that all error types have expected values."""
        assert ErrorType.FILE_NOT_FOUND.value == "file_not_found"
        assert ErrorType.PERMISSION_DENIED.value == "permission_denied"
        assert ErrorType.GIT_NOT_A_REPOSITORY.value == "git_not_a_repository"
        assert ErrorType.TIMEOUT.value == "timeout"
        assert ErrorType.CONNECTION_ERROR.value == "connection_error"
        assert ErrorType.UNKNOWN.value == "unknown"

    def test_error_type_is_str_enum(self) -> None:
        """Test that ErrorType is a string enum."""
        assert isinstance(ErrorType.FILE_NOT_FOUND, str)
        # str() on StrEnum includes class name, but .value gives the string value
        assert ErrorType.FILE_NOT_FOUND.value == "file_not_found"

    def test_all_error_types_exist(self) -> None:
        """Test all expected error types are defined."""
        expected = {
            "FILE_NOT_FOUND",
            "PERMISSION_DENIED",
            "IS_A_DIRECTORY",
            "FILE_EXISTS",
            "NOT_A_DIRECTORY",
            "GIT_NOT_A_REPOSITORY",
            "GIT_CONFLICT",
            "GIT_NO_REMOTE",
            "MODULE_NOT_FOUND",
            "TIMEOUT",
            "CONNECTION_ERROR",
            "SYNTAX_ERROR",
            "JSON_DECODE_ERROR",
            "INVALID_ARGUMENT",
            "UNKNOWN",
        }
        actual = {e.name for e in ErrorType}
        assert expected == actual


class TestRecoveryAction:
    """Tests for RecoveryAction dataclass."""

    def test_recovery_action_defaults(self) -> None:
        """Test default values for RecoveryAction."""
        action = RecoveryAction(
            error_type=ErrorType.UNKNOWN,
            should_retry=False,
        )
        assert action.error_type == ErrorType.UNKNOWN
        assert action.should_retry is False
        assert action.suggestions == []
        assert action.modified_args is None
        assert action.similar_paths == []

    def test_recovery_action_with_suggestions(self) -> None:
        """Test RecoveryAction with suggestions."""
        action = RecoveryAction(
            error_type=ErrorType.FILE_NOT_FOUND,
            should_retry=False,
            suggestions=["Check the path.", "Use find_files."],
        )
        assert len(action.suggestions) == 2
        assert "Check the path." in action.suggestions

    def test_recovery_action_with_modified_args(self) -> None:
        """Test RecoveryAction with modified arguments."""
        action = RecoveryAction(
            error_type=ErrorType.TIMEOUT,
            should_retry=True,
            modified_args={"timeout": 60},
        )
        assert action.should_retry is True
        assert action.modified_args == {"timeout": 60}

    def test_recovery_action_with_similar_paths(self) -> None:
        """Test RecoveryAction with similar paths."""
        action = RecoveryAction(
            error_type=ErrorType.FILE_NOT_FOUND,
            should_retry=False,
            similar_paths=["test.py", "tests.py"],
        )
        assert len(action.similar_paths) == 2


class TestErrorPatterns:
    """Tests for ERROR_PATTERNS dictionary."""

    def test_file_not_found_pattern(self) -> None:
        """Test FileNotFoundError pattern."""
        pattern = ERROR_PATTERNS["FileNotFoundError"]
        assert pattern["type"] == ErrorType.FILE_NOT_FOUND
        assert pattern["auto_retry"] is False
        assert len(pattern["suggest"]) >= 1

    def test_permission_error_pattern(self) -> None:
        """Test PermissionError pattern."""
        pattern = ERROR_PATTERNS["PermissionError"]
        assert pattern["type"] == ErrorType.PERMISSION_DENIED
        assert pattern["auto_retry"] is False

    def test_timeout_error_pattern(self) -> None:
        """Test TimeoutError pattern."""
        pattern = ERROR_PATTERNS["TimeoutError"]
        assert pattern["type"] == ErrorType.TIMEOUT
        assert pattern["auto_retry"] is True

    def test_connection_error_pattern(self) -> None:
        """Test ConnectionError pattern."""
        pattern = ERROR_PATTERNS["ConnectionError"]
        assert pattern["type"] == ErrorType.CONNECTION_ERROR
        assert pattern["auto_retry"] is True

    def test_git_error_pattern(self) -> None:
        """Test GitError pattern."""
        pattern = ERROR_PATTERNS["GitError"]
        assert pattern["type"] == ErrorType.GIT_NOT_A_REPOSITORY
        assert "git" in pattern["suggest"][0].lower()

    def test_all_patterns_have_required_keys(self) -> None:
        """Test all patterns have required keys."""
        for name, pattern in ERROR_PATTERNS.items():
            assert "type" in pattern, f"{name} missing 'type'"
            assert "suggest" in pattern, f"{name} missing 'suggest'"
            assert "auto_retry" in pattern, f"{name} missing 'auto_retry'"
            assert isinstance(pattern["type"], ErrorType), f"{name} type is not ErrorType"
            assert isinstance(pattern["suggest"], list), f"{name} suggest is not a list"
            assert isinstance(pattern["auto_retry"], bool), f"{name} auto_retry is not bool"


class TestMessagePatterns:
    """Tests for MESSAGE_PATTERNS list."""

    def test_message_patterns_structure(self) -> None:
        """Test MESSAGE_PATTERNS have correct structure."""
        for pattern, error_type, suggestions in MESSAGE_PATTERNS:
            assert hasattr(pattern, "search"), "Pattern should be compiled regex"
            assert isinstance(error_type, ErrorType)
            assert isinstance(suggestions, list)
            assert len(suggestions) >= 1

    def test_file_not_found_message_pattern(self) -> None:
        """Test 'No such file' message pattern."""
        for pattern, error_type, _ in MESSAGE_PATTERNS:
            if "such file" in pattern.pattern.lower():
                match = pattern.search("No such file or directory: /tmp/test.txt")
                assert match is not None
                assert error_type == ErrorType.FILE_NOT_FOUND
                return
        pytest.fail("No 'file not found' message pattern found")

    def test_git_repository_message_pattern(self) -> None:
        """Test 'not a git repository' message pattern."""
        for pattern, error_type, _ in MESSAGE_PATTERNS:
            if "git repository" in pattern.pattern.lower():
                match = pattern.search("fatal: not a git repository (or any of the parent directories)")
                assert match is not None
                assert error_type == ErrorType.GIT_NOT_A_REPOSITORY
                return
        pytest.fail("No 'git repository' message pattern found")

    def test_timeout_message_pattern(self) -> None:
        """Test timeout message pattern."""
        for pattern, error_type, _ in MESSAGE_PATTERNS:
            if "time" in pattern.pattern.lower() and "out" in pattern.pattern.lower():
                match = pattern.search("Operation timed out after 30 seconds")
                assert match is not None
                assert error_type == ErrorType.TIMEOUT
                return
        pytest.fail("No 'timeout' message pattern found")


class TestErrorRecovery:
    """Tests for ErrorRecovery class."""

    @pytest.fixture
    def recovery(self) -> ErrorRecovery:
        """Create ErrorRecovery instance."""
        return ErrorRecovery()

    def test_handle_file_not_found(self, recovery: ErrorRecovery) -> None:
        """Test handling FileNotFoundError."""
        error = FileNotFoundError("File not found: /tmp/test.txt")
        action = recovery.handle_tool_error("read_file", error)

        assert action.error_type == ErrorType.FILE_NOT_FOUND
        assert action.should_retry is False
        assert len(action.suggestions) >= 1

    def test_handle_permission_error(self, recovery: ErrorRecovery) -> None:
        """Test handling PermissionError."""
        error = PermissionError("Permission denied: /etc/passwd")
        action = recovery.handle_tool_error("edit_file", error)

        assert action.error_type == ErrorType.PERMISSION_DENIED
        assert action.should_retry is False

    def test_handle_is_a_directory_error(self, recovery: ErrorRecovery) -> None:
        """Test handling IsADirectoryError."""
        error = IsADirectoryError("Is a directory: /tmp")
        action = recovery.handle_tool_error("read_file", error)

        assert action.error_type == ErrorType.IS_A_DIRECTORY
        assert action.should_retry is False

    def test_handle_file_exists_error(self, recovery: ErrorRecovery) -> None:
        """Test handling FileExistsError."""
        error = FileExistsError("File already exists: /tmp/test.txt")
        action = recovery.handle_tool_error("create_file", error)

        assert action.error_type == ErrorType.FILE_EXISTS
        assert action.should_retry is False

    def test_handle_timeout_error(self, recovery: ErrorRecovery) -> None:
        """Test handling TimeoutError."""
        error = TimeoutError("Operation timed out")
        action = recovery.handle_tool_error("shell", error)

        assert action.error_type == ErrorType.TIMEOUT
        assert action.should_retry is True

    def test_handle_connection_error(self, recovery: ErrorRecovery) -> None:
        """Test handling ConnectionError."""
        error = ConnectionError("Connection refused")
        action = recovery.handle_tool_error("web_fetch", error)

        assert action.error_type == ErrorType.CONNECTION_ERROR
        assert action.should_retry is True

    def test_handle_value_error(self, recovery: ErrorRecovery) -> None:
        """Test handling ValueError."""
        error = ValueError("Invalid value provided")
        action = recovery.handle_tool_error("some_tool", error)

        assert action.error_type == ErrorType.INVALID_ARGUMENT
        assert action.should_retry is False

    def test_handle_type_error(self, recovery: ErrorRecovery) -> None:
        """Test handling TypeError."""
        error = TypeError("Expected str, got int")
        action = recovery.handle_tool_error("some_tool", error)

        assert action.error_type == ErrorType.INVALID_ARGUMENT
        assert action.should_retry is False

    def test_handle_json_decode_error(self, recovery: ErrorRecovery) -> None:
        """Test handling json.JSONDecodeError."""
        error = json.JSONDecodeError("Invalid JSON", "{invalid", 0)
        action = recovery.handle_tool_error("web_fetch", error)

        # Note: JSONDecodeError is a subclass of ValueError
        # It may match ValueError pattern first or message pattern
        assert action.error_type in (ErrorType.JSON_DECODE_ERROR, ErrorType.INVALID_ARGUMENT)

    def test_handle_unknown_error(self, recovery: ErrorRecovery) -> None:
        """Test handling unknown error type."""

        class CustomError(Exception):
            pass

        error = CustomError("Something went wrong")
        action = recovery.handle_tool_error("custom_tool", error)

        assert action.error_type == ErrorType.UNKNOWN
        assert action.should_retry is False
        assert "custom_tool" in action.suggestions[0]

    def test_handle_error_with_context(self, recovery: ErrorRecovery) -> None:
        """Test handling error with context information."""
        error = FileNotFoundError("File not found")
        context = {"path": "/home/user/missing.txt"}
        action = recovery.handle_tool_error("read_file", error, context)

        assert action.error_type == ErrorType.FILE_NOT_FOUND
        assert len(action.suggestions) >= 1

    def test_message_pattern_matching_git(self, recovery: ErrorRecovery) -> None:
        """Test message pattern matching for git errors."""

        class GitError(Exception):
            pass

        error = GitError("fatal: not a git repository")
        action = recovery.handle_tool_error("git_status", error)

        assert action.error_type == ErrorType.GIT_NOT_A_REPOSITORY

    def test_message_pattern_matching_module_not_found(self, recovery: ErrorRecovery) -> None:
        """Test message pattern matching for module not found."""

        class UnknownError(Exception):
            pass

        error = UnknownError("No module named 'requests'")
        action = recovery.handle_tool_error("shell", error)

        assert action.error_type == ErrorType.MODULE_NOT_FOUND

    def test_message_pattern_matching_connection_refused(self, recovery: ErrorRecovery) -> None:
        """Test message pattern matching for connection refused."""

        class NetworkError(Exception):
            pass

        error = NetworkError("Connection refused by host")
        action = recovery.handle_tool_error("web_fetch", error)

        assert action.error_type == ErrorType.CONNECTION_ERROR

    def test_git_tool_context_suggestion(self, recovery: ErrorRecovery) -> None:
        """Test git tools get repository-specific suggestions."""

        class UnknownError(Exception):
            pass

        error = UnknownError("fatal: not a git repository")
        action = recovery.handle_tool_error("git_commit", error)

        # Should have git-related suggestions
        suggestions_text = " ".join(action.suggestions).lower()
        assert "git" in suggestions_text or "repository" in suggestions_text


class TestErrorRecoveryCustomPatterns:
    """Tests for custom error pattern registration."""

    @pytest.fixture
    def recovery(self) -> ErrorRecovery:
        """Create ErrorRecovery instance."""
        return ErrorRecovery()

    def test_add_error_pattern(self, recovery: ErrorRecovery) -> None:
        """Test adding custom error pattern."""
        recovery.add_error_pattern(
            "CustomDatabaseError",
            ErrorType.UNKNOWN,
            ["Database connection failed.", "Check database credentials."],
            auto_retry=True,
        )

        class CustomDatabaseError(Exception):
            pass

        error = CustomDatabaseError("DB connection timeout")
        action = recovery.handle_tool_error("db_query", error)

        # Pattern matches by name
        assert "Database" in action.suggestions[0]

    def test_add_message_pattern(self, recovery: ErrorRecovery) -> None:
        """Test adding custom message pattern."""
        recovery.add_message_pattern(
            r"rate limit exceeded",
            ErrorType.TIMEOUT,
            ["API rate limit reached.", "Wait and retry later."],
        )

        class APIError(Exception):
            pass

        error = APIError("Error 429: rate limit exceeded")
        action = recovery.handle_tool_error("api_call", error)

        assert action.error_type == ErrorType.TIMEOUT
        assert "rate limit" in action.suggestions[0].lower()

    def test_custom_pattern_priority(self, recovery: ErrorRecovery) -> None:
        """Test that class-based patterns have priority over message patterns."""
        # Add a specific message pattern
        recovery.add_message_pattern(
            r"special error",
            ErrorType.CONNECTION_ERROR,
            ["Special error occurred."],
        )

        # FileNotFoundError should still match by class
        error = FileNotFoundError("special error in file")
        action = recovery.handle_tool_error("read_file", error)

        # Class-based matching should win
        assert action.error_type == ErrorType.FILE_NOT_FOUND


class TestContextualization:
    """Tests for suggestion contextualization."""

    @pytest.fixture
    def recovery(self) -> ErrorRecovery:
        """Create ErrorRecovery instance."""
        return ErrorRecovery()

    def test_tool_name_in_unknown_error(self, recovery: ErrorRecovery) -> None:
        """Test tool name appears in unknown error suggestions."""

        class UnknownError(Exception):
            pass

        error = UnknownError("Something broke")
        action = recovery.handle_tool_error("my_custom_tool", error)

        assert "my_custom_tool" in action.suggestions[0]

    def test_module_placeholder_replacement(self, recovery: ErrorRecovery) -> None:
        """Test module placeholder is replaced in suggestions."""

        class ModuleError(Exception):
            pass

        error = ModuleError("No module named 'pandas'")
        action = recovery.handle_tool_error("shell", error)

        assert action.error_type == ErrorType.MODULE_NOT_FOUND
        # Check if pandas appears in suggestions (from regex capture)
        suggestions_text = " ".join(action.suggestions)
        # Either the module name is captured or generic suggestion is given
        assert "pandas" in suggestions_text or "module" in suggestions_text.lower()


class TestPropertyBased:
    """Property-based tests using hypothesis."""

    @settings(max_examples=50)
    @given(tool_name=st.from_regex(r"[a-zA-Z][a-zA-Z0-9_]{0,49}", fullmatch=True))
    def test_unknown_error_always_returns_action(self, tool_name: str) -> None:
        """Test that unknown errors always return a RecoveryAction."""
        recovery = ErrorRecovery()

        class RandomError(Exception):
            pass

        error = RandomError("random error")
        action = recovery.handle_tool_error(tool_name, error)

        assert isinstance(action, RecoveryAction)
        assert isinstance(action.error_type, ErrorType)
        assert isinstance(action.should_retry, bool)
        assert isinstance(action.suggestions, list)

    @settings(max_examples=50)
    @given(error_msg=st.text(min_size=1, max_size=200))
    def test_error_message_handling(self, error_msg: str) -> None:
        """Test that any error message is handled gracefully."""
        recovery = ErrorRecovery()

        error = Exception(error_msg)
        action = recovery.handle_tool_error("test_tool", error)

        assert isinstance(action, RecoveryAction)
        assert len(action.suggestions) >= 1

    @settings(max_examples=30)
    @given(
        st.sampled_from(list(ERROR_PATTERNS.keys())).filter(
            lambda x: "." not in x  # Skip dotted names that need imports
        )
    )
    def test_all_builtin_patterns_match(self, pattern_name: str) -> None:
        """Test that builtin exception patterns are recognized."""
        recovery = ErrorRecovery()

        # Create exception instance
        builtins_dict = __builtins__ if isinstance(__builtins__, dict) else vars(__builtins__)
        exc_class = builtins_dict.get(pattern_name)
        if exc_class is None:
            pytest.skip(f"Exception {pattern_name} not found in builtins")

        try:
            error = exc_class("test error")
        except TypeError:
            # Some exceptions require specific args
            pytest.skip(f"Cannot instantiate {pattern_name}")

        action = recovery.handle_tool_error("test_tool", error)

        expected_type = ERROR_PATTERNS[pattern_name]["type"]
        assert action.error_type == expected_type


class TestIntegration:
    """Integration tests for error recovery in tool execution context."""

    @pytest.fixture
    def recovery(self) -> ErrorRecovery:
        """Create ErrorRecovery instance."""
        return ErrorRecovery()

    def test_filesystem_error_flow(self, recovery: ErrorRecovery) -> None:
        """Test error recovery flow for filesystem operations."""
        # Simulate read_file error
        error = FileNotFoundError("No such file: /home/user/project/missing.py")
        context = {"path": "/home/user/project/missing.py"}

        action = recovery.handle_tool_error("read_file", error, context)

        assert action.error_type == ErrorType.FILE_NOT_FOUND
        assert action.should_retry is False
        assert any("find_files" in s or "list_files" in s for s in action.suggestions)

    def test_git_error_flow(self, recovery: ErrorRecovery) -> None:
        """Test error recovery flow for git operations."""
        # Import GitError for testing
        from pygent.tools.git import GitError

        error = GitError("Not a git repository (or any parent up to mount point)")
        action = recovery.handle_tool_error("git_commit", error)

        assert action.error_type == ErrorType.GIT_NOT_A_REPOSITORY
        assert action.should_retry is False
        suggestions_text = " ".join(action.suggestions).lower()
        assert "git" in suggestions_text

    def test_web_timeout_flow(self, recovery: ErrorRecovery) -> None:
        """Test error recovery flow for web timeouts."""
        error = TimeoutError("Request timed out after 30 seconds")
        context = {"url": "https://example.com/api", "timeout": 30}

        action = recovery.handle_tool_error("web_fetch", error, context)

        assert action.error_type == ErrorType.TIMEOUT
        assert action.should_retry is True
        assert any("timeout" in s.lower() for s in action.suggestions)

    def test_shell_module_not_found_flow(self, recovery: ErrorRecovery) -> None:
        """Test error recovery for missing Python module in shell."""

        class ShellError(Exception):
            pass

        error = ShellError("ModuleNotFoundError: No module named 'nonexistent_module'")
        action = recovery.handle_tool_error("shell", error)

        assert action.error_type == ErrorType.MODULE_NOT_FOUND
        suggestions_text = " ".join(action.suggestions).lower()
        assert "module" in suggestions_text or "install" in suggestions_text
