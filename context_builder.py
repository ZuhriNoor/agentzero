"""
Example LangGraph node: Context Builder for AgentZero.
Builds context using RAG from local vector DB and structured memory.
Uses Ollama API for embedding if needed.
"""

from agent_state import AgentState
from memory import LongTermMemory, StructuredMemory

VECTOR_DB_PATH = 'data/vector_db'  # Example path
STRUCTURED_PATH = 'data/user_profile.json'

def context_builder(state: AgentState) -> AgentState:
    from memory import log_node
    log_node('context_builder:entry', state)
    if state.error:
        state.step = "error_handler"
        log_node('context_builder:error', state)
        return state
    # Retrieve relevant context from vector DB (RAG)
    ltm = LongTermMemory(VECTOR_DB_PATH)
    rag_results = ltm.query(state.user_input, top_k=3)

    # Load structured user data
    structured = StructuredMemory(STRUCTURED_PATH)
    user_profile = structured.load()

    # Compose context
    state.context = {
        "rag": rag_results,
        "user_profile": user_profile
    }
    state.step = "context_builder"
    log_node('context_builder:exit', state)
    return state
