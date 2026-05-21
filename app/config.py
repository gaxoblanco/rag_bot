"""
app/config.py
-------------
Configuración centralizada del proyecto.
Todas las variables de entorno se leen desde aquí.
Ningún otro módulo llama a os.getenv() directamente.
"""

import os
from dotenv import load_dotenv
from pathlib import Path

# Carga .env desde la raíz del proyecto
load_dotenv(Path(__file__).parent.parent / ".env")

# ── Ollama ────────────────────────────────────────────────────────────────────
OLLAMA_HOST            = os.getenv("OLLAMA_HOST", "ollama")
OLLAMA_PORT            = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
MODEL_NAME             = os.getenv("MODEL_NAME", "phi3:mini")

OLLAMA_BASE_URL        = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# ── ChromaDB ──────────────────────────────────────────────────────────────────
CHROMA_HOST            = os.getenv("CHROMA_HOST", "chroma")
CHROMA_PORT            = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION      = "gaston_rag"

# ── GitHub ────────────────────────────────────────────────────────────────────
GITHUB_TOKEN           = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME        = os.getenv("GITHUB_USERNAME", "gaxoblanco")

# ── HuggingFace ───────────────────────────────────────────────────────────────
HF_TOKEN               = os.getenv("HF_TOKEN")
HF_USERNAME            = os.getenv("HF_USERNAME", "gaxoblanco")

# ── RAG — parámetros de retrieval ─────────────────────────────────────────────
# Ver docs/MODELO.md sección 3 para guía de ajuste
RETRIEVAL_K       = int(os.getenv("RETRIEVAL_K", "8"))       # chunks devueltos
RETRIEVAL_FETCH_K = int(os.getenv("RETRIEVAL_FETCH_K", "30")) # pool MMR antes de filtrar
RETRIEVAL_LAMBDA  = float(os.getenv("RETRIEVAL_LAMBDA", "0.6")) # 0=diversidad, 1=relevancia

# ── Provider de modelo ────────────────────────────────────────────────────────
# "ollama" | "huggingface"
MODEL_PROVIDER      = os.getenv("MODEL_PROVIDER", "ollama")

# ── HuggingFace Inference API ─────────────────────────────────────────────────
HF_INFERENCE_MODEL  = os.getenv("HF_INFERENCE_MODEL", "meta-llama/Llama-3.1-8B-Instruct")