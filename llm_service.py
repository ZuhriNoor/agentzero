import os
import requests
from dotenv import load_dotenv

load_dotenv()

LLM_PROVIDER = os.getenv("LLM_PROVIDER", "ollama").lower()

# Ollama Config
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4_K_M")
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_CHAT_URL = OLLAMA_API_URL.replace("/api/generate", "/api/chat")
OLLAMA_EMBEDDINGS_API_URL = os.getenv("OLLAMA_EMBEDDINGS_API_URL", "http://localhost:11434/api/embeddings")

# Cloudflare Config
CLOUDFLARE_ACCOUNT_ID = os.getenv("CLOUDFLARE_ACCOUNT_ID")
CLOUDFLARE_API_TOKEN = os.getenv("CLOUDFLARE_API_TOKEN")
CLOUDFLARE_TEXT_MODEL = os.getenv("CLOUDFLARE_TEXT_MODEL", "@cf/meta/llama-3.1-8b-instruct")
CLOUDFLARE_EMBEDDING_MODEL = os.getenv("CLOUDFLARE_EMBEDDING_MODEL", "@cf/baai/bge-base-en-v1.5")


def _cloudflare_headers():
    return {
        "Authorization": f"Bearer {CLOUDFLARE_API_TOKEN}",
        "Content-Type": "application/json"
    }


def _cloudflare_url(model: str) -> str:
    return f"https://api.cloudflare.com/client/v4/accounts/{CLOUDFLARE_ACCOUNT_ID}/ai/run/{model}"


def generate_completion(prompt: str, stream: bool = False, options: dict = None, timeout: int = 120) -> str:
    """Raw text completion (used by router, planner, composer)"""
    if LLM_PROVIDER == "cloudflare":
        # Cloudflare uses a messages array even for raw generation on instruct models, 
        # but supports raw prompt for text generation models. We'll wrap prompt in a user message.
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream
        }
        # Add temperature etc if needed, CF names them similarly but not identically to Ollama
        
        url = _cloudflare_url(CLOUDFLARE_TEXT_MODEL)
        try:
            response = requests.post(url, headers=_cloudflare_headers(), json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                return data["result"]["response"].strip()
            else:
                raise Exception(f"Cloudflare error: {data.get('errors')}")
        except Exception as e:
            print(f"[LLM Service Error] Cloudflare generate: {e}")
            raise
    else:
        # Default: Ollama
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": prompt,
            "stream": stream
        }
        if options:
            payload["options"] = options
            
        try:
            response = requests.post(OLLAMA_API_URL, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            print(f"[LLM Service Error] Ollama generate: {e}")
            raise


def chat_completion(messages: list, stream: bool = False, timeout: int = 120) -> str:
    """Chat-based completion with history (used by executor)"""
    if LLM_PROVIDER == "cloudflare":
        payload = {
            "messages": messages,
            "stream": stream
        }
        url = _cloudflare_url(CLOUDFLARE_TEXT_MODEL)
        try:
            response = requests.post(url, headers=_cloudflare_headers(), json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                return data["result"]["response"].strip()
            else:
                raise Exception(f"Cloudflare error: {data.get('errors')}")
        except Exception as e:
            print(f"[LLM Service Error] Cloudflare chat: {e}")
            raise
    else:
        # Default: Ollama
        payload = {
            "model": OLLAMA_MODEL,
            "messages": messages,
            "stream": stream
        }
        try:
            response = requests.post(OLLAMA_CHAT_URL, json=payload, timeout=timeout)
            response.raise_for_status()
            return response.json().get("message", {}).get("content", "[No response]").strip()
        except Exception as e:
            print(f"[LLM Service Error] Ollama chat: {e}")
            return f"[Chat error: {str(e)}]"


def get_embedding(text: str) -> list:
    """Text embedding (used by context_builder)"""
    if LLM_PROVIDER == "cloudflare":
        payload = {
            "text": [text]
        }
        url = _cloudflare_url(CLOUDFLARE_EMBEDDING_MODEL)
        try:
            response = requests.post(url, headers=_cloudflare_headers(), json=payload, timeout=10)
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                return data["result"]["data"][0]
            else:
                print(f"Cloudflare embedding error: {data.get('errors')}")
                return None
        except Exception as e:
            print(f"[LLM Service Error] Cloudflare embedding: {e}")
            return None
    else:
        # Default: Ollama
        payload = {
            "model": OLLAMA_MODEL,
            "prompt": text
        }
        try:
            response = requests.post(OLLAMA_EMBEDDINGS_API_URL, json=payload, timeout=10)
            response.raise_for_status()
            return response.json().get("embedding")
        except Exception as e:
            print(f"[LLM Service Error] Ollama embedding: {e}")
            return None
