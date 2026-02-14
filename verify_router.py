
import sys
from unittest.mock import MagicMock, patch

# Mock dependencies
sys.modules['agent_state'] = MagicMock()
sys.modules['ollama_config'] = MagicMock()
sys.modules['memory'] = MagicMock()

# Mock env vars in ollama_config
sys.modules['ollama_config'].OLLAMA_MODEL = "mock-model"
sys.modules['ollama_config'].OLLAMA_API_URL = "http://mock-url"

import intent_router

def test_router():
    print("Testing Intent Router...")
    
    test_cases = [
        "Do I have anything planned for this month?",
        "I have a meeting tomorrow at 5 PM",
        "Hello there"
    ]
    
    for text in test_cases:
        print(f"\nInput: '{text}'")
        speech_act = intent_router.classify_speech_act(text)
        print(f"Speech Act: {speech_act}")
        
        # We can't easily run the LLM part without a real LLM or complex mocking of the response
        # But we can verify the prompt it generates
        prompt = intent_router.build_prompt(text, speech_act)
        print("Prompt excerpt:")
        print(prompt.split("\n\n")[-2:]) # Show last part

if __name__ == "__main__":
    test_router()
