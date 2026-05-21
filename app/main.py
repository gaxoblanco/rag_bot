"""
app/main.py
-----------
API REST del sistema RAG personal de Gastón Blanco.

Endpoints:
    GET  /health  — estado del sistema (sin auth)
    POST /ask     — recibe una pregunta y devuelve una respuesta (requiere API key)

Seguridad:
    Header requerido: X-API-Key: <valor de GASTON_RAG_API_KEY en .env>

Uso:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import os
import secrets
from fastapi import FastAPI, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from starlette.requests import Request
from starlette.status import HTTP_401_UNAUTHORIZED
from dotenv import load_dotenv

from app.rag_chain import responder

load_dotenv()

# ── Seguridad — API Key ───────────────────────────────────────────────────────

API_KEY        = os.getenv("GASTON_RAG_API_KEY", "")
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

def verificar_api_key(key: str = Security(api_key_header)) -> str:
    """Valida el header X-API-Key con comparación segura (evita timing attacks)."""
    if not API_KEY:
        raise HTTPException(status_code=500, detail="API key no configurada en el servidor")
    if not key or not secrets.compare_digest(key, API_KEY):
        raise HTTPException(
            status_code=HTTP_401_UNAUTHORIZED,
            detail="API key inválida o ausente",
        )
    return key

# ── Rate limiter ──────────────────────────────────────────────────────────────

limiter = Limiter(key_func=get_remote_address)

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "Gastón RAG API",
    description = "Sistema RAG personal — responde preguntas sobre Gastón Blanco",
    version     = "1.0.0",
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

app.add_middleware(
    CORSMiddleware,
    allow_origins  = ["*"],
    allow_methods  = ["GET", "POST"],
    allow_headers  = ["*"],
)

# ── Modelos de request/response ───────────────────────────────────────────────

class PreguntaRequest(BaseModel):
    question: str

class RespuestaResponse(BaseModel):
    answer:  str
    sources: list[str]
    blocked: bool = False

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Verifica que la API está corriendo. Sin autenticación."""
    return {"status": "ok", "version": "1.0.0"}


@app.post("/ask", response_model=RespuestaResponse)
@limiter.limit("20/minute")
def ask(
    request: Request,
    body:    PreguntaRequest,
    _:       str = Security(verificar_api_key),
):
    """
    Recibe una pregunta y devuelve una respuesta generada por el pipeline RAG.

    Requiere header: X-API-Key: <token>
    Rate limit: 20 requests por minuto por IP
    """
    if not body.question or not body.question.strip():
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")

    resultado = responder(body.question.strip())

    return RespuestaResponse(
        answer  = resultado["answer"],
        sources = resultado["sources"],
        blocked = resultado["blocked"],
    )