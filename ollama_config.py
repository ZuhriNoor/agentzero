import os
from dotenv import load_dotenv

load_dotenv()

OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3:8b-instruct-q4_K_M")
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", "http://localhost:11434/api/generate")
OLLAMA_EMBEDDINGS_API_URL = os.getenv("OLLAMA_EMBEDDINGS_API_URL", "http://localhost:11434/api/embeddings")
