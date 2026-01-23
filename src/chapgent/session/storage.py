import json
from pathlib import Path

import aiofiles
from pydantic import ValidationError

from chapgent.session.models import Session, SessionSummary


class SessionStorage:
    """JSON-based session persistence."""

    def __init__(self, storage_dir: Path | None = None) -> None:
        if storage_dir:
            self.storage_dir = storage_dir
        else:
            # Default to XDG compliant path: ~/.local/share/chapgent/sessions/
            self.storage_dir = Path.home() / ".local" / "share" / "chapgent" / "sessions"

        # Ensure storage directory exists
        self.storage_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, session_id: str) -> Path:
        return self.storage_dir / f"{session_id}.json"

    async def save(self, session: Session) -> None:
        """Save a session to disk."""
        path = self._get_session_path(session.id)

        # Use model_dump_json for serialization
        json_data = session.model_dump_json(indent=2)

        async with aiofiles.open(path, "w") as f:
            await f.write(json_data)

    async def load(self, session_id: str) -> Session | None:
        """Load a session from disk."""
        path = self._get_session_path(session_id)

        if not path.exists():
            return None

        async with aiofiles.open(path) as f:
            content = await f.read()

        return Session.model_validate_json(content)

    async def list_sessions(self) -> list[SessionSummary]:
        """List all saved sessions."""
        if not self.storage_dir.exists():
            return []

        summaries = []
        for file_path in self.storage_dir.glob("*.json"):
            if file_path.name == "index.json":
                continue

            try:
                async with aiofiles.open(file_path) as f:
                    content = await f.read()

                session = Session.model_validate_json(content)
                summaries.append(
                    SessionSummary(
                        id=session.id,
                        created_at=session.created_at,
                        updated_at=session.updated_at,
                        message_count=len(session.messages),
                        working_directory=session.working_directory,
                        metadata=session.metadata,
                    )
                )
            except (OSError, json.JSONDecodeError, ValidationError):
                # Skip corrupted or unreadable session files
                continue

        summaries.sort(key=lambda x: x.updated_at, reverse=True)
        return summaries

    async def delete(self, session_id: str) -> bool:
        """Delete a session."""
        path = self._get_session_path(session_id)
        if path.exists():
            path.unlink()
            return True
        return False
