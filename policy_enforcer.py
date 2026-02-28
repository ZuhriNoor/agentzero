"""
Policy Enforcer node for AgentZero (LangGraph).
Enforces explicit permission gating and privacy/safety policies for all actions.
"""
from agent_state import AgentState
from memory import AuditLog

# Example: static policy config (could be loaded from file)
POLICY = {
    "chat": {"allowed": True, "reason": "General conversation allowed"},
    "add_task": {"allowed": True, "reason": "User productivity"},
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
    # ...extend as needed...
}

LOG_PATH = 'data/audit.log'

def policy_enforcer(state: AgentState) -> AgentState:
    from memory import log_node
    log_node('policy_enforcer:entry', state)
    if state.error:
        state.step = "error_handler"
        log_node('policy_enforcer:error', state)
        return state
    intent = state.intent or "unknown"
    policy = POLICY.get(intent, {"allowed": False, "reason": "Unknown or unconfigured intent"})
    allowed = policy["allowed"]
    reason = policy["reason"]
    # Log the policy decision
    audit = AuditLog(LOG_PATH)
    audit.append({
        "step": "policy_enforcer",
        "intent": intent,
        "allowed": allowed,
        "reason": reason,
        "user_input": state.user_input
    })
    # Enforce policy
    if not allowed:
        state.error = f"Action '{intent}' blocked: {reason}"
        state.step = "error_handler"
        log_node('policy_enforcer:error', state)
        return state
    state.permissions[intent] = allowed
    # Also grant permissions for all action types in the plan
    if state.plan:
        for action in state.plan:
            action_type = action.get("type")
            if action_type and action_type in POLICY:
                state.permissions[action_type] = POLICY[action_type]["allowed"]
    
    # If intent is chat, pre-authorize safe tools so the planner can use them freely
    if intent == "chat":
        SAFE_TOOLS = ["add_task", "add_event", "list_events", "list_habits", "add_habit", "track_habit", "query_note", "plan_day", "plan_week", "remember_fact"]
        for tool in SAFE_TOOLS:
            if tool in POLICY and POLICY[tool]["allowed"]:
                state.permissions[tool] = True
    state.step = "policy_enforcer"
    log_node('policy_enforcer:exit', state)
    return state
