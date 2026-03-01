"""
Final Response Composer node for AgentZero (LangGraph).
Formats the final response for the user, using tool/skill results and context.
Handles chat responses.
"""
from agent_state import AgentState


def response_composer(state: AgentState) -> AgentState:
    from memory import log_node
    log_node('response_composer:entry', state)
    if state.error:
        state.response = f"Error: {state.error}"
        state.step = "error_handler"
        log_node('response_composer:error', state)
        return state
    elif state.tool_results:
        # Compose a user-friendly response from tool/skill/chat results
        responses = []
        for result in state.tool_results:
            if 'chat' in result:
                responses.append(result['chat'])
            elif 'error' in result:
                responses.append(f"[Error] {result['error']}")
            elif 'tool' in result and result['tool'] == 'add_event' and result.get('result') is True:
                responses.append("Event added to calendar.")
            elif 'tool' in result and result['tool'] == 'list_events' and isinstance(result.get('result'), list):
                events = result['result']
                if not events:
                    responses.append("You have no events for that period.")
                else:
                    # Use LLM to format the response naturally
                    from llm_service import generate_completion
                    
                    event_list_str = "\n".join([f"- {e['name']} at {e['begin']}" for e in events])
                    prompt = (
                        "You are a helpful assistant. The user asked about their calendar events.\n"
                        f"User Query: {state.user_input}\n"
                        f"Events Found:\n{event_list_str}\n\n"
                        "Please provide a natural language summary of these events. "
                        "Do not make up any events. Be concise and friendly."
                    )
                    
                    try:
                        natural_response = generate_completion(prompt=prompt, stream=False, timeout=30)
                        responses.append(natural_response)
                    except Exception as e:
                        # Fallback to simple listing if LLM fails
                        responses.append(f"You have {len(events)} events:\n" + event_list_str)

            elif 'result' in result:
                responses.append(str(result['result']))
        state.response = "\n".join(responses)
    else:
        state.response = "No result."
    state.step = "response_composer"
    log_node('response_composer:exit', state)
    return state
