import pytest
from agentzero.graph import build_agentzero_graph
from agentzero.agent_state import AgentState

@pytest.fixture
def compiled_graph():
    return build_agentzero_graph().compile()

@pytest.mark.asyncio
async def test_full_pipeline_chat_intent(compiled_graph, mock_chat_completion):
    """
    Simulate a full run where the Supervisor routes to 'chat', 
    executor runs chat LLM, and response composer formats it.
    """
    # 1. Supervisor classifies intent as 'chat'
    # 2. Executor handles chat response
    mock_chat_completion.side_effect = [
        '{"domain": "chat"}',
        "How can I help you today?"
    ]
    
    state = AgentState(user_input="Hello!")
    
    result = await compiled_graph.ainvoke(state)
    
    assert result["intent"] == "chat"
    assert "chat" in result["tool_results"][0]
    assert result["response"] == "How can I help you today?"

@pytest.mark.asyncio
async def test_full_pipeline_action_intent(compiled_graph, mock_chat_completion):
    """
    Simulate an action pipeline: supervisor -> task_agent -> executor -> response composer.
    """
    mock_chat_completion.side_effect = [
        '{"domain": "task"}', # Supervisor routes to task_agent
        '{"plan": [{"type": "add_task", "params": {"task": "buy groceries"}}]}', # Task agent plan
        "I added 'buy groceries' to your tasks." # Response composer summary
    ]
    
    state = AgentState(user_input="Remind me to buy groceries")
    
    result = await compiled_graph.ainvoke(state)
    
    assert result["intent"] == "task"
    assert len(result["plan"]) == 1
    assert result["plan"][0]["type"] == "add_task"
    
    # Check that executor ran the task locally (returns success dictionary)
    has_action = any('action' in r and r['action'] == 'add_task' for r in result["tool_results"])
    assert has_action
    
    # Check final LLM composer output
    assert result["response"] == "I added 'buy groceries' to your tasks."

@pytest.mark.asyncio
async def test_full_pipeline_permission_denied(compiled_graph, mock_chat_completion):
    """
    If a sub-agent hallucinates an unconfigured action, 
    the executor should append an error and the composer should report it or retry.
    """
    mock_chat_completion.side_effect = [
        '{"domain": "task"}', 
        '{"plan": [{"type": "delete_database", "params": {}}]}', # Fails permission
        '{"plan": [{"type": "ask_user", "params": {"question": "I cannot do that."}}]}', # Retry plan
        "I cannot do that." # Final response output
    ]
    
    state = AgentState(user_input="Delete everything")
    
    result = await compiled_graph.ainvoke(state)
    
    assert result["retries"] == 0 # Reset to 0 after success
    assert result["response"] == "I cannot do that."
