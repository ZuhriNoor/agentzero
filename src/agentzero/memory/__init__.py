"""
Local memory modules for AgentZero: STM, LTM, Structured, AuditLog.
Thread-safe file operations with per-file locking.
"""
import os
import json
import logging
import threading
from typing import Any, Dict, List

logger = logging.getLogger("agentzero.memory")

# Per-file locks to prevent concurrent writes to the same file
_file_locks: Dict[str, threading.Lock] = {}
_file_locks_lock = threading.Lock()


def _get_file_lock(path: str) -> threading.Lock:
    """Get or create a lock for a specific file path."""
    with _file_locks_lock:
        if path not in _file_locks:
            _file_locks[path] = threading.Lock()
        return _file_locks[path]


# Node-level trace logging + metrics instrumentation
LOG_PIPE_PATH = 'data/node_trace.log'
_trace_lock = threading.Lock()
_node_entry_times: Dict[str, float] = {}  # node_name -> perf_counter at entry
_entry_times_lock = threading.Lock()


def log_node(step, state):
    import time as _time
    from agentzero.metrics import MetricsCollector
    
    entry = {
        'step': step,
        'user_input': getattr(state, 'user_input', None),
        'intent': getattr(state, 'intent', None),
        'plan': getattr(state, 'plan', None),
        'error': getattr(state, 'error', None),
        'permissions': getattr(state, 'permissions', None),
        'tool_results': getattr(state, 'tool_results', None),
        'response': getattr(state, 'response', None),
    }
    with _trace_lock:
        with open(LOG_PIPE_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    # Metrics instrumentation
    try:
        collector = MetricsCollector()
        node_name = step.split(':')[0]  # e.g. "supervisor" from "supervisor:entry"
        phase = step.split(':')[1] if ':' in step else ''
        
        if phase == 'entry':
            with _entry_times_lock:
                _node_entry_times[node_name] = _time.perf_counter()
        elif phase in ('exit', 'error'):
            with _entry_times_lock:
                start = _node_entry_times.pop(node_name, None)
            if start is not None:
                duration_ms = (_time.perf_counter() - start) * 1000
                had_error = phase == 'error' or bool(getattr(state, 'error', None))
                domain = getattr(state, 'intent', None) or 'unknown'
                collector.record(node_name, duration_ms, had_error=had_error, domain=domain)
    except Exception:
        pass  # Never let metrics crash the pipeline


class ShortTermMemory:
    def __init__(self):
        self.state: Dict[str, Any] = {}

    def get(self, key: str) -> Any:
        return self.state.get(key)

    def set(self, key: str, value: Any):
        self.state[key] = value

    def clear(self):
        self.state.clear()


class LongTermMemory:
    def __init__(self, db_path: str):
        import chromadb
        self.db_path = db_path
        self.client = chromadb.PersistentClient(path=db_path)
        self.collection = self.client.get_or_create_collection(name="agent_memory")

    def add(self, text: str, metadata: dict = None):
        import uuid
        doc_id = str(uuid.uuid4())
        self.collection.add(
            documents=[text],
            metadatas=[metadata] if metadata else None,
            ids=[doc_id]
        )

    def query(self, query_text: str, top_k=5) -> List[str]:
        try:
            results = self.collection.query(
                query_texts=[query_text],
                n_results=top_k
            )
            if results and results.get("documents") and len(results["documents"]) > 0:
                return results["documents"][0]
            return []
        except Exception as e:
            logger.error(f"ChromaDB Query Error: {e}")
            return []


class StructuredMemory:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._lock = _get_file_lock(file_path)
        if not os.path.exists(file_path):
            os.makedirs(os.path.dirname(file_path), exist_ok=True)
            with open(file_path, 'w') as f:
                json.dump({}, f)

    def load(self) -> Dict[str, Any]:
        with self._lock:
            try:
                with open(self.file_path, 'r') as f:
                    content = f.read().strip()
                    if not content:
                        return {}
                    return json.loads(content)
            except (json.JSONDecodeError, FileNotFoundError):
                return {}

    def save(self, data: Dict[str, Any]):
        with self._lock:
            with open(self.file_path, 'w') as f:
                json.dump(data, f, indent=2)


class AuditLog:
    def __init__(self, log_path: str):
        self.log_path = log_path
        self._lock = _get_file_lock(log_path)

    def append(self, entry: Dict[str, Any]):
        with self._lock:
            with open(self.log_path, 'a') as f:
                f.write(json.dumps(entry) + '\n')

    def read_all(self) -> List[Dict[str, Any]]:
        with self._lock:
            if not os.path.exists(self.log_path):
                return []
            with open(self.log_path, 'r') as f:
                return [json.loads(line) for line in f if line.strip()]
