import pytest
import datetime
import json
from agentzero.planner import planner

@pytest.mark.asyncio
async def test_planner_prompt_construction(base_state, mock_generate_completion):
    """
    Tests that the prompt correctly injects today's date and the user's intent.
    """
    # Setup state
    base_state.user_input = "I have a meeting this Sunday"
    base_state.intent = "add_event"
    
    # Mock LLM response
    mock_generate_completion.return_value = '{"plan": [{"type": "add_event", "params": {"name": "meeting", "date": "2026-02-15"}}]}'
    
    new_state = await planner(base_state)
    
    # Verify mock was called
    mock_generate_completion.assert_awaited()
    args, kwargs = mock_generate_completion.call_args
    prompt = kwargs['prompt']
    
    now = datetime.datetime.now()
    expected_day = now.strftime('%A')
    
    # Check that current context was injected
    assert expected_day in prompt
    assert "Intent: add_event" in prompt
    assert "User: I have a meeting this Sunday" in prompt
    
    # Verify plan parsing
    assert new_state.step == "planner"
    assert len(new_state.plan) == 1
    assert new_state.plan[0]["type"] == "add_event"
    assert new_state.plan[0]["params"]["name"] == "meeting"

@pytest.mark.asyncio
async def test_planner_list_events(base_state, mock_generate_completion):
    base_state.user_input = "What do I have this week?"
    base_state.intent = "list_events"
    
    mock_generate_completion.return_value = '{"plan": [{"type": "list_events", "params": {"start": "2026-01-27", "end": "2026-02-03"}}]}'
    
    new_state = await planner(base_state)
    assert new_state.plan[0]["type"] == "list_events"

@pytest.mark.asyncio
async def test_planner_error_passthrough(base_state):
    base_state.error = "Previous error"
    new_state = await planner(base_state)
    assert new_state.step == "error_handler"
    assert new_state.plan == []

@pytest.mark.asyncio
async def test_planner_llm_json_error(base_state, mock_generate_completion):
    base_state.intent = "add_task"
    # Return mangled JSON
    mock_generate_completion.return_value = 'This is not JSON'
    
    new_state = await planner(base_state)
    assert new_state.step == "planner" 
    assert new_state.plan == [] # Fallback to empty plan when parsing fails
