"""Session storage implementation."""

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field
import uuid


@dataclass
class Session:
    """Represents a conversation session."""
    id: str = field(default_factory=lambda: str(uuid.uuid4())[:8])
    name: str = ""
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    updated_at: str = field(default_factory=lambda: datetime.now().isoformat())
    model: str = "gpt-4o"
    provider: str = "openai"
    working_directory: str = "."
    messages: list = field(default_factory=list)
    tools: list = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "name": self.name,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "model": self.model,
            "provider": self.provider,
            "working_directory": self.working_directory,
            "messages": self.messages,
            "tools": self.tools,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "Session":
        return cls(
            id=data.get("id", str(uuid.uuid4())[:8]),
            name=data.get("name", ""),
            created_at=data.get("created_at", datetime.now().isoformat()),
            updated_at=data.get("updated_at", datetime.now().isoformat()),
            model=data.get("model", "gpt-4o"),
            provider=data.get("provider", "openai"),
            working_directory=data.get("working_directory", "."),
            messages=data.get("messages", []),
            tools=data.get("tools", []),
        )


class SessionStorage:
    """
    Handles persistence of sessions to disk.

    Sessions are stored in ~/.mini-agent/sessions/
    """

    def __init__(self, base_dir: Optional[str] = None):
        if base_dir:
            self.base_dir = Path(base_dir)
        else:
            self.base_dir = Path.home() / ".mini-agent" / "sessions"

        self._ensure_dir()

    def _ensure_dir(self) -> None:
        """Ensure the session directory exists."""
        self.base_dir.mkdir(parents=True, exist_ok=True)

    def _get_session_path(self, session_id: str) -> Path:
        """Get the path for a session file."""
        return self.base_dir / f"{session_id}.json"

    def save(self, session: Session) -> None:
        """Save a session to disk."""
        session.updated_at = datetime.now().isoformat()
        path = self._get_session_path(session.id)

        with open(path, 'w', encoding='utf-8') as f:
            json.dump(session.to_dict(), f, indent=2)

    def load(self, session_id: str) -> Optional[Session]:
        """Load a session from disk."""
        path = self._get_session_path(session_id)

        if not path.exists():
            return None

        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return Session.from_dict(data)
        except Exception:
            return None

    def delete(self, session_id: str) -> bool:
        """Delete a session from disk."""
        path = self._get_session_path(session_id)

        if path.exists():
            path.unlink()
            return True
        return False

    def list_sessions(self) -> list[Session]:
        """List all saved sessions."""
        sessions = []

        for path in self.base_dir.glob("*.json"):
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                sessions.append(Session.from_dict(data))
            except Exception:
                continue

        # Sort by updated_at descending
        sessions.sort(key=lambda s: s.updated_at, reverse=True)
        return sessions

    def exists(self, session_id: str) -> bool:
        """Check if a session exists."""
        return self._get_session_path(session_id).exists()
