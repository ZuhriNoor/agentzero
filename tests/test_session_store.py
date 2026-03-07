import pytest
import time
import os
from agentzero.session_store import SQLiteSessionStore

@pytest.fixture
def temp_store(tmp_path):
    """Provides a fresh SessionStore backed by a temporary SQLite file."""
    db_path = tmp_path / "test_sessions.db"
    store = SQLiteSessionStore(str(db_path))
    return store

def test_get_nonexistent_session(temp_store):
    data = temp_store.get("unknown_user")
    assert data["history"] == []
    assert "last_accessed" in data

def test_set_and_get_session(temp_store):
    history = [
        {"role": "user", "content": "hello"},
        {"role": "assistant", "content": "hi there"}
    ]
    
    # Set data
    temp_store.set("user1", history)
    
    # Retrieve data
    data = temp_store.get("user1")
    assert data["history"] == history
    
def test_update_session_history(temp_store):
    history1 = [{"role": "user", "content": "1"}]
    temp_store.set("user1", history1)
    
    history2 = [{"role": "user", "content": "1"}, {"role": "assistant", "content": "2"}]
    temp_store.set("user1", history2)
    
    data = temp_store.get("user1")
    assert data["history"] == history2

def test_delete_session(temp_store):
    temp_store.set("user1", [{"role": "user", "content": "hello"}])
    temp_store.delete("user1")
    
    data = temp_store.get("user1")
    assert data["history"] == []

def test_cleanup_expired_sessions(temp_store):
    # Insert a session
    temp_store.set("expired_user", [{"role": "user", "content": "old message"}])
    
    # Simulate time passing by writing a very old `last_accessed` directly to DB
    old_time = time.time() - 4000
    with temp_store._get_connection() as conn:
        conn.execute(
            "UPDATE sessions SET last_accessed = ? WHERE session_id = ?",
            (old_time, "expired_user")
        )
        
    # Also add a fresh session
    temp_store.set("fresh_user", [{"role": "user", "content": "new message"}])
    
    # Run cleanup (default 3600s TTL)
    deleted_count = temp_store.cleanup()
    
    assert deleted_count == 1
    
    # Verify expired was deleted
    data = temp_store.get("expired_user")
    assert data["history"] == []
    
    # Verify fresh survived
    data = temp_store.get("fresh_user")
    assert len(data["history"]) == 1

def test_persistence_across_instances(tmp_path):
    """Verify that writing to the DB and creating a NEW store instance retains the data."""
    db_path = tmp_path / "persistent.db"
    
    store1 = SQLiteSessionStore(str(db_path))
    history = [{"role": "user", "content": "persist me"}]
    store1.set("persist_user", history)
    
    # Create entirely new instance pointing to same file
    store2 = SQLiteSessionStore(str(db_path))
    data = store2.get("persist_user")
    
    assert data["history"] == history
