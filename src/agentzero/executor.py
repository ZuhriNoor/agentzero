"""
Executor node for AgentZero (LangGraph).
Executes planned actions using the unified action registry.
Handles 'chat' intent by generating a conversational response using the LLM.
"""
import asyncio

from agentzero.agent_state import AgentState
from agentzero.actions import load_actions
from agentzero.llm_service import chat_completion

ACTIONS = load_actions()


async def chat_with_llm(message: str, history: list = None, rag_context: list = None) -> str:
    system_prompt = "Your name is Ein. You are a helpful, productivity AI agent."
    if rag_context:
        system_prompt += "\n\nRelevant Context about the User:\n" + "\n".join([f"- {fact}" for fact in rag_context])
        
    messages = [{"role": "system", "content": system_prompt}]
    if history:
        messages.extend(history)
    messages.append({"role": "user", "content": message})
    try:
        return await chat_completion(messages=messages, stream=False, timeout=120)
    except Exception as e:
        return f"[Chat error: {str(e)}]"


async def executor(state: AgentState) -> AgentState:
    from agentzero.memory import log_node
    log_node('executor:entry', state)
    if state.error:
        state.step = "error_handler"
        log_node('executor:error', state)
        return state
    results = []
    
    # Check if we skipped planner (chat intent with no plan)
    if not state.plan and state.intent == "chat":
        state.plan = [{"type": "chat", "params": state.user_input}]
        
    if not state.plan:
        state.error = "No plan to execute."
        state.step = "error_handler"
        return state

    for action in state.plan:
        action_type = action.get("type")
        params = action.get("params", {})

        # Handle chat intent directly
        if action_type == "chat":
            if isinstance(params, str):
                user_message = params
            else:
                user_message = params.get("message", state.user_input)
            rag_context = state.context.get("rag") if state.context else None
            chat_response = await chat_with_llm(user_message, state.chat_history, rag_context)
            results.append({"chat": chat_response})
            continue

        # Check permissions
        if action_type != "ask_user" and not state.permissions.get(action_type, False):
            results.append({"error": f"Permission denied for {action_type}"})
            continue

        # Handle Conversational Slot-Filling directly
        if action_type == "ask_user":
            question = params.get("question", "Could you provide more details?")
            results.append({"chat": question})
            continue

        # Unified action dispatch (supports both sync and async actions)
        if action_type in ACTIONS:
            try:
                runner = ACTIONS[action_type].run
                if asyncio.iscoroutinefunction(runner):
                    result = await runner(**params)
                else:
                    result = runner(**params)
                results.append({"action": action_type, "result": result})
            except Exception as e:
                results.append({"action": action_type, "error": str(e)})
        else:
            results.append({"error": f"Unknown action type: {action_type}"})

    state.tool_results = results
    state.step = "executor"
    log_node('executor:exit', state)
    return state
