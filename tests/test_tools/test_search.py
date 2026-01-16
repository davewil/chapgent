"""Tests for search tools (grep_search, find_files)."""

import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from pygent.tools.search import (
    _get_depth,
    _grep_with_python,
    _grep_with_ripgrep,
    _is_ripgrep_available,
    _should_include_path,
    find_files,
    grep_search,
)

# Unit tests for grep_search


@pytest.mark.asyncio
async def test_grep_search_basic_match(tmp_path):
    """Test basic pattern matching."""
    # Create test files
    (tmp_path / "test.py").write_text("def hello():\n    print('hello')\n", encoding="utf-8")
    (tmp_path / "other.py").write_text("def world():\n    pass\n", encoding="utf-8")

    result = await grep_search("hello", str(tmp_path))
    data = json.loads(result)

    assert data["count"] >= 1
    # Should find "hello" in test.py
    files = [r["file"] for r in data["results"]]
    assert any("test.py" in f for f in files)


@pytest.mark.asyncio
async def test_grep_search_no_matches(tmp_path):
    """Test search with no matches."""
    (tmp_path / "test.txt").write_text("nothing special here", encoding="utf-8")

    result = await grep_search("xyz123", str(tmp_path))
    data = json.loads(result)

    assert data.get("message") == "No matches found"
    assert data["results"] == []


@pytest.mark.asyncio
async def test_grep_search_file_pattern(tmp_path):
    """Test filtering by file pattern."""
    (tmp_path / "code.py").write_text("def func(): pass", encoding="utf-8")
    (tmp_path / "code.txt").write_text("def func(): pass", encoding="utf-8")

    result = await grep_search("def", str(tmp_path), file_pattern="*.py")
    data = json.loads(result)

    # Should only find match in .py file
    for r in data["results"]:
        assert r["file"].endswith(".py")


@pytest.mark.asyncio
async def test_grep_search_ignore_case(tmp_path):
    """Test case-insensitive search."""
    (tmp_path / "test.txt").write_text("Hello World\nhello world", encoding="utf-8")

    result = await grep_search("HELLO", str(tmp_path), ignore_case=True)
    data = json.loads(result)

    # Should find both lines
    assert data["count"] == 2


@pytest.mark.asyncio
async def test_grep_search_case_sensitive(tmp_path):
    """Test case-sensitive search (default)."""
    (tmp_path / "test.txt").write_text("Hello World\nhello world", encoding="utf-8")

    result = await grep_search("Hello", str(tmp_path), ignore_case=False)
    data = json.loads(result)

    # Should find only one line
    assert data["count"] == 1


@pytest.mark.asyncio
async def test_grep_search_max_results(tmp_path):
    """Test max_results limit."""
    content = "\n".join([f"match line {i}" for i in range(20)])
    (tmp_path / "test.txt").write_text(content, encoding="utf-8")

    result = await grep_search("match", str(tmp_path), max_results=5)
    data = json.loads(result)

    assert data["count"] == 5


@pytest.mark.asyncio
async def test_grep_search_single_file(tmp_path):
    """Test searching a single file directly."""
    test_file = tmp_path / "single.py"
    test_file.write_text("line one\nline two\nline three", encoding="utf-8")

    result = await grep_search("two", str(test_file))
    data = json.loads(result)

    assert data["count"] == 1
    assert data["results"][0]["line"] == 2


@pytest.mark.asyncio
async def test_grep_search_regex_pattern(tmp_path):
    """Test regex pattern matching."""
    (tmp_path / "test.py").write_text("def foo_bar():\ndef baz_qux():\n", encoding="utf-8")

    result = await grep_search(r"def \w+_\w+", str(tmp_path))
    data = json.loads(result)

    assert data["count"] == 2


@pytest.mark.asyncio
async def test_grep_search_skips_hidden_dirs(tmp_path):
    """Test that hidden directories are skipped."""
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "secret.txt").write_text("findme", encoding="utf-8")
    (tmp_path / "visible.txt").write_text("findme", encoding="utf-8")

    # Use Python backend to test our filtering
    with patch("pygent.tools.search._is_ripgrep_available", return_value=False):
        result = await grep_search("findme", str(tmp_path))
        data = json.loads(result)

    # Should only find in visible.txt
    assert data["count"] == 1
    assert ".hidden" not in data["results"][0]["file"]


