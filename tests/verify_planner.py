
import sys
import os
import json
import datetime
from unittest.mock import MagicMock, patch

# --- MOCK DEPENDENCIES START ---

# Mock memory
mock_memory = MagicMock()
sys.modules['memory'] = mock_memory

# Mock llm_service
mock_llm_service = MagicMock()
sys.modules['llm_service'] = mock_llm_service

# Mock agent_state
mock_agent_state = MagicMock()
# Define a simple AgentState class for testing
class AgentState:
    def __init__(self, user_input, intent, context=None, plan=None, error=None, step=None):
        self.user_input = user_input
        self.intent = intent
        self.context = context or {}
        self.plan = plan or []
        self.error = error
        self.step = step
mock_agent_state.AgentState = AgentState
sys.modules['agent_state'] = mock_agent_state

# --- MOCK DEPENDENCIES END ---

# Now safe to import planner
import planner

def test_planner_prompt():
    print("Testing planner prompt construction...")
    
    # Patch requests.post where it is used in planner.py
    # Since we mocked ollama_config, planner imports are already done.
    # But requests is imported in planner.py
    
    with patch('planner.generate_completion', create=True) as mock_generate:
        # Mock response structure
        mock_generate.return_value = '{"plan": []}'

        # Test 1: Check Current Date/Time injection in Prompt
        print("\n[Test 1] Verifying Date/Time in Prompt...")
        state = AgentState(user_input="I have a meeting this Sunday", intent="add_event")
        planner.planner(state)
        
        if not mock_generate.called:
            print("FAILURE: generate_completion was not called.")
            return

        args, kwargs = mock_generate.call_args
        prompt = kwargs['prompt']
        
        now = datetime.datetime.now()
        expected_day = now.strftime('%A')     # e.g., Friday
        expected_date = now.strftime('%Y-%m-%d') # e.g., 2026-02-13
        
        # We also check for %H:%M roughly, but exact minute might flip, so just checking date/day is good enough
        
        print(f"Checking for day '{expected_day}'...")
        if expected_day in prompt:
            print(f"SUCCESS: Found day '{expected_day}'.")
        else:
            print(f"FAILURE: Day '{expected_day}' NOT found in prompt.")
            print("Prompt snippet:", prompt.split('\nExamples:')[0][-150:])
            
        print(f"Checking for date '{expected_date}'...")
        if expected_date in prompt:
            print(f"SUCCESS: Found date '{expected_date}'.")
        else:
            print(f"FAILURE: Date '{expected_date}' NOT found in prompt.")

        # Test 2: Check list_events intent
        print("\n[Test 2] Verifying list_events uses LLM...")
        # Reset mock
        mock_generate.reset_mock()
        
        state = AgentState(user_input="What do I have this week?", intent="list_events")
        planner.planner(state)
        
        if mock_generate.called:
             print("SUCCESS: list_events invoked LLM (generate_completion called).")
        else:
             print("FAILURE: list_events did NOT invoke LLM (regex shortcut still active?).")

if __name__ == "__main__":
    test_planner_prompt()
