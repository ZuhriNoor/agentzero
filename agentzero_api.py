
# AgentZero API server scaffold (FastAPI).
# Serves as a secure, local-first gateway for mobile/desktop clients.
# Connects to the LangGraph agent system as a backend module.


from fastapi import FastAPI, HTTPException, Request, BackgroundTasks, WebSocket, WebSocketDisconnect, UploadFile, File, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel
from auth import (
    LoginRequest, TokenResponse, authenticate_user,
    create_access_token, require_auth, validate_ws_token,
    hash_password,
)
import uvicorn
import os
import httpx
from dotenv import load_dotenv
from typing import Set, List, Dict
from graph import build_agentzero_graph
from scheduler import Scheduler
import asyncio
import shutil
import uuid
# Import Whisper
try:
    from faster_whisper import WhisperModel
except ImportError:
    print("Warning: faster-whisper not installed. Voice features will fail.")
    WhisperModel = None

load_dotenv()

# WhatsApp Configuration
WHATSAPP_PHONE_NUMBER_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID")
WHATSAPP_ACCESS_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN")
WHATSAPP_VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN")

# Simple in-memory deduplication
processed_message_ids: Set[str] = set()

# Short-term memory (STM) for conversational chat mapped by session_id
session_memory: Dict[str, List[Dict[str, str]]] = {}

# WebSocket Connection Manager
# This list tracks active connections from your separate app (e.g., React Native, Flutter, Web App)
# When a notification needs to be sent, we will broadcast it to all these clients.
connected_clients: List[WebSocket] = []

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

# GLOBAL STATE
scheduler = None
last_active_user_phone = None  # To track who to message on WhatsApp
whisper_model = None

# ==========================================
# AUTHENTICATION
# ==========================================

