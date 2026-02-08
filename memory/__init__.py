import threading

# Node-level logging utility
LOG_PIPE_PATH = 'data/node_trace.log'
LOG_LOCK = threading.Lock()
def log_node(step, state):
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
    with LOG_LOCK:
        with open(LOG_PIPE_PATH, 'a') as f:
            f.write(json.dumps(entry) + '\n')
"""
Local memory modules for AgentZero: STM, LTM, Structured, AuditLog.
"""
import os
import json
from typing import Any, Dict, List

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
        # Placeholder for vector DB (e.g., ChromaDB)
        self.db_path = db_path
        # ...init vector DB...

    def add(self, embedding, metadata):
        # ...add to vector DB...
        pass

    def query(self, embedding, top_k=5):
        # ...query vector DB...
        return []

class StructuredMemory:
    def __init__(self, file_path: str):
        self.file_path = file_path
        if not os.path.exists(file_path):
            with open(file_path, 'w') as f:
                json.dump({}, f)

    def load(self) -> Dict[str, Any]:
        try:
            with open(self.file_path, 'r') as f:
                content = f.read().strip()
                if not content:
                    return {}
                return json.loads(content)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def save(self, data: Dict[str, Any]):
        with open(self.file_path, 'w') as f:
            json.dump(data, f, indent=2)

class AuditLog:
    def __init__(self, log_path: str):
        self.log_path = log_path

    def append(self, entry: Dict[str, Any]):
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')

    def read_all(self) -> List[Dict[str, Any]]:
        if not os.path.exists(self.log_path):
            return []
        with open(self.log_path, 'r') as f:
            return [json.loads(line) for line in f if line.strip()]
