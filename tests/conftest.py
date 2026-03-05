import pytest
from unittest.mock import AsyncMock

@pytest.fixture
def mock_generate_completion(mocker):
    """Mocks generate_completion to return a controlled string."""
    mock = AsyncMock()
    mocker.patch("agentzero.intent_router.generate_completion", mock)
    mocker.patch("agentzero.planner.generate_completion", mock)
    return mock

@pytest.fixture
def mock_chat_completion(mocker):
    """Mocks chat_completion to return a controlled string."""
    mock = AsyncMock()
    mocker.patch("agentzero.executor.chat_completion", mock)
    mocker.patch("agentzero.response_composer.chat_completion", mock)
    mocker.patch("agentzero.actions.planning_actions.chat_completion", mock)
    return mock

@pytest.fixture
def base_state():
    from agentzero.agent_state import AgentState
    return AgentState(
        user_input="",
        intent="",
        chat_history=[],
        context={},
        plan=[],
        tool_results=[],
        response="",
        error=None,
        step=""
    )
