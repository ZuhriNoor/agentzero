"""
Memory Writer node for AgentZero (LangGraph).
Persists STM→LTM, structured memory, and audit log after execution.
"""
from agent_state import AgentState
from memory import ShortTermMemory, LongTermMemory, StructuredMemory, AuditLog
import os
import json

VECTOR_DB_PATH = 'data/vector_db'
STRUCTURED_PATH = 'data/user_profile.json'
LOG_PATH = 'data/audit.log'


def memory_writer(state: AgentState) -> AgentState:
    from memory import log_node
    log_node('memory_writer:entry', state)
    if state.error:
        state.step = "error_handler"
        log_node('memory_writer:error', state)
        return state
    # Persist STM (session state)
    stm = ShortTermMemory()
    for k, v in state.memory.items():
        stm.set(k, v)
    # Persist LTM (vector DB) if new knowledge
    if state.tool_results:
        ltm = LongTermMemory(VECTOR_DB_PATH)
        for result in state.tool_results:
            # Example: store result as embedding (placeholder)
            ltm.add(embedding=None, metadata=result)
    # Persist structured memory (e.g., user profile)
    structured = StructuredMemory(STRUCTURED_PATH)
    data = structured.load()
    data.update(state.memory.get('structured', {}))
    structured.save(data)
    # Audit log
    audit = AuditLog(LOG_PATH)
    audit.append({
        "step": "memory_writer",
        "tool_results": state.tool_results,
        "memory": state.memory
    })
    state.step = "memory_writer"
    log_node('memory_writer:exit', state)
    return state
