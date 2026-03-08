import pytest
from agentzero.supervisor import supervisor_node
from agentzero.agent_state import AgentState

@pytest.mark.asyncio
async def test_supervisor_node_routing(base_state, mock_chat_completion):
    base_state.user_input = "Schedule a meeting for tomorrow"
    
    # Mock LLM returning 'calendar' domain
    mock_chat_completion.return_value = '{"domain": "calendar"}'
    
    new_state = await supervisor_node(base_state)
    
    # Verify mock was called
    mock_chat_completion.assert_awaited()
    args, kwargs = mock_chat_completion.call_args
    prompt = kwargs['messages'][0]['content']
    
    # Check that system prompt is correct
    assert "Supervisor Router" in prompt
    
    # Verify proper domain selection
    assert new_state.step == "supervisor"
    assert new_state.intent == "calendar"

@pytest.mark.asyncio
async def test_supervisor_fallback_to_chat(base_state, mock_chat_completion):
    base_state.user_input = "Hello there!"
    
    # If LLM returns an invalid JSON or domain, it falls back to chat
    mock_chat_completion.return_value = '{"domain": "invalid_domain"}'
    
    new_state = await supervisor_node(base_state)
    assert new_state.intent == "chat"

@pytest.mark.asyncio
async def test_supervisor_error_passthrough(base_state):
    base_state.error = "Previous error"
    new_state = await supervisor_node(base_state)
    assert new_state.step == "error_handler"
    assert new_state.intent == ""
