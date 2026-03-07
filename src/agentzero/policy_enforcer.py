"""
Policy Enforcer node for AgentZero (LangGraph).
Enforces intent-level gating and pre-authorizes actions based on the POLICY dict.
Per-action permission checks happen in the executor at dispatch time.
"""
from agentzero.agent_state import AgentState
from agentzero.memory import AuditLog

# Policy config — controls which actions are allowed
POLICY = {
    "chat": {"allowed": True, "reason": "General conversation allowed"},
    "add_task": {"allowed": True, "reason": "Task creation allowed"},
    "list_tasks": {"allowed": True, "reason": "Task listing allowed"},
    "edit_task": {"allowed": True, "reason": "Task modification allowed"},
    "complete_task": {"allowed": True, "reason": "Task completion allowed"},
    "add_event": {"allowed": True, "reason": "User scheduling allowed"},
    "list_events": {"allowed": True, "reason": "Calendar event listing allowed"},
    "plan_day": {"allowed": True, "reason": "Daily planning allowed"},
    "plan_week": {"allowed": True, "reason": "Weekly planning allowed"},
    "get_file": {"allowed": False, "reason": "File access not permitted by default"},
    "query_note": {"allowed": True, "reason": "Note search allowed"},
    "list_habits": {"allowed": True, "reason": "Habit listing allowed"},
    "add_habit": {"allowed": True, "reason": "Habit creation allowed"},
    "delete_habit": {"allowed": True, "reason": "Habit deletion allowed"},
    "track_habit": {"allowed": True, "reason": "Habit tracking allowed"},
    "parse_message": {"allowed": True, "reason": "LLM message parsing allowed"},
    "remember_fact": {"allowed": True, "reason": "Memory storage allowed"},
}

LOG_PATH = 'data/audit.log'

def policy_enforcer(state: AgentState) -> AgentState:
    from agentzero.memory import log_node
    log_node('policy_enforcer:entry', state)
    if state.error:
        state.step = "error_handler"
        log_node('policy_enforcer:error', state)
        return state

    intent = state.intent or "unknown"
    policy = POLICY.get(intent, {"allowed": False, "reason": "Unknown or unconfigured intent"})
    allowed = policy["allowed"]
    reason = policy["reason"]

    # Audit log the intent decision
    audit = AuditLog(LOG_PATH)
    audit.append({
        "step": "policy_enforcer",
        "intent": intent,
        "allowed": allowed,
        "reason": reason,
        "user_input": state.user_input
    })

    # Block disallowed intents
    if not allowed:
        state.error = f"Action '{intent}' blocked: {reason}"
        state.step = "error_handler"
        log_node('policy_enforcer:error', state)
        return state

    # Pre-authorize all allowed actions from POLICY
    # The executor will check these at dispatch time
    for action_name, action_policy in POLICY.items():
        if action_policy["allowed"]:
            state.permissions[action_name] = True

    state.step = "policy_enforcer"
    log_node('policy_enforcer:exit', state)
    return state
