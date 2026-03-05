"""
Final Response Composer node for AgentZero (LangGraph).
Converts action results into natural language using the LLM.
"""
import json
import logging
from agentzero.agent_state import AgentState
from agentzero.llm_service import chat_completion

logger = logging.getLogger("agentzero.response_composer")


async def response_composer(state: AgentState) -> AgentState:
    from agentzero.memory import log_node
    log_node('response_composer:entry', state)

    if state.error:
        state.response = f"Error: {state.error}"
        state.step = "error_handler"
        log_node('response_composer:error', state)
        return state

    if not state.tool_results:
        state.response = "No result."
        state.step = "response_composer"
        log_node('response_composer:exit', state)
        return state

    # Separate chat responses (already natural language) from action results
    chat_responses = []
    action_results = []

    for result in state.tool_results:
        if 'chat' in result:
            chat_responses.append(result['chat'])
        elif 'error' in result:
            action_results.append(f"Error: {result['error']}")
        elif 'action' in result:
            action_results.append(result)

    # Chat responses pass through directly
    if chat_responses and not action_results:
        state.response = "\n".join(chat_responses)
    elif action_results:
        # Convert action results to natural language via LLM
        results_text = json.dumps(action_results, default=str, indent=2)
        messages = [
            {
                "role": "system",
                "content": (
                    "You are Ein, a helpful productivity AI. "
                    "Convert the following action results into a clear, concise, "
                    "natural language response for the user. "
                    "Do NOT fabricate any data — only use what is provided. "
                    "Be friendly and conversational."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User's original request: {state.user_input}\n\n"
                    f"Action results:\n{results_text}"
                ),
            },
        ]
        try:
            state.response = await chat_completion(messages=messages, stream=False, timeout=30)
        except Exception as e:
            logger.error(f"LLM response composition failed: {e}")
            # Fallback: return raw results as strings
            parts = chat_responses + [str(r) for r in action_results]
            state.response = "\n".join(parts)
    else:
        state.response = "Done."

    state.step = "response_composer"
    log_node('response_composer:exit', state)
    return state
