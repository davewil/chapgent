"""Search tools for finding files and code patterns.

This module provides tools for searching file contents using regex patterns
and finding files matching glob patterns.
"""

from __future__ import annotations

import asyncio
import json
import re
import shutil
from pathlib import Path

from pygent.tools.base import ToolRisk, tool


def _is_ripgrep_available() -> bool:
    """Check if ripgrep (rg) is available on the system."""
    return shutil.which("rg") is not None


async def _grep_with_ripgrep(
    pattern: str,
    path: str,
    file_pattern: str | None,
    ignore_case: bool,
    context_lines: int,
    max_results: int,
) -> list[dict[str, str | int]]:
    """Execute grep search using ripgrep."""
    cmd = ["rg", "--json", "--max-count", str(max_results)]

    if ignore_case:
        cmd.append("--ignore-case")

    if context_lines > 0:
        cmd.extend(["--context", str(context_lines)])

    if file_pattern:
        cmd.extend(["--glob", file_pattern])

    cmd.extend([pattern, path])

    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, _ = await proc.communicate()
    except FileNotFoundError:
        # ripgrep not found
        return []

    results: list[dict[str, str | int]] = []
    for line in stdout.decode("utf-8", errors="replace").splitlines():
        if not line.strip():
            continue
        try:
            data = json.loads(line)
            if data.get("type") == "match":
                match_data = data.get("data", {})
                submatches = match_data.get("submatches", [])
                match_text = submatches[0].get("match", {}).get("text", "") if submatches else ""
                results.append(
                    {
                        "file": match_data.get("path", {}).get("text", ""),
                        "line": match_data.get("line_number", 0),
                        "content": match_data.get("lines", {}).get("text", "").rstrip("\n"),
                        "match": match_text,
                    }
                )
                if len(results) >= max_results:
                    break
        except json.JSONDecodeError:
            continue

    return results


async def _grep_with_python(
    pattern: str,
    path: str,
    file_pattern: str | None,
    ignore_case: bool,
    context_lines: int,
    max_results: int,
) -> list[dict[str, str | int]]:
    """Execute grep search using pure Python."""
    search_path = Path(path)
    if not search_path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    flags = re.IGNORECASE if ignore_case else 0
    try:
        regex = re.compile(pattern, flags)
    except re.error as e:
        raise ValueError(f"Invalid regex pattern: {e}") from e

    results: list[dict[str, str | int]] = []

    # Collect files to search
    if search_path.is_file():
        files = [search_path]
    else:
        if file_pattern:
            files = list(search_path.rglob(file_pattern))
        else:
            files = [f for f in search_path.rglob("*") if f.is_file()]

    # Filter out hidden and common ignore patterns
    def should_include(f: Path) -> bool:
        parts = f.parts
        return not any(
            part.startswith(".") or part in ("node_modules", "__pycache__", ".git", "venv", ".venv") for part in parts
        )

    files = [f for f in files if should_include(f)]

    for file_path in files:
        if len(results) >= max_results:
            break

        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
            lines = content.splitlines()

            for line_num, line in enumerate(lines, start=1):
                if len(results) >= max_results:
                    break

                match = regex.search(line)
                if match:
                    results.append(
                        {
                            "file": str(file_path),
                            "line": line_num,
                            "content": line,
                            "match": match.group(0),
                        }
                    )

        except (OSError, UnicodeDecodeError):
            # Skip files that can't be read
            continue

    return results


@tool(
    name="grep_search",
    description="Search for patterns in files using regex. Returns matching lines with file path and line number.",
    risk=ToolRisk.LOW,
)
async def grep_search(
    pattern: str,
    path: str = ".",
    file_pattern: str | None = None,
    ignore_case: bool = False,
    context_lines: int = 0,
    max_results: int = 100,
) -> str:
    """Search file contents with regex.

    Args:
        pattern: Regex pattern to search for.
        path: Directory to search in (default: current directory).
        file_pattern: Glob pattern to filter files (e.g., "*.py").
        ignore_case: Case-insensitive search.
        context_lines: Lines of context around matches.
        max_results: Maximum number of matches to return.

    Returns:
        JSON array of matches with file, line, content, and match fields.
    """
    if _is_ripgrep_available():
        results = await _grep_with_ripgrep(pattern, path, file_pattern, ignore_case, context_lines, max_results)
    else:
        results = await _grep_with_python(pattern, path, file_pattern, ignore_case, context_lines, max_results)

    if not results:
        return json.dumps({"message": "No matches found", "results": []})

    return json.dumps({"count": len(results), "results": results}, indent=2)


def _should_include_path(path: Path, base_path: Path) -> bool:
    """Check if a path should be included (not hidden or in common ignore dirs).

    Args:
        path: The path to check.
        base_path: The base directory (to get relative parts).

    Returns:
        True if the path should be included.
    """
    try:
        rel_path = path.relative_to(base_path)
        parts = rel_path.parts
    except ValueError:
        parts = path.parts

    return not any(
        part.startswith(".") or part in ("node_modules", "__pycache__", ".git", "venv", ".venv") for part in parts
    )


def _get_depth(path: Path, base_path: Path) -> int:
    """Calculate the depth of a path relative to base.

    Args:
        path: The path to measure.
        base_path: The base directory.

    Returns:
        Number of directory levels from base to path.
    """
    try:
        rel_path = path.relative_to(base_path)
        return len(rel_path.parts)
    except ValueError:
        return 0


@tool(
    name="find_files",
    description="Find files and directories matching a glob pattern. Returns a list of matching paths.",
    risk=ToolRisk.LOW,
)
async def find_files(
    pattern: str,
    path: str = ".",
    max_depth: int | None = None,
    file_type: str | None = None,
) -> str:
    """Find files by name pattern.

    Args:
        pattern: Glob pattern (e.g., "**/*.py", "test_*.py").
        path: Base directory to search (default: current directory).
        max_depth: Maximum directory depth to search.
        file_type: Filter by type ("file" or "directory").

    Returns:
        JSON array of matching paths relative to the search path.
    """
    search_path = Path(path)
    if not search_path.exists():
        raise FileNotFoundError(f"Path not found: {path}")

    if not search_path.is_dir():
        raise NotADirectoryError(f"Path is not a directory: {path}")

    matches: list[str] = []

    for item in search_path.glob(pattern):
        # Skip hidden files and common ignore directories
        if not _should_include_path(item, search_path):
            continue

        # Check max_depth
        if max_depth is not None:
            depth = _get_depth(item, search_path)
            if depth > max_depth:
                continue

        # Check file_type filter
        if file_type == "file" and not item.is_file():
            continue
        if file_type == "directory" and not item.is_dir():
            continue

        # Store relative path for cleaner output
        try:
            rel_path = item.relative_to(search_path)
            matches.append(str(rel_path))
        except ValueError:
            matches.append(str(item))

    # Sort for consistent output
    matches.sort()

    if not matches:
        return json.dumps({"message": "No files found", "files": []})

    return json.dumps({"count": len(matches), "files": matches}, indent=2)
