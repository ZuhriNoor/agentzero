import sqlite3
import json
import time
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, List

logger = logging.getLogger("agentzero.session_store")

class SessionStore(ABC):
    """Abstract base class for session persistence."""
    
    @abstractmethod
    def get(self, session_id: str) -> Dict[str, Any]:
        """Retrieve a session by ID. Must return a dict with a 'history' list."""
        pass

    @abstractmethod
    def set(self, session_id: str, history: List[Dict[str, str]]) -> None:
        """Store the history list for a session."""
        pass

    @abstractmethod
    def delete(self, session_id: str) -> None:
        """Explicitly delete a session."""
        pass

    @abstractmethod
    def cleanup(self, max_age_seconds: int = 3600) -> int:
        """Remove sessions older than max_age_seconds. Returns number deleted."""
        pass

class SQLiteSessionStore(SessionStore):
    """SQLite-backed implementation of SessionStore."""
    
    def __init__(self, db_path: str = "data/sessions.db"):
        self.db_path = db_path
        self._init_db()

    def _get_connection(self):
        # Timeout 5.0s, isolation_level=None for autocommit
        conn = sqlite3.connect(self.db_path, timeout=5.0)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        try:
            with self._get_connection() as conn:
                # Use WAL mode for better concurrency (reads don't block writes)
                conn.execute("PRAGMA journal_mode=WAL")
                conn.execute(
                    """
                    CREATE TABLE IF NOT EXISTS sessions (
                        session_id TEXT PRIMARY KEY,
                        history TEXT NOT NULL,
                        last_accessed REAL NOT NULL
                    )
                    """
                )
                conn.execute(
                    "CREATE INDEX IF NOT EXISTS idx_sessions_last_accessed ON sessions(last_accessed)"
                )
        except Exception as e:
            logger.error(f"Failed to initialize SQLite session store: {e}")

    def get(self, session_id: str) -> Dict[str, Any]:
        try:
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "SELECT history, last_accessed FROM sessions WHERE session_id = ?",
                    (session_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    history_json = row["history"]
                    # Decrypt if encryption is enabled
                    from agentzero.encryption import decrypt_data
                    history_json = decrypt_data(history_json)
                    try:
                        history = json.loads(history_json)
                    except json.JSONDecodeError:
                        history = []
                    
                    # Update last_accessed on read to prevent expiring active sessions
                    now = time.time()
                    conn.execute(
                        "UPDATE sessions SET last_accessed = ? WHERE session_id = ?",
                        (now, session_id)
                    )
                    
                    return {"history": history, "last_accessed": now}
        except Exception as e:
            logger.error(f"Error fetching session {session_id}: {e}")
            
        # Return default empty structured dict if missing or error
        return {"history": [], "last_accessed": time.time()}

    def set(self, session_id: str, history: List[Dict[str, str]]) -> None:
        try:
            now = time.time()
            history_json = json.dumps(history)
            # Encrypt if encryption is enabled
            from agentzero.encryption import encrypt_data
            history_json = encrypt_data(history_json)
            
            with self._get_connection() as conn:
                conn.execute(
                    """
                    INSERT INTO sessions (session_id, history, last_accessed)
                    VALUES (?, ?, ?)
                    ON CONFLICT(session_id) DO UPDATE SET
                        history = excluded.history,
                        last_accessed = excluded.last_accessed
                    """,
                    (session_id, history_json, now)
                )
        except Exception as e:
            logger.error(f"Error saving session {session_id}: {e}")

    def delete(self, session_id: str) -> None:
        try:
            with self._get_connection() as conn:
                conn.execute("DELETE FROM sessions WHERE session_id = ?", (session_id,))
        except Exception as e:
            logger.error(f"Error deleting session {session_id}: {e}")

    def cleanup(self, max_age_seconds: int = 3600) -> int:
        try:
            cutoff_time = time.time() - max_age_seconds
            with self._get_connection() as conn:
                cursor = conn.execute(
                    "DELETE FROM sessions WHERE last_accessed < ?",
                    (cutoff_time,)
                )
                return cursor.rowcount
        except Exception as e:
            logger.error(f"Error cleaning up sessions: {e}")
            return 0
