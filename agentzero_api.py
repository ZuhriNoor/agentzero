"""
AgentZero API server scaffold (FastAPI).
Serves as a secure, local-first gateway for mobile/desktop clients.
Connects to the LangGraph agent system as a backend module.
"""
from fastapi import FastAPI, HTTPException, Request, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
import uvicorn
import os
import httpx
from dotenv import load_dotenv
from typing import Set
from graph import build_agentzero_graph

load_dotenv()

# WhatsApp Configuration
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

# Simple in-memory deduplication
processed_message_ids: Set[str] = set()

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

@app.get("/webhook")
async def verify_webhook(request: Request):
    """
    Verifies the webhook for WhatsApp Cloud API.
    """
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")

    if mode and token:
        if mode == "subscribe" and token == WHATSAPP_VERIFY_TOKEN:
            print("WEBHOOK_VERIFIED")
            return int(challenge)
        else:
            raise HTTPException(status_code=403, detail="Verification failed")
    else:
        raise HTTPException(status_code=400, detail="Missing parameters")

@app.post("/webhook")
async def webhook_handler(request: Request, background_tasks: BackgroundTasks):
    """
    Handles incoming messages from WhatsApp.
    Uses BackgroundTasks to prevent timeouts and deduplication to avoid retries.
    """
    try:
        data = await request.json()
        
        entry = data.get("entry", [])[0]
        changes = entry.get("changes", [])[0]
        value = changes.get("value", {})
        messages = value.get("messages", [])

        if messages:
            message = messages[0]
            message_id = message.get("id")
            from_number = message.get("from")
            msg_body = message.get("text", {}).get("body")
            
            # Deduplication Check
            if message_id in processed_message_ids:
                print(f"Duplicate message ignored: {message_id}")
                return {"status": "ok"}
            
            processed_message_ids.add(message_id)
            
            if from_number and msg_body:
                print(f"Received message from {from_number}: {msg_body}")
                # Offload processing to background task
                background_tasks.add_task(process_whatsapp_message, from_number, msg_body)
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}

async def process_whatsapp_message(from_number: str, msg_body: str):
    """
    Background task to run the agent and send the response.
    """
    try:
        # Run synchronous agent pipeline in a threadpool
        print(f"Processing message: {msg_body}")
        agent_response = await run_in_threadpool(run_agent_pipeline, msg_body)
        print(f"Agent response: {agent_response}")
        
        # Send response back to WhatsApp
        await send_whatsapp_message(from_number, agent_response)
    except Exception as e:
        print(f"Error in background processing: {e}")

async def send_whatsapp_message(to_number: str, message_text: str):
    """
    Sends a text message using WhatsApp Cloud API.
    """
    if not WHATSAPP_PHONE_NUMBER_ID or not WHATSAPP_ACCESS_TOKEN:
        print("WhatsApp credentials missing.")
        return

    url = f"https://graph.facebook.com/v19.0/{WHATSAPP_PHONE_NUMBER_ID}/messages"
    headers = {
        "Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }
    payload = {
        "messaging_product": "whatsapp",
        "to": to_number,
        "text": {"body": message_text},
    }
    
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(url, headers=headers, json=payload)
            response.raise_for_status()
            print(f"Message sent to {to_number}")
        except httpx.HTTPStatusError as e:
            print(f"Failed to send message: {e.response.text}")

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
