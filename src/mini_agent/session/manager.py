"""Session manager implementation."""

from datetime import datetime
from typing import Optional

from .storage import Session, SessionStorage


class SessionManager:
    """
    Manages sessions for the agent.

    Provides high-level operations for creating, loading, and saving sessions.
    """

    def __init__(self, storage: Optional[SessionStorage] = None):
        self.storage = storage or SessionStorage()
        self.current_session: Optional[Session] = None

    def create_session(
        self,
        name: str = "",
        model: str = "gpt-4o",
        provider: str = "openai",
        working_directory: str = ".",
    ) -> Session:
        """Create a new session."""
        session = Session(
            name=name or datetime.now().strftime("Session %Y-%m-%d %H:%M"),
            model=model,
            provider=provider,
            working_directory=working_directory,
        )
        self.storage.save(session)
        self.current_session = session
        return session

    def load_session(self, session_id: str) -> Optional[Session]:
        """Load an existing session."""
        session = self.storage.load(session_id)
        if session:
            self.current_session = session
        return session

    def save_session(self, session: Optional[Session] = None) -> None:
        """Save the current or specified session."""
        target = session or self.current_session
        if target:
            self.storage.save(target)

    def delete_session(self, session_id: str) -> bool:
        """Delete a session."""
        if self.current_session and self.current_session.id == session_id:
            self.current_session = None
        return self.storage.delete(session_id)

    def list_sessions(self) -> list[Session]:
        """List all saved sessions."""
        return self.storage.list_sessions()

    def get_or_create_session(
        self,
        session_id: Optional[str] = None,
        model: str = "gpt-4o",
        provider: str = "openai",
        working_directory: str = ".",
    ) -> Session:
        """Get an existing session or create a new one."""
        if session_id:
            session = self.load_session(session_id)
            if session:
                return session

        return self.create_session(
            model=model,
            provider=provider,
            working_directory=working_directory,
        )

    def update_session_messages(self, messages: list) -> None:
        """Update messages in the current session."""
        if self.current_session:
            self.current_session.messages = messages
            self.save_session()

    def get_session_info(self) -> Optional[dict]:
        """Get info about the current session."""
        if not self.current_session:
            return None

        return {
            "id": self.current_session.id,
            "name": self.current_session.name,
            "model": self.current_session.model,
            "message_count": len(self.current_session.messages),
            "created_at": self.current_session.created_at,
            "updated_at": self.current_session.updated_at,
        }
