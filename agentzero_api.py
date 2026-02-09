"""
AgentZero API server scaffold (FastAPI).
Serves as a secure, local-first gateway for mobile/desktop clients.
Connects to the LangGraph agent system as a backend module.
"""
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
from graph import build_agentzero_graph

app = FastAPI(title="AgentZero API", description="Local-first agent API server.")

# Allow all origins for local development/mobile app testing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the agent graph
agent_app = build_agentzero_graph().compile()

def run_agent_pipeline(user_input: str) -> str:
    """
    Invokes the AgentZero LangGraph with the user's input.
    Returns the final response string.
    """
    try:
        initial_state = {"user_input": user_input}
        # invoke() runs the graph until END and returns the final state
        final_state = agent_app.invoke(initial_state)
        
        # Helper to extract response (handles both Pydantic object and dict)
        if isinstance(final_state, dict):
            return final_state.get("response", "[No response generated]")
        else:
            return getattr(final_state, "response", "[No response generated]")
    except Exception as e:
        return f"[Agent Execution Error: {str(e)}]"

class ChatRequest(BaseModel):
    message: str
    session_id: str = None  # Optional: for STM

class ChatResponse(BaseModel):
    response: str
    audit_id: str = None

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest):
    try:
        agent_response = run_agent_pipeline(req.message)
        return ChatResponse(response=agent_response)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
