import pytest
from agentzero.intent_router import classify_speech_act, build_prompt, classify_intent, intent_router
from agentzero.agent_state import AgentState

def test_classify_speech_act():
    assert classify_speech_act("what do I have today?") == "question"
    assert classify_speech_act("add buy milk to tasks") == "command"
    assert classify_speech_act("schedule a meeting") == "command"
    assert classify_speech_act("hello there") == "chat"

def test_build_prompt():
    prompt = build_prompt("add buy milk", "command")
    assert "add_event" in prompt
    assert "add_task" in prompt
    assert "User input: add buy milk" in prompt

@pytest.mark.asyncio
async def test_classify_intent_known(mock_generate_completion):
    mock_generate_completion.return_value = "add_task"
    intent = await classify_intent("add buy milk to tasks")
    assert intent == "add_task"
    mock_generate_completion.assert_awaited()

@pytest.mark.asyncio
async def test_classify_intent_unknown_fallback(mock_generate_completion):
    mock_generate_completion.return_value = "some_random_word"
    intent = await classify_intent("do some random stuff")
    assert intent == "chat" # Because some_random_word is not in ALL_INTENTS

@pytest.mark.asyncio
async def test_intent_router_node(mock_generate_completion):
    mock_generate_completion.return_value = "list_events"
    state = AgentState(user_input="what's on my calendar")
    
    new_state = await intent_router(state)
    assert new_state.intent == "list_events"
    assert new_state.step == "intent_router"
    
@pytest.mark.asyncio
async def test_intent_router_error_passthrough():
    state = AgentState(user_input="hello", error="Something broke earlier")
    new_state = await intent_router(state)
    assert new_state.step == "error_handler"
