"""Behavioral tests for search tools.

Tests verify user-facing behavior:
- grep_search: Search file contents for patterns
- find_files: Find files matching a glob pattern
- find_definition: Find symbol definitions in code
"""

import json

import pytest

from chapgent.tools.search import find_definition, find_files, grep_search

# =============================================================================
# grep_search - User can search file contents
# =============================================================================


class TestGrepSearch:
    """User can search files for text patterns."""

    @pytest.mark.asyncio
    async def test_finds_matching_text(self, tmp_path):
        """Basic text search finds matches."""
        (tmp_path / "app.py").write_text("def hello():\n    print('hello')\n")
        (tmp_path / "other.py").write_text("def world():\n    pass\n")

        result = await grep_search("hello", str(tmp_path))
        data = json.loads(result)

        assert data["count"] >= 1
        assert any("app.py" in r["file"] for r in data["results"])

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_matches(self, tmp_path):
        """Search with no matches returns empty results."""
        (tmp_path / "test.txt").write_text("nothing here")

        result = await grep_search("xyz123notfound", str(tmp_path))
        data = json.loads(result)

        assert data["results"] == []

    @pytest.mark.asyncio
    async def test_filters_by_file_extension(self, tmp_path):
        """File pattern filters results to matching files."""
        (tmp_path / "code.py").write_text("def func(): pass")
        (tmp_path / "code.txt").write_text("def func(): pass")

        result = await grep_search("def", str(tmp_path), file_pattern="*.py")
        data = json.loads(result)

        for r in data["results"]:
            assert r["file"].endswith(".py")

    @pytest.mark.asyncio
    async def test_case_insensitive_search(self, tmp_path):
        """Case-insensitive search finds all case variations."""
        (tmp_path / "test.txt").write_text("Hello World\nhello world\nHELLO")

        result = await grep_search("hello", str(tmp_path), ignore_case=True)
        data = json.loads(result)

        assert data["count"] == 3

    @pytest.mark.asyncio
    async def test_limits_results(self, tmp_path):
        """Max results limits output count."""
        content = "\n".join([f"match line {i}" for i in range(50)])
        (tmp_path / "big.txt").write_text(content)

        result = await grep_search("match", str(tmp_path), max_results=10)
        data = json.loads(result)

        assert data["count"] == 10

    @pytest.mark.asyncio
    async def test_supports_regex_patterns(self, tmp_path):
        """Regex patterns work for complex searches."""
        (tmp_path / "code.py").write_text("def foo_bar():\ndef baz_qux():\n")

        result = await grep_search(r"def \w+_\w+", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 2

    @pytest.mark.asyncio
    async def test_skips_hidden_directories(self, tmp_path):
        """Hidden directories (.git, .hidden) are not searched."""
        hidden = tmp_path / ".hidden"
        hidden.mkdir()
        (hidden / "secret.txt").write_text("findme")
        (tmp_path / "visible.txt").write_text("findme")

        result = await grep_search("findme", str(tmp_path))
        data = json.loads(result)

        # Should only find in visible.txt
        assert data["count"] == 1
        assert ".hidden" not in data["results"][0]["file"]

    @pytest.mark.asyncio
    async def test_skips_node_modules(self, tmp_path):
        """node_modules directory is not searched (when using Python backend)."""
        from unittest.mock import patch

        # Create actual node_modules directory (not node_modules_dir)
        nm = tmp_path / "project" / "node_modules"
        nm.mkdir(parents=True)
        (nm / "package.js").write_text("findme")
        (tmp_path / "project" / "app.js").write_text("findme")

        # Force Python backend to test our filtering
        with patch("chapgent.tools.search._is_ripgrep_available", return_value=False):
            result = await grep_search("findme", str(tmp_path / "project"))
            data = json.loads(result)

        # Should only find in app.js, node_modules should be skipped
        assert data["count"] == 1
        assert "app.js" in data["results"][0]["file"]

    @pytest.mark.asyncio
    async def test_returns_line_numbers(self, tmp_path):
        """Results include accurate line numbers."""
        (tmp_path / "code.py").write_text("line one\nline two\nline three")

        result = await grep_search("two", str(tmp_path))
        data = json.loads(result)

        assert data["results"][0]["line"] == 2


# =============================================================================
# find_files - User can find files by pattern
# =============================================================================


class TestFindFiles:
    """User can find files matching glob patterns."""

    @pytest.mark.asyncio
    async def test_finds_files_by_extension(self, tmp_path):
        """Finds files matching extension pattern."""
        (tmp_path / "app.py").write_text("")
        (tmp_path / "test.py").write_text("")
        (tmp_path / "readme.md").write_text("")

        result = await find_files("*.py", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 2
        assert all(f.endswith(".py") for f in data["files"])

    @pytest.mark.asyncio
    async def test_searches_recursively(self, tmp_path):
        """Finds files in subdirectories."""
        subdir = tmp_path / "src"
        subdir.mkdir(parents=True)
        (tmp_path / "root.py").write_text("")
        (subdir / "nested.py").write_text("")

        result = await find_files("**/*.py", str(tmp_path))
        data = json.loads(result)

        filenames = [f.split("/")[-1] for f in data["files"]]
        assert "root.py" in filenames or "nested.py" in filenames

    @pytest.mark.asyncio
    async def test_returns_empty_when_no_matches(self, tmp_path):
        """Returns empty list when no files match."""
        (tmp_path / "only.txt").write_text("")

        result = await find_files("*.py", str(tmp_path))
        data = json.loads(result)

        assert data["files"] == []

    @pytest.mark.asyncio
    async def test_respects_max_depth(self, tmp_path):
        """Max depth limits search depth."""
        deep = tmp_path / "a" / "b" / "c"
        deep.mkdir(parents=True)
        (tmp_path / "root.py").write_text("")
        (deep / "deep.py").write_text("")

        # With max_depth=1, should only find root.py
        result = await find_files("*.py", str(tmp_path), max_depth=1)
        data = json.loads(result)

        filenames = [f.split("/")[-1] for f in data["files"]]
        assert "root.py" in filenames
        assert "deep.py" not in filenames

    @pytest.mark.asyncio
    async def test_can_filter_files_only(self, tmp_path):
        """File type filter can find only files (not directories)."""
        (tmp_path / "subdir").mkdir()
        (tmp_path / "file.txt").write_text("")

        result = await find_files("*", str(tmp_path), file_type="f")
        data = json.loads(result)

        # Should only find file.txt, not subdir
        assert data["count"] >= 1
        assert any("file.txt" in f for f in data["files"])

    @pytest.mark.asyncio
    async def test_skips_hidden_directories(self, tmp_path):
        """Hidden directories are skipped."""
        hidden = tmp_path / ".git"
        hidden.mkdir()
        (hidden / "config.py").write_text("")
        (tmp_path / "app.py").write_text("")

        result = await find_files("*.py", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 1
        assert ".git" not in data["files"][0]

    @pytest.mark.asyncio
    async def test_skips_pycache(self, tmp_path):
        """__pycache__ directories are skipped."""
        cache = tmp_path / "__pycache__"
        cache.mkdir()
        (cache / "module.cpython-311.pyc").write_text("")
        (tmp_path / "module.py").write_text("")

        result = await find_files("*", str(tmp_path))
        data = json.loads(result)

        assert not any("__pycache__" in f for f in data["files"])


# =============================================================================
# find_definition - User can find where symbols are defined
# =============================================================================


class TestFindDefinition:
    """User can find symbol definitions in code."""

    @pytest.mark.asyncio
    async def test_finds_python_function(self, tmp_path):
        """Finds Python function definitions."""
        (tmp_path / "module.py").write_text("def calculate_total(items):\n    return sum(items)\n")

        result = await find_definition("calculate_total", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 1
        assert data["definitions"][0]["type"] == "function"
        assert "def calculate_total" in data["definitions"][0]["context"]

    @pytest.mark.asyncio
    async def test_finds_python_async_function(self, tmp_path):
        """Finds Python async function definitions."""
        (tmp_path / "async_module.py").write_text("async def fetch_data():\n    return await api()\n")

        result = await find_definition("fetch_data", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 1
        assert data["definitions"][0]["type"] == "async function"

    @pytest.mark.asyncio
    async def test_finds_python_class(self, tmp_path):
        """Finds Python class definitions."""
        (tmp_path / "models.py").write_text("class UserModel:\n    pass\n")

        result = await find_definition("UserModel", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 1
        assert data["definitions"][0]["type"] == "class"

    @pytest.mark.asyncio
    async def test_finds_python_variable(self, tmp_path):
        """Finds Python variable/constant definitions."""
        (tmp_path / "config.py").write_text("DATABASE_URL = 'postgres://localhost/db'\n")

        result = await find_definition("DATABASE_URL", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 1
        assert data["definitions"][0]["type"] == "variable"

    @pytest.mark.asyncio
    async def test_finds_javascript_function(self, tmp_path):
        """Finds JavaScript function definitions."""
        (tmp_path / "utils.js").write_text("function processData(input) {\n    return input.map(x => x * 2);\n}\n")

        result = await find_definition("processData", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 1
        assert data["definitions"][0]["type"] == "function"

    @pytest.mark.asyncio
    async def test_finds_javascript_const(self, tmp_path):
        """Finds JavaScript const definitions."""
        (tmp_path / "config.js").write_text("const API_ENDPOINT = 'https://api.example.com';\n")

        result = await find_definition("API_ENDPOINT", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 1
        assert data["definitions"][0]["type"] == "const"

    @pytest.mark.asyncio
    async def test_finds_typescript_interface(self, tmp_path):
        """Finds TypeScript interface definitions."""
        (tmp_path / "types.ts").write_text("interface UserProfile {\n    id: number;\n    name: string;\n}\n")

        result = await find_definition("UserProfile", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 1
        assert data["definitions"][0]["type"] == "interface"

    @pytest.mark.asyncio
    async def test_finds_go_function(self, tmp_path):
        """Finds Go function definitions."""
        (tmp_path / "main.go").write_text("func HandleRequest(w http.ResponseWriter, r *http.Request) {\n}\n")

        result = await find_definition("HandleRequest", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 1
        # Go functions are detected as "function" type
        assert data["definitions"][0]["type"] in ("func", "function")

    @pytest.mark.asyncio
    async def test_finds_rust_function(self, tmp_path):
        """Finds Rust function definitions."""
        (tmp_path / "lib.rs").write_text("fn process_data(input: Vec<i32>) -> Vec<i32> {\n    input\n}\n")

        result = await find_definition("process_data", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 1
        # Rust functions are detected as "function" type
        assert data["definitions"][0]["type"] in ("fn", "function")

    @pytest.mark.asyncio
    async def test_returns_empty_for_unknown_symbol(self, tmp_path):
        """Returns empty when symbol not found."""
        (tmp_path / "code.py").write_text("def other_function(): pass\n")

        result = await find_definition("nonexistent_symbol", str(tmp_path))
        data = json.loads(result)

        # Either count is 0 or definitions list is empty
        assert data.get("count", 0) == 0 or len(data.get("definitions", [])) == 0

    @pytest.mark.asyncio
    async def test_searches_recursively(self, tmp_path):
        """Finds definitions in subdirectories."""
        subdir = tmp_path / "src" / "utils"
        subdir.mkdir(parents=True)
        (subdir / "helpers.py").write_text("def deep_function():\n    pass\n")

        result = await find_definition("deep_function", str(tmp_path))
        data = json.loads(result)

        assert data["count"] == 1


# =============================================================================
# Error Handling - Tools handle errors gracefully
# =============================================================================


class TestErrorHandling:
    """Search tools handle errors gracefully."""

    @pytest.mark.asyncio
    async def test_find_files_raises_for_nonexistent_path(self):
        """find_files raises FileNotFoundError for nonexistent path."""
        with pytest.raises(FileNotFoundError):
            await find_files("*.py", "/nonexistent/path/xyz")

    @pytest.mark.asyncio
    async def test_find_definition_raises_for_nonexistent_path(self):
        """find_definition raises FileNotFoundError for nonexistent path."""
        with pytest.raises(FileNotFoundError):
            await find_definition("symbol", "/nonexistent/path/xyz")
