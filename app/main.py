"""
app/main.py
-----------
API REST del sistema RAG personal de Gastón Blanco.

Endpoints:
    GET  /health  — estado del sistema
    POST /ask     — recibe una pregunta y devuelve una respuesta

Estado actual: esqueleto mínimo para que Docker arranque.
La lógica RAG se conecta en la Fase 5.
"""

from fastapi import FastAPI
from pydantic import BaseModel

# ── App ───────────────────────────────────────────────────────────────────────

app = FastAPI(
    title       = "Gastón RAG API",
    description = "Sistema RAG personal — responde preguntas sobre Gastón Blanco",
    version     = "0.1.0",
)

# ── Modelos de request/response ───────────────────────────────────────────────

class PreguntaRequest(BaseModel):
    question: str

class RespuestaResponse(BaseModel):
    answer:  str
    sources: list[str]

# ── Endpoints ─────────────────────────────────────────────────────────────────

@app.get("/health")
def health():
    """Verifica que la API está corriendo."""
    return {"status": "ok", "version": "0.1.0"}


@app.post("/ask", response_model=RespuestaResponse)
def ask(body: PreguntaRequest):
    """
    Recibe una pregunta y devuelve una respuesta.
    Por ahora devuelve un placeholder — la lógica RAG se conecta en Fase 5.
    """
    return RespuestaResponse(
        answer  = f"[Fase 5 pendiente] Pregunta recibida: '{body.question}'",
        sources = [],
    )