@pytest.mark.asyncio
async def test_grep_search_skips_node_modules(tmp_path):
    """Test that node_modules is skipped."""
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "lib.js").write_text("findme", encoding="utf-8")
    (tmp_path / "app.js").write_text("findme", encoding="utf-8")

    with patch("pygent.tools.search._is_ripgrep_available", return_value=False):
        result = await grep_search("findme", str(tmp_path))
        data = json.loads(result)

    # Should only find in app.js
    assert data["count"] == 1
    assert "node_modules" not in data["results"][0]["file"]


# Tests for Python backend


@pytest.mark.asyncio
async def test_grep_python_path_not_found():
    """Test Python backend with non-existent path."""
    with pytest.raises(FileNotFoundError, match="Path not found"):
        await _grep_with_python("pattern", "/nonexistent/path", None, False, 0, 100)


@pytest.mark.asyncio
async def test_grep_python_invalid_regex():
    """Test Python backend with invalid regex."""
    with pytest.raises(ValueError, match="Invalid regex pattern"):
        await _grep_with_python("[invalid", ".", None, False, 0, 100)


@pytest.mark.asyncio
async def test_grep_python_unreadable_file(tmp_path):
    """Test that unreadable files are skipped gracefully."""
    # Create a file that can't be decoded as UTF-8
    binary_file = tmp_path / "binary.dat"
    binary_file.write_bytes(b"\xff\xfe\x00\x00")

    # Create a readable file
    (tmp_path / "text.txt").write_text("findme", encoding="utf-8")

    # Should not crash
    results = await _grep_with_python("findme", str(tmp_path), None, False, 0, 100)
    assert len(results) == 1


# Tests for ripgrep backend


@pytest.mark.asyncio
async def test_grep_ripgrep_not_found():
    """Test ripgrep backend when rg is not found."""
    with patch("asyncio.create_subprocess_exec", side_effect=FileNotFoundError):
        results = await _grep_with_ripgrep("pattern", ".", None, False, 0, 100)
        assert results == []