@app.post("/auth/login", response_model=TokenResponse)
async def login(req: LoginRequest):
    if not authenticate_user(req.username, req.password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token(subject=req.username)
    return TokenResponse(
        access_token=token,
        expires_in=24 * 3600  # matches JWT_EXPIRY_HOURS default
    )

@app.get("/auth/hash-password")
async def get_password_hash(password: str = Query(...)):
    """
    Utility endpoint to generate a bcrypt hash for a password.
    Use this ONCE to generate ADMIN_PASSWORD_HASH for your .env, then remove or disable.
    """
    return {"hash": hash_password(password)}

@app.on_event("startup")
async def startup_event():
    """
    Start the background scheduler on API startup.
    Initialize Whisper model.
    """
    global scheduler, whisper_model
    scheduler = Scheduler(broadcast_func=broadcast_notification)
    # Give 30 seconds for WebSocket clients to connect before checking reminders
    asyncio.create_task(scheduler.start(initial_delay=30))
    
    # Initialize Whisper (Tiny model for speed, CPU int8 for compatibility)
    if WhisperModel:
        print("Loading Whisper Model (tiny)...")
        try:
            # Models: tiny, base, small, medium, large-v3
            # 'small' is a good balance for CPU. 'medium' is better but slower.
            # compute_type="int8" is faster on CPU
            whisper_model = WhisperModel("base", device="cpu", compute_type="int8") 
            print("Whisper Model Loaded.")
        except Exception as e:
            print(f"Failed to load Whisper: {e}")

@app.on_event("shutdown")
def shutdown_event():
    if scheduler:
        scheduler.stop()

# Helper for WhatsApp Media
async def download_whatsapp_media(media_id: str) -> str:
    """
    Downloads media from WhatsApp API and saves to a temp file.
    Returns path to the file.
    """
    if not WHATSAPP_ACCESS_TOKEN:
        raise Exception("Missing WhatsApp Access Token")
        
    async with httpx.AsyncClient() as client:
        # 1. Get Media URL
        url_resp = await client.get(
            f"https://graph.facebook.com/v17.0/{media_id}",
            headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
        )
        url_resp.raise_for_status()
        media_url = url_resp.json().get("url")
        
        # 2. Download Binary
        media_resp = await client.get(
            media_url,
            headers={"Authorization": f"Bearer {WHATSAPP_ACCESS_TOKEN}"}
        )
        media_resp.raise_for_status()
        
        # 3. Save to file
        filename = f"temp_wa_{uuid.uuid4()}.ogg" # WhatsApp usually sends OGG
        with open(filename, "wb") as f:
            f.write(media_resp.content)
            
        return filename

@app.post("/voice")
async def voice_endpoint(file: UploadFile = File(...), _user: str = Depends(require_auth)):
    """
    Accepts an audio file, transcribes it, and executes the command.
    """
    if not whisper_model:
        raise HTTPException(status_code=500, detail="Whisper model not loaded.")
    
    # Save temp file
    temp_filename = f"temp_{uuid.uuid4()}_{file.filename}"
    with open(temp_filename, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        
    try:
        # Transcribe
        # beam_size=5 is standard.
        segments, info = await run_in_threadpool(whisper_model.transcribe, temp_filename, beam_size=5)
        text = "".join([s.text for s in segments]).strip()
        print(f"[Voice] Transcribed: {text}")
        
        if not text:
             return {"response": "I couldn't hear anything.", "transcription": ""}

        # Execute Agent
        agent_response = run_agent_pipeline(text)
        return {"response": agent_response, "transcription": text}
        
    except Exception as e:
        print(f"Voice Error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
        
    finally:
        # Cleanup
        if os.path.exists(temp_filename):
            os.remove(temp_filename)

# ==========================================
# NOTIFICATION SYSTEM (Multi-Channel)
# ==========================================
# This function sends notifications to ALL configured channels:
# 1. WhatsApp (if a user has recently interacted via WhatsApp)
# 2. WebSocket Clients (your separate app)
# ==========================================
async def broadcast_notification(message: str):
    print(f"[BROADCAST] Notification: {message}")
    
    # Channel 1: WebSocket Broadcast (Your App)
    for client in connected_clients:
        try:
            await client.send_text(message)
        except Exception as e:
            print(f"Error sending to WebSocket client: {e}")
            
    # Channel 2: WhatsApp (Push Notification)
    if last_active_user_phone:
        await send_whatsapp_message(last_active_user_phone, message)
    else:
        print("No active WhatsApp user to notify.")

from fastapi import WebSocket, WebSocketDisconnect
import traceback

# Make sure these are imported!
connected_clients = [] 

@app.websocket("/ws/notifications")
async def websocket_endpoint(websocket: WebSocket, token: str = Query(None)):
    # Validate JWT token for WebSocket connections
    if not token or not validate_ws_token(token):
        await websocket.close(code=4001, reason="Unauthorized")
        print("WebSocket rejected: invalid or missing token.")
        return

    print("Attempting to connect...")
    await websocket.accept()
    # 1. Send a "Welcome" message to turn the App Light GREEN
    await websocket.send_text("Connected via WebSocket") 
    print("Connection accepted!")
    
    connected_clients.append(websocket)
    print(f"Client added. Total clients: {len(connected_clients)}")

    try:
        # Create a heartbeat task to keep connection alive through Cloudflare
        async def heartbeat(ws):
            while True:
                await asyncio.sleep(15) # Send ping every 15 seconds
                try:
                    await ws.send_text("ping")
                except:
                    break

        # Run both the receiver (to detect disconnects) and heartbeat
        heartbeat_task = asyncio.create_task(heartbeat(websocket))
        
        while True:
            # We just listen. If client disconnects, receive_text raises generic Exception or WebSocketDisconnect
            data = await websocket.receive_text()
            print(f"Received: {data}")
            
    except WebSocketDisconnect:
        print("Client disconnected normally.")
    except Exception as e:
        print(f"WebSocket Error: {e}")
        # traceback.print_exc()
    finally:
        if 'heartbeat_task' in locals():
            heartbeat_task.cancel()
        if websocket in connected_clients:
            connected_clients.remove(websocket)
        print("Client removed.")

def run_agent_pipeline(user_input: str, session_id: str = "default") -> str:
    """
    Invokes the AgentZero LangGraph with the user's input.
    Maintains a sliding window of the last 5 chat interactions.
    Returns the final response string.
    """
    try:
        # Retrieve history for this session
        history = session_memory.get(session_id, [])
        
        initial_state = {"user_input": user_input, "chat_history": history}
        # invoke() runs the graph until END and returns the final state
        final_state = agent_app.invoke(initial_state)
        
        # Helper to extract response (handles both Pydantic object and dict)
        if isinstance(final_state, dict):
            agent_response = final_state.get("response", "[No response generated]")
        else:
            agent_response = getattr(final_state, "response", "[No response generated]")
            
        # Update session memory (keep last 5 interactions = 10 messages)
        history.append({"role": "user", "content": user_input})
        history.append({"role": "assistant", "content": agent_response})
        
        if len(history) > 10:
            history = history[-10:]
            
        session_memory[session_id] = history
        
        return agent_response
    except Exception as e:
        return f"[Agent Execution Error: {str(e)}]"

class ChatRequest(BaseModel):
    message: str
    session_id: str = None  # Optional: for STM

class ChatResponse(BaseModel):
    response: str
    audit_id: str = None

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(req: ChatRequest, _user: str = Depends(require_auth)):
    try:
        agent_response = run_agent_pipeline(req.message, req.session_id or "default")
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
    global last_active_user_phone
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
            
            # Update last active user for push notifications
            if from_number:
                last_active_user_phone = from_number
            
            # Deduplication Check
            if message_id in processed_message_ids:
                print(f"Duplicate message ignored: {message_id}")
                return {"status": "ok"}
            
            processed_message_ids.add(message_id)
            
            if from_number:
                print(f"Received message from {from_number} (Type: {message.get('type')})")
                # Offload processing to background task
                background_tasks.add_task(process_whatsapp_message, from_number, message)
        
        return {"status": "ok"}
    except Exception as e:
        print(f"Error processing webhook: {e}")
        return {"status": "error", "message": str(e)}


async def process_whatsapp_message(from_number: str, message: dict):
    """
    Background task to run the agent and send the response.
    """
    try:
        # 3. Process the Message
        if message.get("type") == "text":
            user_text = message["text"]["body"]  # Extract the text
            print(f"Received WhatsApp message from {from_number}: {user_text}")

            # Run the Agent!
            agent_response = await run_in_threadpool(run_agent_pipeline, user_text, from_number)

            # Send response back to WhatsApp
            await send_whatsapp_message(from_number, agent_response)
            
        elif message.get("type") == "audio":
            media_id = message["audio"]["id"]
            print(f"Received WhatsApp AUDIO from {from_number}. Downloading...")
            
            try:
                if not whisper_model:
                    await send_whatsapp_message(from_number, "Voice features are not active on the server.")
                    return # {"status": "error", "detail": "Whisper not loaded"} # This is a background task, no return value needed

                # 1. Download
                audio_path = await download_whatsapp_media(media_id)
                
                # 2. Transcribe
                segments, info = await run_in_threadpool(whisper_model.transcribe, audio_path, beam_size=5)
                transcribed_text = "".join([s.text for s in segments]).strip()
                print(f"[WhatsApp Voice] Transcribed: {transcribed_text}")
                
                if not transcribed_text:
                    await send_whatsapp_message(from_number, "I couldn't hear anything in that voice note.")
                else:
                    # 3. Run Agent with transcribed text
                    # Optional: specific prefix to let agent know it was voice? Nah.
                    agent_response = await run_in_threadpool(run_agent_pipeline, transcribed_text, from_number)
                    await send_whatsapp_message(from_number, agent_response)
                    
                # Cleanup
                if os.path.exists(audio_path):
                    os.remove(audio_path)
                    
            except Exception as e:
                print(f"Error processing WhatsApp audio: {e}")
                await send_whatsapp_message(from_number, "Sorry, I had trouble understanding that voice note.")
                
        else:
            print(f"Received non-text/audio message type: {message.get('type')}")
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
