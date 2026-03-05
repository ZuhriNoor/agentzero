import os
import logging
import requests
from dotenv import load_dotenv

logger = logging.getLogger("agentzero.llm")

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


def _cloudflare_request(url: str, payload: dict, timeout: int, max_retries: int = 2) -> dict:
    """Makes a Cloudflare API request with retry + exponential backoff."""
    import time
    last_error = None
    for attempt in range(max_retries + 1):
        try:
            response = requests.post(url, headers=_cloudflare_headers(), json=payload, timeout=timeout)
            response.raise_for_status()
            data = response.json()
            if data.get("success"):
                return data
            else:
                raise Exception(f"Cloudflare error: {data.get('errors')}")
        except Exception as e:
            last_error = e
            if attempt < max_retries:
                backoff = 2 ** attempt  # 1s, 2s
                logger.warning(f"Cloudflare attempt {attempt+1} failed: {e}. Retrying in {backoff}s...")
                time.sleep(backoff)
            else:
                logger.error(f"Cloudflare failed after {max_retries+1} attempts: {e}")
    raise last_error


def generate_completion(prompt: str, stream: bool = False, options: dict = None, timeout: int = 30) -> str:
    """Raw text completion (used by router, planner, composer)"""
    if LLM_PROVIDER == "cloudflare":
        payload = {
            "messages": [{"role": "user", "content": prompt}],
            "stream": stream
        }
        url = _cloudflare_url(CLOUDFLARE_TEXT_MODEL)
        data = _cloudflare_request(url, payload, timeout)
        return data["result"]["response"].strip()
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
            logger.error(f"Ollama generate error: {e}")
            raise


def chat_completion(messages: list, stream: bool = False, timeout: int = 30) -> str:
    """Chat-based completion with history (used by executor)"""
    if LLM_PROVIDER == "cloudflare":
        payload = {
            "messages": messages,
            "stream": stream
        }
        url = _cloudflare_url(CLOUDFLARE_TEXT_MODEL)
        data = _cloudflare_request(url, payload, timeout)
        return data["result"]["response"].strip()
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
            logger.error(f"Ollama chat error: {e}")
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
                logger.error(f"Cloudflare embedding error: {data.get('errors')}")
                return None
        except Exception as e:
            logger.error(f"Cloudflare embedding error: {e}")
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
            logger.error(f"Ollama embedding error: {e}")
            return None