@pytest.mark.asyncio
async def test_grep_ripgrep_json_parsing():
    """Test ripgrep JSON output parsing."""
    # Simulate ripgrep JSON output
    rg_output = (
        b'{"type":"match","data":{"path":{"text":"test.py"},"line_number":5,'
        b'"lines":{"text":"def foo():\\n"},"submatches":[{"match":{"text":"foo"}}]}}\n'
    )

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(rg_output, b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        results = await _grep_with_ripgrep("foo", ".", None, False, 0, 100)

    assert len(results) == 1
    assert results[0]["file"] == "test.py"
    assert results[0]["line"] == 5
    assert results[0]["match"] == "foo"


@pytest.mark.asyncio
async def test_grep_ripgrep_invalid_json():
    """Test ripgrep backend handles invalid JSON lines."""
    rg_output = (
        b'not json\n{"type":"match","data":{"path":{"text":"test.py"},'
        b'"line_number":1,"lines":{"text":"x"},"submatches":[{"match":{"text":"x"}}]}}\n'
    )

    mock_proc = MagicMock()
    mock_proc.communicate = AsyncMock(return_value=(rg_output, b""))

    with patch("asyncio.create_subprocess_exec", return_value=mock_proc):
        results = await _grep_with_ripgrep("x", ".", None, False, 0, 100)

    # Should skip invalid line and parse valid one
    assert len(results) == 1


def test_is_ripgrep_available():
    """Test ripgrep availability check."""
    with patch("shutil.which", return_value="/usr/bin/rg"):
        assert _is_ripgrep_available() is True

    with patch("shutil.which", return_value=None):
        assert _is_ripgrep_available() is False


@pytest.mark.asyncio
async def test_grep_search_uses_ripgrep_when_available(tmp_path):
    """Test that grep_search uses ripgrep when available."""
    (tmp_path / "test.txt").write_text("hello", encoding="utf-8")

    with patch("pygent.tools.search._is_ripgrep_available", return_value=True):
        with patch("pygent.tools.search._grep_with_ripgrep", return_value=[]) as mock_rg:
            await grep_search("hello", str(tmp_path))
            mock_rg.assert_called_once()


@pytest.mark.asyncio
async def test_grep_search_uses_python_when_ripgrep_unavailable(tmp_path):
    """Test that grep_search falls back to Python when ripgrep unavailable."""
    (tmp_path / "test.txt").write_text("hello", encoding="utf-8")

    with patch("pygent.tools.search._is_ripgrep_available", return_value=False):
        with patch("pygent.tools.search._grep_with_python", return_value=[]) as mock_py:
            await grep_search("hello", str(tmp_path))
            mock_py.assert_called_once()


# Property-based tests


@settings(max_examples=50, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    content=st.text(min_size=10, max_size=200).filter(lambda s: "\r" not in s and "\x00" not in s),
    search_word=st.text(min_size=3, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"),
)
@pytest.mark.asyncio
async def test_prop_grep_finds_inserted_pattern(tmp_path, content, search_word):
    """Property: if we insert a word into content, grep should find it."""
    # Insert search_word into the content
    full_content = f"{content}\n{search_word}\n"
    test_file = tmp_path / "prop_test.txt"
    test_file.write_text(full_content, encoding="utf-8")

    # Force Python backend for deterministic behavior
    with patch("pygent.tools.search._is_ripgrep_available", return_value=False):
        result = await grep_search(search_word, str(test_file))
        data = json.loads(result)

    # Should find at least one match
    assert data["count"] >= 1


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    lines=st.lists(st.text(min_size=5, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz "), min_size=1, max_size=10),
)
@pytest.mark.asyncio
async def test_prop_grep_respects_max_results(tmp_path, lines):
    """Property: grep should never return more than max_results."""
    # Write lines that all contain "a"
    content_lines = [line + " a" for line in lines]
    test_file = tmp_path / "prop_max.txt"
    test_file.write_text("\n".join(content_lines), encoding="utf-8")

    max_results = 3
    with patch("pygent.tools.search._is_ripgrep_available", return_value=False):
        result = await grep_search("a", str(test_file), max_results=max_results)
        data = json.loads(result)

    assert data["count"] <= max_results


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    word=st.text(min_size=4, max_size=15, alphabet="abcdefghijklmnopqrstuvwxyz"),
)
@pytest.mark.asyncio
async def test_prop_grep_case_insensitive(tmp_path, word):
    """Property: case-insensitive search should find both cases."""
    lower = word.lower()
    upper = word.upper()
    test_file = tmp_path / "prop_case.txt"
    test_file.write_text(f"{lower}\n{upper}\n", encoding="utf-8")

    with patch("pygent.tools.search._is_ripgrep_available", return_value=False):
        result = await grep_search(lower, str(test_file), ignore_case=True)
        data = json.loads(result)

    # Should find both if they're different
    if lower != upper:
        assert data["count"] == 2
    else:
        assert data["count"] >= 1


# =============================================================================
# Unit tests for find_files
# =============================================================================


@pytest.mark.asyncio
async def test_find_files_basic(tmp_path):
    """Test basic file finding with glob pattern."""
    (tmp_path / "file1.py").touch()
    (tmp_path / "file2.py").touch()
    (tmp_path / "file3.txt").touch()

    result = await find_files("*.py", str(tmp_path))
    data = json.loads(result)

    assert data["count"] == 2
    assert "file1.py" in data["files"]
    assert "file2.py" in data["files"]
    assert "file3.txt" not in data["files"]


@pytest.mark.asyncio
async def test_find_files_recursive(tmp_path):
    """Test recursive file finding with **."""
    (tmp_path / "root.py").touch()
    subdir = tmp_path / "subdir"
    subdir.mkdir()
    (subdir / "nested.py").touch()

    result = await find_files("**/*.py", str(tmp_path))
    data = json.loads(result)

    assert data["count"] == 2
    files = data["files"]
    assert any("root.py" in f for f in files)
    assert any("nested.py" in f for f in files)


@pytest.mark.asyncio
async def test_find_files_no_matches(tmp_path):
    """Test find_files when no files match."""
    (tmp_path / "file.txt").touch()

    result = await find_files("*.py", str(tmp_path))
    data = json.loads(result)

    assert data.get("message") == "No files found"
    assert data["files"] == []


@pytest.mark.asyncio
async def test_find_files_path_not_found():
    """Test find_files with non-existent path."""
    with pytest.raises(FileNotFoundError, match="Path not found"):
        await find_files("*.py", "/nonexistent/path")


@pytest.mark.asyncio
async def test_find_files_path_not_directory(tmp_path):
    """Test find_files with a file path instead of directory."""
    test_file = tmp_path / "file.txt"
    test_file.touch()

    with pytest.raises(NotADirectoryError, match="Path is not a directory"):
        await find_files("*.py", str(test_file))


@pytest.mark.asyncio
async def test_find_files_file_type_filter_files(tmp_path):
    """Test filtering to only files."""
    (tmp_path / "file.py").touch()
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    result = await find_files("*", str(tmp_path), file_type="file")
    data = json.loads(result)

    assert "file.py" in data["files"]
    assert "subdir" not in data["files"]


@pytest.mark.asyncio
async def test_find_files_file_type_filter_directories(tmp_path):
    """Test filtering to only directories."""
    (tmp_path / "file.py").touch()
    subdir = tmp_path / "subdir"
    subdir.mkdir()

    result = await find_files("*", str(tmp_path), file_type="directory")
    data = json.loads(result)

    assert data["count"] == 1
    assert "subdir" in data["files"]


@pytest.mark.asyncio
async def test_find_files_max_depth(tmp_path):
    """Test max_depth filtering."""
    (tmp_path / "root.py").touch()
    level1 = tmp_path / "level1"
    level1.mkdir()
    (level1 / "nested1.py").touch()
    level2 = level1 / "level2"
    level2.mkdir()
    (level2 / "deep.py").touch()

    # max_depth=1 should find root.py and level1/nested1.py
    result = await find_files("**/*.py", str(tmp_path), max_depth=2)
    data = json.loads(result)

    files = data["files"]
    assert any("root.py" in f for f in files)
    assert any("nested1.py" in f for f in files)
    # deep.py is at depth 3 (level1/level2/deep.py)
    assert not any("deep.py" in f for f in files)


@pytest.mark.asyncio
async def test_find_files_skips_hidden_dirs(tmp_path):
    """Test that hidden directories are skipped."""
    (tmp_path / "visible.py").touch()
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "secret.py").touch()

    result = await find_files("**/*.py", str(tmp_path))
    data = json.loads(result)

    assert data["count"] == 1
    assert "visible.py" in data["files"]


@pytest.mark.asyncio
async def test_find_files_skips_node_modules(tmp_path):
    """Test that node_modules is skipped."""
    (tmp_path / "app.js").touch()
    nm = tmp_path / "node_modules"
    nm.mkdir()
    (nm / "lib.js").touch()

    result = await find_files("**/*.js", str(tmp_path))
    data = json.loads(result)

    assert data["count"] == 1
    assert "app.js" in data["files"]


@pytest.mark.asyncio
async def test_find_files_skips_pycache(tmp_path):
    """Test that __pycache__ is skipped."""
    (tmp_path / "main.py").touch()
    cache = tmp_path / "__pycache__"
    cache.mkdir()
    (cache / "main.cpython-310.pyc").touch()

    result = await find_files("**/*", str(tmp_path), file_type="file")
    data = json.loads(result)

    assert data["count"] == 1
    assert "main.py" in data["files"]


@pytest.mark.asyncio
async def test_find_files_sorted_output(tmp_path):
    """Test that output is sorted alphabetically."""
    (tmp_path / "z_file.py").touch()
    (tmp_path / "a_file.py").touch()
    (tmp_path / "m_file.py").touch()

    result = await find_files("*.py", str(tmp_path))
    data = json.loads(result)

    assert data["files"] == ["a_file.py", "m_file.py", "z_file.py"]


# =============================================================================
# Tests for helper functions
# =============================================================================


def test_should_include_path_normal(tmp_path):
    """Test _should_include_path with normal path."""

    file_path = tmp_path / "subdir" / "file.py"
    assert _should_include_path(file_path, tmp_path) is True


def test_should_include_path_hidden(tmp_path):
    """Test _should_include_path with hidden directory."""

    file_path = tmp_path / ".hidden" / "file.py"
    assert _should_include_path(file_path, tmp_path) is False


def test_should_include_path_node_modules(tmp_path):
    """Test _should_include_path with node_modules."""

    file_path = tmp_path / "node_modules" / "lib" / "index.js"
    assert _should_include_path(file_path, tmp_path) is False


def test_get_depth(tmp_path):
    """Test _get_depth calculation."""

    # Depth 1: file in root
    assert _get_depth(tmp_path / "file.py", tmp_path) == 1

    # Depth 2: file in subdir
    assert _get_depth(tmp_path / "subdir" / "file.py", tmp_path) == 2

    # Depth 3: file in nested subdirs
    assert _get_depth(tmp_path / "a" / "b" / "file.py", tmp_path) == 3


def test_get_depth_unrelated_path():
    """Test _get_depth with unrelated path (ValueError case)."""
    from pathlib import Path

    # When paths are unrelated, should return 0
    assert _get_depth(Path("/some/other/path"), Path("/completely/different")) == 0


# =============================================================================
# Property-based tests for find_files
# =============================================================================


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    filenames=st.lists(
        st.text(min_size=3, max_size=10, alphabet="abcdefghijklmnopqrstuvwxyz"),
        min_size=1,
        max_size=10,
        unique=True,
    ),
)
@pytest.mark.asyncio
async def test_prop_find_files_finds_created_files(tmp_path, filenames):
    """Property: find_files should find all created .py files."""
    import shutil
    import uuid

    # Use unique subdirectory for each hypothesis example
    test_dir = tmp_path / f"test_{uuid.uuid4().hex}"
    test_dir.mkdir(exist_ok=True)

    try:
        # Create files
        for name in filenames:
            (test_dir / f"{name}.py").touch()

        result = await find_files("*.py", str(test_dir))
        data = json.loads(result)

        assert data["count"] == len(filenames)
        for name in filenames:
            assert f"{name}.py" in data["files"]
    finally:
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)


