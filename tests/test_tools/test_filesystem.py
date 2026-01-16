import json

import pytest
from pygent.tools.filesystem import edit_file, list_files, read_file


@pytest.mark.asyncio
async def test_read_file(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("Hello World", encoding="utf-8")

    content = await read_file(str(f))
    assert content == "Hello World"


@pytest.mark.asyncio
async def test_read_file_not_found():
    with pytest.raises(FileNotFoundError):
        await read_file("/non/existent/path/xyz.txt")


@pytest.mark.asyncio
async def test_list_files(tmp_path):
    (tmp_path / "a.txt").touch()
    (tmp_path / "b.txt").touch()
    (tmp_path / "sub").mkdir()
    (tmp_path / "sub" / "c.txt").touch()

    # Non-recursive
    result_json = await list_files(str(tmp_path))
    entries = json.loads(result_json)
    names = sorted([e["name"] for e in entries])
    assert names == ["a.txt", "b.txt", "sub"]

    # Recursive
    result_json_rec = await list_files(str(tmp_path), recursive=True)
    entries_rec = json.loads(result_json_rec)
    # paths = sorted([e["path"] for e in entries_rec])
    # path output format depends on implementation, usually relative to search root
    # Let's assume the implementation returns relative paths or we check presence
    assert any(e["name"] == "c.txt" for e in entries_rec)
    assert any(e["name"] == "a.txt" for e in entries_rec)


@pytest.mark.asyncio
async def test_edit_file(tmp_path):
    f = tmp_path / "code.py"
    f.write_text("print('hello')\nprint('world')", encoding="utf-8")

    await edit_file(str(f), "print('world')", "print('universe')")

    content = f.read_text(encoding="utf-8")
    assert content == "print('hello')\nprint('universe')"


@pytest.mark.asyncio
async def test_edit_file_not_found(tmp_path):
    f = tmp_path / "notes.txt"
    f.write_text("foo bar", encoding="utf-8")

    with pytest.raises(ValueError, match="String not found"):
        await edit_file(str(f), "baz", "qux")
