"""
Example: Error handler node for LangGraph (production-grade).
Handles errors, logs them, and provides deterministic fallback.
"""
from agent_state import AgentState
from memory import AuditLog

LOG_PATH = 'data/audit.log'

def error_handler(state: AgentState) -> AgentState:
    from memory import log_node
    log_node('error_handler:entry', state)
    # Log the error
    audit = AuditLog(LOG_PATH)
    audit.append({
        "step": state.step,
        "error": state.error,
        "user_input": state.user_input
    })
    # Deterministic fallback: clear sensitive state, set response
    state.memory.clear()
    state.response = "An error occurred. The action was not completed. Please try again or contact support."
    log_node('error_handler:exit', state)
    return state
