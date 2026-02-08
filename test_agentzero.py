"""
AgentZero test harness: Runs the full LangGraph pipeline with sample input.
"""
from agent_state import AgentState
from graph import build_agentzero_graph

def run_agentzero(user_input: str):
    graph = build_agentzero_graph()
    compiled_graph = graph.compile()
    state = AgentState(user_input=user_input)
    # Run the compiled graph
    result = compiled_graph.invoke(state)
    return result

if __name__ == "__main__":
    print("AgentZero Test Harness\n----------------------")
    while True:
        user_input = input("You: ")
        if user_input.lower() in ("exit", "quit"): break
        result = run_agentzero(user_input)
        print(f"Agent: {result['response']}")
        if result.get('error'):
            print(f"[Error] {result['error']}")
