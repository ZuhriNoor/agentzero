
import sys
from unittest.mock import MagicMock, patch

# Mock dependencies
sys.modules['agent_state'] = MagicMock()
sys.modules['memory'] = MagicMock()
sys.modules['llm_service'] = MagicMock()

# Define AgentState
class AgentState:
    def __init__(self, user_input, tool_results=None, response=None, error=None, step=None):
        self.user_input = user_input
        self.tool_results = tool_results or []
        self.response = response
        self.error = error
        self.step = step

# Import response_composer
import response_composer

def test_response_composer():
    print("Testing Response Composer...")
    
    # Mock data
    events = [
        {"name": "Meeting with Bob", "begin": "2026-02-15 10:00"},
        {"name": "Lunch", "begin": "2026-02-15 12:30"}
    ]
    state = AgentState(
        user_input="What do I have tomorrow?",
        tool_results=[{"tool": "list_events", "result": events}]
    )
    
    # Mock generate_completion to simulate LLM response
    with patch('response_composer.generate_completion', create=True) as mock_generate:
        mock_generate.return_value = "You have a meeting with Bob at 10 AM and Lunch at 12:30."
        
        # Run functionality
        response_composer.response_composer(state)
        
        # Verify
        print(f"\nUser Input: {state.user_input}")
        print(f"Generated Response: {state.response}")
        
        # Check if LLM was called with expected prompt
        if mock_generate.called:
            args, kwargs = mock_generate.call_args
            prompt = kwargs['prompt']
            print("\nPrompt Sent to LLM:")
            print(prompt)
            if "Meeting with Bob" in prompt and "Lunch" in prompt:
                 print("\nSUCCESS: Events included in prompt.")
            else:
                 print("\nFAILURE: Events missing from prompt.")
        else:
            print("\nFAILURE: LLM was not called.")

if __name__ == "__main__":
    test_response_composer()
