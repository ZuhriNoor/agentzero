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
                    responses.append("You have no events for that date.")
                else:
                    lines = [f"You have {len(events)} event{'s' if len(events) > 1 else ''}:"]
                    for e in events:
                        name = e.get('name', 'Untitled')
                        begin = e.get('begin', '')
                        # Try to format time nicely
                        try:
                            from dateutil.parser import parse as parse_date
                            dt = parse_date(begin)
                            time_str = dt.strftime('%Y-%m-%d %H:%M') if dt.hour or dt.minute else dt.strftime('%Y-%m-%d')
                        except Exception:
                            time_str = begin
                        lines.append(f"- {name} at {time_str}")
                    responses.append("\n".join(lines))
            elif 'result' in result:
                responses.append(str(result['result']))
        state.response = "\n".join(responses)
    else:
        state.response = "No result."
    state.step = "response_composer"
    log_node('response_composer:exit', state)
    return state
