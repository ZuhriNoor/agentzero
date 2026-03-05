import pytest
from agentzero.graph import build_agentzero_graph
from agentzero.agent_state import AgentState

@pytest.fixture
def compiled_graph():
    return build_agentzero_graph().compile()

@pytest.mark.asyncio
async def test_full_pipeline_chat_intent(compiled_graph, mock_generate_completion, mock_chat_completion):
    """
    Simulate a full run where the LLM routes to 'chat', planner skips it, 
    executor runs chat LLM, and response composer formats it.
    """
    # 1. Router classifies intent as 'chat'
    mock_generate_completion.return_value = "chat"
    # 2. Executor handles chat response
    mock_chat_completion.return_value = "How can I help you today?"
    
    state = AgentState(user_input="Hello!")
    
    # Run pipeline
    result = await compiled_graph.ainvoke(state)
    
    assert result["intent"] == "chat"
    assert "chat" in result["tool_results"][0]
    assert result["response"] == "How can I help you today?"

@pytest.mark.asyncio
async def test_full_pipeline_action_intent(compiled_graph, mock_generate_completion, mock_chat_completion):
    """
    Simulate an action pipeline: intent router -> planner -> executor -> response composer.
    """
    # 1. Router classifies as 'add_task'
    mock_generate_completion.side_effect = [
        "add_task", # First call to generate_completion via router
        '{"plan": [{"type": "add_task", "params": {"name": "buy groceries"}}]}' # Second call via planner
    ]
    
    # 3. Response composer summarizes result
    mock_chat_completion.return_value = "I added 'buy groceries' to your tasks."
    
    state = AgentState(user_input="Remind me to buy groceries", permissions={"add_task": True})
    
    result = await compiled_graph.ainvoke(state)
    
    assert result["intent"] == "add_task"
    assert len(result["plan"]) == 1
    assert result["plan"][0]["type"] == "add_task"
    
    # Check that executor ran the task locally (returns success dictionary)
    has_action = any('action' in r and r['action'] == 'add_task' for r in result["tool_results"])
    assert has_action
    
    # Check final LLM composer output
    assert result["response"] == "I added 'buy groceries' to your tasks."

@pytest.mark.asyncio
async def test_full_pipeline_permission_denied(compiled_graph, mock_generate_completion, mock_chat_completion):
    """
    If permission is denied for a specific action (e.g. LLM hallucinates an unconfigured action), 
    the executor should append an error and the composer should report it.
    """
    # 1. Router classifies intent as 'add_task' (allowed by policy_enforcer)
    # 2. Planner hallucinates an action that isn't pre-authorized
    mock_generate_completion.side_effect = [
        "add_task", 
        '{"plan": [{"type": "delete_database", "params": {}}]}'
    ]
    
    # Mock fallback formatting
    mock_chat_completion.return_value = "I cannot do that because I lack permission."
    
    state = AgentState(user_input="Delete everything")
    
    result = await compiled_graph.ainvoke(state)
    
    # The executor should have blocked 'delete_database'
    error_result = next(r for r in result["tool_results"] if "error" in r)
    assert "Permission denied for delete_database" in error_result["error"]
    assert result["response"] == "I cannot do that because I lack permission."
