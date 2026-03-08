"""
Policy Enforcer node for AgentZero (LangGraph).
Enforces intent-level gating and pre-authorizes actions based on the POLICY dict.
Per-action permission checks happen in the executor at dispatch time.
"""
from agentzero.agent_state import AgentState
from agentzero.memory import AuditLog

# Policy config — controls which domains are allowed
POLICY = {
    "chat": {"allowed": True, "reason": "General conversation allowed"},
    "task": {"allowed": True, "reason": "Task and Habit management allowed"},
    "calendar": {"allowed": True, "reason": "Calendar and Planning allowed"},
    "knowledge": {"allowed": True, "reason": "Knowledge and Memory allowed"},
}

LOG_PATH = 'data/audit.log'

def policy_enforcer(state: AgentState) -> AgentState:
    from agentzero.memory import log_node
    log_node('policy_enforcer:entry', state)
    if state.error:
        state.step = "error_handler"
        log_node('policy_enforcer:error', state)
        return state

    domain = state.intent or "unknown"
    policy = POLICY.get(domain, {"allowed": False, "reason": "Unknown or unconfigured domain"})
    allowed = policy["allowed"]
    reason = policy["reason"]

    # Audit log the domain decision
    audit = AuditLog(LOG_PATH)
    audit.append({
        "step": "policy_enforcer",
        "domain": domain,
        "allowed": allowed,
        "reason": reason,
        "user_input": state.user_input
    })

    # Block disallowed domains
    if not allowed:
        state.error = f"Action '{domain}' blocked: {reason}"
        state.step = "error_handler"
        log_node('policy_enforcer:error', state)
        return state

    # Map domain to specific permissions for executor
    if domain == "task":
        state.permissions.update({
            "add_task": True, "list_tasks": True, "edit_task": True, "complete_task": True,
            "add_habit": True, "list_habits": True, "delete_habit": True, "track_habit": True
        })
    elif domain == "calendar":
        state.permissions.update({
            "add_event": True, "list_events": True, "plan_day": True, "plan_week": True
        })
    elif domain == "knowledge":
        state.permissions.update({
            "remember_fact": True, "query_note": True, "get_file": False
        })
    elif domain == "chat":
        # Chat bypasses tools, goes to executor directly
        pass

    state.step = "policy_enforcer"
    log_node('policy_enforcer:exit', state)
    return state
