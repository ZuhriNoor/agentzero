# AgentZero

A local-first, privacy-preserving AI agent system built with [FastAPI](https://fastapi.tiangolo.com/) and [LangGraph](https://github.com/langchain-ai/langgraph).

AgentZero runs entirely on your own hardware. No data leaves your device — all LLM inference, memory, and task scheduling happen locally.

## Features

- **Local-first AI** — Works with [Ollama](https://ollama.com/) for fully offline LLM inference, or optionally with Cloudflare Workers AI.
- **Multi-agent graph** — Supervisor, policy enforcer, calendar, task, and knowledge agents orchestrated via LangGraph.
- **Persistent memory** — Vector-based memory with [ChromaDB](https://www.trychroma.com/) and SQLite session store.
- **Task scheduler** — Background agent for recurring and time-based tasks.
- **Voice input** — Speech-to-text via [faster-whisper](https://github.com/SYSTRAN/faster-whisper).
- **WhatsApp integration** — Receive and respond to WhatsApp messages via the Cloud API.
- **JWT authentication** — Secure REST and WebSocket endpoints.
- **Encryption at rest** — Optional Fernet/AES encryption for all stored data.
- **Docker support** — Single-command deployment with Docker Compose.

## Requirements

- Python 3.9+
- [Ollama](https://ollama.com/) (for local LLM inference) **or** Cloudflare Workers AI credentials
- [ffmpeg](https://ffmpeg.org/) (required for voice features)

## Quick Start

### 1. Clone and install

```bash
git clone https://github.com/ZuhriNoor/agentzero.git
cd agentzero
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
# Edit .env with your settings
```

Key variables in `.env`:

| Variable | Description |
|---|---|
| `LLM_PROVIDER` | `ollama` (local) or `cloudflare` |
| `OLLAMA_MODEL` | Ollama model name, e.g. `mistral-nemo:12b` |
| `JWT_SECRET_KEY` | Random secret for JWT signing |
| `ADMIN_USERNAME` | Admin login username |
| `ADMIN_PASSWORD_HASH` | bcrypt hash of the admin password |
| `ENCRYPTION_KEY` | Fernet key for data encryption at rest (optional) |

Generate a JWT secret:
```bash
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

Generate a password hash (start the server first):
```bash
curl http://localhost:8000/auth/hash-password?******
```

### 3. Run

```bash
PYTHONPATH=src uvicorn agentzero_api:app --host 0.0.0.0 --port 8000
```

The API will be available at `http://localhost:8000`.

## Docker

```bash
cp .env.example .env
# Edit .env with your settings
docker compose up --build
```

The API is exposed on port `8000`.

## API

See [`openapi.yaml`](openapi.yaml) for the full OpenAPI spec.

| Endpoint | Method | Description |
|---|---|---|
| `/auth/login` | POST | Obtain a JWT token |
| `/chat` | POST | Send a message to the agent |
| `/chat/stream` | WebSocket | Stream agent responses |
| `/voice` | POST | Send audio for transcription and agent response |
| `/tasks` | GET/POST | List and create scheduled tasks |
| `/health` | GET | Health check |

## Project Structure

```
agentzero_api.py        # FastAPI application entry point
src/agentzero/
  graph.py              # LangGraph agent graph definition
  supervisor.py         # Supervisor agent node
  agents/               # Specialized agents (calendar, task, knowledge)
  actions/              # Action handlers (calendar, filesystem, tasks, memory, …)
  skills/               # Reusable skill modules
  memory/               # Memory read/write logic
  scheduler.py          # Background task scheduler
  session_store.py      # SQLite session persistence
  auth.py               # JWT authentication
  encryption.py         # Fernet encryption at rest
  policy_enforcer.py    # Request policy checks
  llm_service.py        # LLM provider abstraction (Ollama / Cloudflare)
```

## Scaling

See [`SCALING.md`](SCALING.md) for notes on multi-agent deployments, local IPC, and zero-knowledge sync.

## License

This project does not currently include a license file. All rights reserved by the author.
