"""Tests for context models."""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from pygent.context.models import (
    GitInfo,
    ProjectContext,
    ProjectType,
    TestFramework,
)

# TestFramework enum tests


def test_test_framework_values():
    """Test TestFramework enum has expected values."""
    assert TestFramework.PYTEST.value == "pytest"
    assert TestFramework.UNITTEST.value == "unittest"
    assert TestFramework.JEST.value == "jest"
    assert TestFramework.MOCHA.value == "mocha"
    assert TestFramework.VITEST.value == "vitest"
    assert TestFramework.GO_TEST.value == "go test"
    assert TestFramework.CARGO_TEST.value == "cargo test"
    assert TestFramework.UNKNOWN.value == "unknown"


def test_test_framework_from_string():
    """Test creating TestFramework from string value."""
    assert TestFramework("pytest") == TestFramework.PYTEST
    assert TestFramework("jest") == TestFramework.JEST
    assert TestFramework("unknown") == TestFramework.UNKNOWN


def test_test_framework_invalid():
    """Test invalid TestFramework value raises error."""
    with pytest.raises(ValueError):
        TestFramework("invalid_framework")


# ProjectType enum tests


def test_project_type_values():
    """Test ProjectType enum has expected values."""
    assert ProjectType.PYTHON.value == "python"
    assert ProjectType.NODE.value == "node"
    assert ProjectType.GO.value == "go"
    assert ProjectType.RUST.value == "rust"
    assert ProjectType.UNKNOWN.value == "unknown"


def test_project_type_from_string():
    """Test creating ProjectType from string value."""
    assert ProjectType("python") == ProjectType.PYTHON
    assert ProjectType("node") == ProjectType.NODE
    assert ProjectType("unknown") == ProjectType.UNKNOWN


def test_project_type_invalid():
    """Test invalid ProjectType value raises error."""
    with pytest.raises(ValueError):
        ProjectType("invalid_type")


# GitInfo model tests


def test_git_info_defaults():
    """Test GitInfo default values."""
    info = GitInfo()
    assert info.branch is None
    assert info.remote is None
    assert info.has_changes is False
    assert info.commit_count == 0
    assert info.last_commit is None


def test_git_info_with_values():
    """Test GitInfo with explicit values."""
    info = GitInfo(
        branch="main",
        remote="https://github.com/user/repo.git",
        has_changes=True,
        commit_count=42,
        last_commit="abc123",
    )
    assert info.branch == "main"
    assert info.remote == "https://github.com/user/repo.git"
    assert info.has_changes is True
    assert info.commit_count == 42
    assert info.last_commit == "abc123"


def test_git_info_serialization():
    """Test GitInfo JSON serialization."""
    info = GitInfo(branch="main", has_changes=True)
    data = info.model_dump()
    assert data["branch"] == "main"
    assert data["has_changes"] is True

    # Can reconstruct from dict
    info2 = GitInfo.model_validate(data)
    assert info2.branch == "main"


# ProjectContext model tests


def test_project_context_defaults():
    """Test ProjectContext default values."""
    ctx = ProjectContext()
    assert ctx.type == ProjectType.UNKNOWN
    assert ctx.root == "."
    assert ctx.name is None
    assert ctx.version is None
    assert ctx.dependencies == []
    assert ctx.scripts == {}
    assert ctx.test_framework == TestFramework.UNKNOWN
    assert ctx.git_info is None
    assert ctx.config_files == []


def test_project_context_with_values():
    """Test ProjectContext with explicit values."""
    ctx = ProjectContext(
        type=ProjectType.PYTHON,
        root="/home/user/project",
        name="myproject",
        version="1.0.0",
        dependencies=["requests", "pytest"],
        scripts={"test": "pytest", "lint": "ruff check"},
        test_framework=TestFramework.PYTEST,
        git_info=GitInfo(branch="main"),
        config_files=["pyproject.toml", "setup.cfg"],
    )
    assert ctx.type == ProjectType.PYTHON
    assert ctx.root == "/home/user/project"
    assert ctx.name == "myproject"
    assert ctx.version == "1.0.0"
    assert ctx.dependencies == ["requests", "pytest"]
    assert ctx.scripts == {"test": "pytest", "lint": "ruff check"}
    assert ctx.test_framework == TestFramework.PYTEST
    assert ctx.git_info is not None
    assert ctx.git_info.branch == "main"
    assert ctx.config_files == ["pyproject.toml", "setup.cfg"]


def test_project_context_root_path_property():
    """Test ProjectContext.root_path property returns Path object."""
    import sys

    # Use platform-appropriate absolute path
    if sys.platform == "win32":
        test_path = "C:\\Users\\user\\project"
    else:
        test_path = "/home/user/project"

    ctx = ProjectContext(root=test_path)
    path = ctx.root_path
    # Path separators differ between platforms, so just check the parts
    assert path.parts[-1] == "project"
    assert "user" in path.parts or "Users" in path.parts
    assert path.is_absolute()


def test_project_context_serialization():
    """Test ProjectContext JSON serialization."""
    ctx = ProjectContext(
        type=ProjectType.NODE,
        root="/app",
        name="webapp",
        dependencies=["express"],
        git_info=GitInfo(branch="develop"),
    )
    data = ctx.model_dump()
    assert data["type"] == "node"
    assert data["root"] == "/app"
    assert data["name"] == "webapp"
    assert data["git_info"]["branch"] == "develop"

    # Can reconstruct from dict
    ctx2 = ProjectContext.model_validate(data)
    assert ctx2.type == ProjectType.NODE
    assert ctx2.git_info is not None
    assert ctx2.git_info.branch == "develop"


def test_project_context_json_round_trip():
    """Test ProjectContext survives JSON round trip."""
    ctx = ProjectContext(
        type=ProjectType.RUST,
        root="/projects/myrust",
        name="myrust",
        version="0.1.0",
        test_framework=TestFramework.CARGO_TEST,
    )
    json_str = ctx.model_dump_json()
    ctx2 = ProjectContext.model_validate_json(json_str)

    assert ctx2.type == ctx.type
    assert ctx2.root == ctx.root
    assert ctx2.name == ctx.name
    assert ctx2.version == ctx.version
    assert ctx2.test_framework == ctx.test_framework


# Property-based tests


@given(
    name=st.text(min_size=1, max_size=50).filter(lambda x: x.strip()),
    version=st.from_regex(r"[0-9]+\.[0-9]+\.[0-9]+", fullmatch=True),
)
@settings(max_examples=20)
def test_project_context_properties(name: str, version: str):
    """Property test for ProjectContext serialization."""
    ctx = ProjectContext(
        type=ProjectType.PYTHON,
        name=name.strip(),
        version=version,
    )
    data = ctx.model_dump()
    ctx2 = ProjectContext.model_validate(data)
    assert ctx2.name == ctx.name
    assert ctx2.version == ctx.version


@given(
    branch=st.text(min_size=1, max_size=30).filter(lambda x: x.strip()),
    commit_count=st.integers(min_value=0, max_value=100000),
)
@settings(max_examples=20)
def test_git_info_properties(branch: str, commit_count: int):
    """Property test for GitInfo serialization."""
    info = GitInfo(branch=branch.strip(), commit_count=commit_count)
    data = info.model_dump()
    info2 = GitInfo.model_validate(data)
    assert info2.branch == info.branch
    assert info2.commit_count == info.commit_count
