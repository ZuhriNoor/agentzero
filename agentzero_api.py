"""
AgentZero API server scaffold (FastAPI).
Serves as a secure, local-first gateway for mobile/desktop clients.
Connects to the LangGraph agent system as a backend module.
"""
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

app = FastAPI(title="AgentZero API", description="Local-first agent API server.")

# Example: agent system interface (to be implemented)
def run_agent_pipeline(user_input: str) -> str:
    # Call LangGraph pipeline and return response
    # ...
    return "[Agent response here]"

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
