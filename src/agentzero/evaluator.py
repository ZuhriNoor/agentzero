"""
Evaluator node for AgentZero (LangGraph).
Inspects the tool results from the executor. If any tool returned an error,
it increments the retry counter and loops back to the planner to self-correct.
"""

from agentzero.agent_state import AgentState

async def evaluator(state: AgentState) -> AgentState:
    from agentzero.memory import log_node
    log_node('evaluator:entry', state)
    
    if state.error:
        state.step = "error_handler"
        log_node('evaluator:error', state)
        return state

    has_error = False
    if state.tool_results:
        for result in state.tool_results:
            if "error" in result:
                has_error = True
            for k, v in result.items():
                if isinstance(v, str) and v.startswith("Error:"):
                    has_error = True

    if has_error:
        state.retries += 1
        if state.retries >= 3:
            # Too many retries, stop looping and pass the error to the response composer
            state.step = "evaluator (max retries)"
        else:
            state.step = "evaluator (retry loop)"
    else:
        # Reset retries on success so subsequent chat turns don't carry it over
        state.retries = 0
        state.step = "evaluator (success)"

    log_node('evaluator:exit', state)
    return state
