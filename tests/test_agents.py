import pytest
import datetime
import json
from agentzero.agents import calendar_agent_node, task_agent_node, knowledge_agent_node

@pytest.mark.asyncio
async def test_calendar_agent_ask_user(base_state, mock_chat_completion):
    base_state.user_input = "Schedule a meeting"
    base_state.intent = "calendar"
    
    # LLM simulates Conversational Slot Filling by asking for missing time/date
    mock_chat_completion.return_value = '{"plan": [{"type": "ask_user", "params": {"question": "What time?"}}]}'
    
    new_state = await calendar_agent_node(base_state)
    
    # Verify plan parsing
    assert new_state.step == "calendar_agent"
    assert len(new_state.plan) == 1
    assert new_state.plan[0]["type"] == "ask_user"
    assert new_state.plan[0]["params"]["question"] == "What time?"

@pytest.mark.asyncio
async def test_task_agent_standard_plan(base_state, mock_chat_completion):
    base_state.user_input = "Remind me to buy milk by tomorrow 5 PM"
    base_state.intent = "task"
    
    mock_chat_completion.return_value = '{"plan": [{"type": "add_task", "params": {"task": "buy milk", "deadline": "2026-02-15 17:00"}}]}'
    
    new_state = await task_agent_node(base_state)
    
    assert new_state.step == "task_agent"
    assert new_state.plan[0]["type"] == "add_task"
    assert new_state.plan[0]["params"]["task"] == "buy milk"

@pytest.mark.asyncio
async def test_knowledge_agent_error_passthrough(base_state, mock_chat_completion):
    base_state.intent = "knowledge"
    # Malformed JSON is gracefully caught by json.loads('{}')
    mock_chat_completion.return_value = 'Bad AI Response'
    
    new_state = await knowledge_agent_node(base_state)
    assert new_state.step == "knowledge_agent"
    assert new_state.plan == [] 
