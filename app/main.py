"""
app/main.py
-----------
API REST del sistema RAG personal del usuario.

Endpoints:
    GET  /health  — estado del sistema (sin auth)
    POST /ask     — recibe una pregunta y devuelve una respuesta (requiere API key)

Seguridad:
    Header requerido: X-API-Key: <valor de USER_RAG_API_KEY en .env>
    Filtros de input: longitud, repetición de chars/palabras, caracteres válidos

Uso:
    uvicorn app.main:app --host 0.0.0.0 --port 8000
"""

import os
import re
import secrets
from collections import Counter

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
# Cargamos una Key para que la API sea segura por defecto. Si no se setea, la API no funcionará (500 error) para evitar endpoints abiertos.

API_KEY        = os.getenv("USER_RAG_API_KEY", "")
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
# Limito el uso de los tokens por IP para evitar abusos. 20 requests por minuto.

limiter = Limiter(key_func=get_remote_address)

# ── Filtros de input ──────────────────────────────────────────────────────────
# Detectan inputs maliciosos o abusivos antes de llegar al pipeline RAG.
# Devuelven (es_valido, motivo) — motivo solo se usa para logs internos.

MAX_CHARS         = 200   # longitud máxima del input
MAX_CHAR_RATIO    = 0.40  # un caracter no puede superar el 40% del total
MAX_WORD_REPEAT   = 4     # una palabra no puede repetirse más de N veces
VALID_CHARS_REGEX = re.compile(r"^[a-zA-Z0-9_\s\.,;:¿?¡!áéíóúÁÉÍÓÚüÜñÑ'\"\-\(\)@#/]+$")

def _validar_input(texto: str) -> tuple[bool, str]:
    """
    Valida el input antes de procesarlo.
    Retorna (True, "") si es válido o (False, motivo) si no lo es.
    """
    # 1. Longitud máxima
    if len(texto) > MAX_CHARS:
        return False, f"input demasiado largo ({len(texto)} chars, máx {MAX_CHARS})"

    # 2. Repetición de caracteres — "aaaaaaaaaaa" o "!!!!!!!!!!"
    if texto:
        char_counts = Counter(texto.replace(" ", ""))
        total_chars = len(texto.replace(" ", ""))
        if total_chars > 5:  # mínimo para evitar falsos positivos con inputs muy cortos
            char_mas_comun, count = char_counts.most_common(1)[0]
            if count / total_chars > MAX_CHAR_RATIO:
                return False, f"repetición de caracter '{char_mas_comun}' ({count}/{total_chars})"

    # 3. Repetición de palabras — "ignora ignora ignora ignora"
    palabras = texto.lower().split()
    if palabras:
        palabra_counts = Counter(palabras)
        _, max_count = palabra_counts.most_common(1)[0]
        if max_count > MAX_WORD_REPEAT:
            return False, f"repetición de palabra (máx {max_count} veces)"

    # 4. Caracteres válidos — solo letras, números, puntuación básica
    if not VALID_CHARS_REGEX.match(texto):
        return False, "caracteres no permitidos en el input"

    return True, ""

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
# Defino modelos Pydantic para validar y documentar los datos de entrada/salida de los endpoints.

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
    Filtros: longitud máx 300 chars, sin repetición de chars/palabras, solo ASCII+español
    """
    pregunta = body.question.strip() if body.question else ""

    # Validación básica
    if not pregunta:
        raise HTTPException(status_code=400, detail="La pregunta no puede estar vacía")

    # Filtros de input
    es_valido, motivo = _validar_input(pregunta)
    if not es_valido:
        print(f"[input_filter] Bloqueado — {motivo}")
        return RespuestaResponse(
            answer  = "No entendí la pregunta. ¿Podés reformularla?",
            sources = [],
            blocked = True,
        )

    resultado = responder(pregunta)

    return RespuestaResponse(
        answer  = resultado["answer"],
        sources = resultado["sources"],
        blocked = resultado["blocked"],
    )