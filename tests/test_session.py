"""Tests for session management."""

import pytest
import tempfile
import os
import json

from mini_agent.session.storage import Session, SessionStorage
from mini_agent.session.manager import SessionManager


class TestSession:
    def test_create(self):
        session = Session()
        assert session.id is not None
        assert len(session.id) == 8
        assert session.model == "gpt-4o"

    def test_create_with_params(self):
        session = Session(
            name="Test Session",
            model="gpt-4",
            working_directory="/tmp"
        )
        assert session.name == "Test Session"
        assert session.model == "gpt-4"
        assert session.working_directory == "/tmp"

    def test_serialize(self):
        session = Session(
            id="test1234",
            name="Test",
            model="gpt-4o",
            messages=[{"role": "user", "content": "hello"}]
        )
        data = session.to_dict()

        assert data["id"] == "test1234"
        assert data["name"] == "Test"
        assert len(data["messages"]) == 1

    def test_deserialize(self):
        data = {
            "id": "test1234",
            "name": "Test",
            "model": "gpt-4",
            "created_at": "2024-01-01T00:00:00",
            "updated_at": "2024-01-01T00:00:00",
            "messages": [{"role": "user", "content": "hello"}]
        }
        session = Session.from_dict(data)

        assert session.id == "test1234"
        assert session.name == "Test"
        assert session.model == "gpt-4"
        assert len(session.messages) == 1


class TestSessionStorage:
    def test_save_and_load(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(base_dir=tmpdir)

            session = Session(id="test1234", name="Test Session")
            storage.save(session)

            # Check file exists
            assert os.path.exists(os.path.join(tmpdir, "test1234.json"))

            # Load it back
            loaded = storage.load("test1234")
            assert loaded is not None
            assert loaded.name == "Test Session"

    def test_load_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(base_dir=tmpdir)
            result = storage.load("nonexistent")
            assert result is None

    def test_delete(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(base_dir=tmpdir)

            session = Session(id="test1234", name="Test")
            storage.save(session)
            assert storage.exists("test1234")

            storage.delete("test1234")
            assert not storage.exists("test1234")

    def test_list_sessions(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(base_dir=tmpdir)

            # Create multiple sessions
            storage.save(Session(id="session1", name="First"))
            storage.save(Session(id="session2", name="Second"))
            storage.save(Session(id="session3", name="Third"))

            sessions = storage.list_sessions()
            assert len(sessions) == 3

            # Should be sorted by updated_at
            ids = [s.id for s in sessions]
            assert "session1" in ids
            assert "session2" in ids
            assert "session3" in ids


class TestSessionManager:
    def test_create_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(base_dir=tmpdir)
            manager = SessionManager(storage=storage)

            session = manager.create_session(name="Test")
            assert session.name == "Test"
            assert manager.current_session == session

    def test_load_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(base_dir=tmpdir)
            manager = SessionManager(storage=storage)

            # Create and save
            session = manager.create_session(name="Test")

            # Reset and load
            manager.current_session = None
            loaded = manager.load_session(session.id)

            assert loaded is not None
            assert loaded.name == "Test"
            assert manager.current_session == loaded

    def test_get_or_create(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(base_dir=tmpdir)
            manager = SessionManager(storage=storage)

            # Should create new session
            session1 = manager.get_or_create_session()
            assert session1 is not None

            # Should load existing
            session2 = manager.get_or_create_session(session_id=session1.id)
            assert session2.id == session1.id

            # Should create new if ID doesn't exist
            session3 = manager.get_or_create_session(session_id="nonexistent")
            assert session3.id != session1.id

    def test_update_messages(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(base_dir=tmpdir)
            manager = SessionManager(storage=storage)

            manager.create_session()
            messages = [{"role": "user", "content": "hello"}]
            manager.update_session_messages(messages)

            assert manager.current_session.messages == messages

    def test_get_session_info(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            storage = SessionStorage(base_dir=tmpdir)
            manager = SessionManager(storage=storage)

            # No session yet
            assert manager.get_session_info() is None

            # Create session
            manager.create_session(name="Test")
            info = manager.get_session_info()

            assert info is not None
            assert info["name"] == "Test"
