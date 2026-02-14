"""
Intent Router node for AgentZero (LangGraph).
Production-grade two-stage intent classification.
"""


from agent_state import AgentState
import requests
from typing import Set
from ollama_config import OLLAMA_MODEL, OLLAMA_API_URL


# ======================
# Ollama configuration is now loaded from .env via ollama_config.py


# ======================
# Intent definitions
# ======================

ALL_INTENTS: Set[str] = {
    "chat",
    "add_task",
    "add_event",
    "list_events",
    "get_file",
    "query_note",
    "plan_day",
    "plan_week",
    "list_habits",
    "add_habit",
    "delete_habit",
    "track_habit",
    "unknown",
}


INTENT_BUCKETS = {
    "question": {
        "list_events",
        "list_habits",
        "query_note",
        "get_file",
        "chat",
        "unknown",
    },
    "command": {
        "add_task",
        "add_event",
        "add_habit",
        "delete_habit",
        "track_habit",
        "plan_day",
        "plan_week",
        "chat",
        "unknown",
    },
    "chat": {
        "chat",
        "add_event",
        "add_task",
        "add_habit",
        "track_habit",
        "plan_day",
        "plan_week",
        "unknown",
    },
}


# ======================
# Stage 1: Speech-act classifier (deterministic)
# ======================

def classify_speech_act(text: str) -> str:
    t = text.lower().strip()

    QUESTION_PREFIXES = (
        "what", "do i", "what's", "show", "list",
        "anything", "when", "where", "who"
    )

    COMMAND_PREFIXES = (
        "add", "schedule", "create", "delete",
        "track", "plan", "remind", "put"
    )

    if t.endswith("?"):
        return "question"

    if t.startswith(QUESTION_PREFIXES):
        return "question"

    if t.startswith(COMMAND_PREFIXES):
        return "command"

    return "chat"


# ======================
# Stage 2: LLM intent classifier (constrained)
# ======================

def build_prompt(user_input: str, speech_act: str) -> str:
    allowed_intents = "\n".join(sorted(INTENT_BUCKETS[speech_act]))

    return (
        "You are an intent classifier.\n\n"
        f"Speech act: {speech_act}\n\n"
        "Allowed intents:\n"
        f"{allowed_intents}\n\n"
        "Rules:\n"
        "- Return exactly ONE intent from the allowed list\n"
        "- Do not explain\n"
        "- Do not add punctuation\n\n"
        f"User input: {user_input}\n"
        "Intent:"
    )


def classify_intent_llm(user_input: str, speech_act: str) -> str:
    prompt = build_prompt(user_input, speech_act)

    payload = {
        "model": OLLAMA_MODEL,
        "prompt": prompt,
        "stream": False,
        "options": {
            "temperature": 0.0,
            "top_p": 1.0,
        }
    }

    try:
        response = requests.post(
            OLLAMA_API_URL,
            json=payload,
            timeout=10
        )
        response.raise_for_status()

        raw = response.json().get("response", "")
        intent = raw.strip().lower().split()[0]

        if intent in INTENT_BUCKETS[speech_act]:
            return intent

    except Exception:
        pass

    return "unknown"


# ======================
# Public router API
# ======================

def classify_intent(user_input: str) -> str:
    speech_act = classify_speech_act(user_input)
    intent = classify_intent_llm(user_input, speech_act)

    if intent in ALL_INTENTS and intent != "unknown":
        return intent

    return "chat"


# ======================
# LangGraph node
# ======================

def intent_router(state: AgentState) -> AgentState:
    from memory import log_node

    log_node("intent_router:entry", state)

    if state.error:
        state.step = "error_handler"
        log_node("intent_router:error", state)
        return state

    state.intent = classify_intent(state.user_input)
    state.step = "intent_router"

    log_node("intent_router:exit", state)
    return state
