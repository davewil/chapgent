import pytest
from hypothesis import HealthCheck, given, settings
from hypothesis import strategies as st
from hypothesis.strategies import datetimes
from pygent.session.models import Message, Session, TextBlock, ToolInvocation, ToolResultBlock, ToolUseBlock
from pygent.session.storage import SessionStorage

# Strategies for generating Session objects
text_block_strategy = st.builds(TextBlock, text=st.text())
tool_use_block_strategy = st.builds(
    ToolUseBlock,
    id=st.text(),
    name=st.text(),
    input=st.dictionaries(keys=st.text(), values=st.text()),  # Simple dict for now
)
tool_result_block_strategy = st.builds(
    ToolResultBlock, tool_use_id=st.text(), content=st.text(), is_error=st.booleans()
)

content_block_strategy = st.one_of(text_block_strategy, tool_use_block_strategy, tool_result_block_strategy)

message_strategy = st.builds(
    Message,
    role=st.sampled_from(["user", "assistant", "system"]),
    content=st.one_of(st.text(), st.lists(content_block_strategy)),
    timestamp=datetimes(),
)

tool_invocation_strategy = st.builds(
    ToolInvocation,
    tool_name=st.text(),
    arguments=st.dictionaries(keys=st.text(), values=st.text()),
    result=st.text(),
    timestamp=datetimes(),
)

session_strategy = st.builds(
    Session,
    id=st.text(min_size=1),  # Ensure non-empty ID
    messages=st.lists(message_strategy),
    tool_history=st.lists(tool_invocation_strategy),
    working_directory=st.text(),
    metadata=st.dictionaries(keys=st.text(), values=st.text()),
)


@pytest.fixture
def storage(tmp_path):
    return SessionStorage(storage_dir=tmp_path)


@pytest.mark.asyncio
async def test_save_and_load_roundtrip(storage):
    # Manual roundtrip test
    session = Session(id="test-session", working_directory="/tmp")
    await storage.save(session)

    loaded = await storage.load("test-session")
    assert loaded == session


@pytest.mark.asyncio
@given(session=session_strategy)
@settings(suppress_health_check=[HealthCheck.function_scoped_fixture])
async def test_property_save_load(tmp_path, session):
    # Avoid reserved characters in filenames if session.id is used directly
    # For this test, we might want to sanitize or force a safe ID,
    # but let's assume the session ID generator handles safety or storage handles it.
    # For simplicity in property test, let's fix the ID to be safe
    session.id = "safe-id-" + str(hash(session.id))

    storage = SessionStorage(storage_dir=tmp_path)
    await storage.save(session)
    loaded = await storage.load(session.id)

    # Pydantic models should be equal
    assert loaded.model_dump() == session.model_dump()


@pytest.mark.asyncio
async def test_list_sessions(storage):
    s1 = Session(id="s1")
    s2 = Session(id="s2")

    await storage.save(s1)
    await storage.save(s2)

    sessions = await storage.list_sessions()
    assert len(sessions) == 2
    ids = {s.id for s in sessions}
    assert "s1" in ids
    assert "s2" in ids


@pytest.mark.asyncio
async def test_delete_session(storage):
    s1 = Session(id="s1")
    await storage.save(s1)

    assert await storage.load("s1") is not None

    await storage.delete("s1")

    assert await storage.load("s1") is None


@pytest.mark.asyncio
async def test_persistence_across_instances(tmp_path):
    storage1 = SessionStorage(storage_dir=tmp_path)
    s1 = Session(id="s1")
    await storage1.save(s1)

    storage2 = SessionStorage(storage_dir=tmp_path)
    loaded = await storage2.load("s1")
    assert loaded == s1