@settings(max_examples=30, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    py_count=st.integers(min_value=0, max_value=5),
    txt_count=st.integers(min_value=0, max_value=5),
)
@pytest.mark.asyncio
async def test_prop_find_files_filters_by_extension(tmp_path, py_count, txt_count):
    """Property: find_files should only return files matching pattern."""
    import shutil
    import uuid

    # Use unique subdirectory for each hypothesis example
    test_dir = tmp_path / f"test_{uuid.uuid4().hex}"
    test_dir.mkdir(exist_ok=True)

    try:
        # Create .py files
        for i in range(py_count):
            (test_dir / f"file{i}.py").touch()

        # Create .txt files
        for i in range(txt_count):
            (test_dir / f"file{i}.txt").touch()

        result = await find_files("*.py", str(test_dir))
        data = json.loads(result)

        if py_count == 0:
            assert data.get("message") == "No files found"
        else:
            assert data["count"] == py_count
            for f in data["files"]:
                assert f.endswith(".py")
    finally:
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)


@settings(max_examples=20, deadline=None, suppress_health_check=[HealthCheck.function_scoped_fixture])
@given(
    depth=st.integers(min_value=1, max_value=4),
)
@pytest.mark.asyncio
async def test_prop_find_files_respects_max_depth(tmp_path, depth):
    """Property: find_files should respect max_depth setting."""
    import shutil
    import uuid

    # Use unique subdirectory for each hypothesis example
    test_dir = tmp_path / f"test_{uuid.uuid4().hex}"
    test_dir.mkdir(exist_ok=True)

    try:
        # Create nested structure
        current = test_dir
        for i in range(5):
            current = current / f"level{i}"
            current.mkdir(exist_ok=True)
            (current / f"file_at_{i + 1}.py").touch()

        result = await find_files("**/*.py", str(test_dir), max_depth=depth)
        data = json.loads(result)

        # All returned files should be within max_depth
        for f in data.get("files", []):
            file_depth = f.count("/") + 1 if "/" in f else 1
            # Allow for platform differences in path separators
            file_depth = max(f.count("/"), f.count("\\")) + 1
            assert file_depth <= depth
    finally:
        # Clean up
        shutil.rmtree(test_dir, ignore_errors=True)
