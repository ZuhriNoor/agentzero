import pytest
import json
from agentzero.response_composer import response_composer

@pytest.mark.asyncio
async def test_response_composer_empty(base_state):
    """If there are no tool_results, response_composer should just return 'No result.'"""
    base_state.tool_results = []
    
    new_state = await response_composer(base_state)
    assert new_state.response == "No result."
    assert new_state.step == "response_composer"

@pytest.mark.asyncio
async def test_response_composer_chat_only(base_state):
    """If tool_results only contains a 'chat' key, it passes through untouched."""
    base_state.tool_results = [{"chat": "Hello from the LLM!"}]
    
    new_state = await response_composer(base_state)
    assert new_state.response == "Hello from the LLM!"

@pytest.mark.asyncio
async def test_response_composer_action_with_llm(base_state, mock_chat_completion):
    """If tool_results contains action results, it should ask the LLM to format them."""
    base_state.user_input = "add meeting tomorrow"
    base_state.tool_results = [{"action": "add_event", "result": "Success!"}]
    
    mock_chat_completion.return_value = "I have successfully added the meeting for you."
    
    new_state = await response_composer(base_state)
    
    # Check that LLM was called
    mock_chat_completion.assert_awaited()
    args, kwargs = mock_chat_completion.call_args
    messages = kwargs.get("messages", [])
    assert len(messages) == 2
    assert "add_event" in messages[1]["content"]
    
    # Check the result was stored
    assert new_state.response == "I have successfully added the meeting for you."

@pytest.mark.asyncio
async def test_response_composer_error_state(base_state):
    """If state.error is set, the composer should pass it through and route to error_handler."""
    base_state.error = "A fatal error occurred."
    
    new_state = await response_composer(base_state)
    assert new_state.response == "Error: A fatal error occurred."
    assert new_state.step == "error_handler"
