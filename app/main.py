"""
app/main.py
-----------
API REST del sistema RAG personal del usuario.

Endpoints:
    GET  /         — dashboard público (sin auth, Jinja2 template)
    GET  /health   — estado del sistema (sin auth)
    POST /ask      — recibe una pregunta (requiere API key)
    POST /playground — playground público (sin auth, rate limit 5/día por IP)

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

import json
from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Security
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.security import APIKeyHeader
from fastapi.templating import Jinja2Templates
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

# ── Templates y datos del dashboard ──────────────────────────────────────────
# Jinja2 sirve el dashboard HTML. eval_results.json se carga una vez al iniciar.

_TEMPLATES_DIR = Path(__file__).parent / "templates"
templates      = Jinja2Templates(directory=str(_TEMPLATES_DIR))

_EVAL_FILE = Path(__file__).parent.parent / "data" / "eval_results.json"

def _cargar_eval() -> dict:
    """Carga los resultados de evaluación RAGAS desde el JSON cacheado."""
    try:
        with open(_EVAL_FILE, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}

app.state.limiter = limiter

def _playground_rate_limit_handler(request: Request, exc):
    """
    Handler personalizado para rate limit del playground.
    Devuelve HTML amable en lugar del JSON generico de slowapi.
    """
    if request.url.path == "/playground":
        return HTMLResponse(
            content="""
<div class="result-item" style="border-color: rgba(252,211,77,0.3)">
  <div class="result-header">
    <span class="result-q">límite diario alcanzado</span>
    <span class="badge badge-blocked">429</span>
  </div>
  <div class="result-body">
    <div class="result-answer" style="border-left-color: rgba(252,211,77,0.4)">
      Usaste las 5 preguntas disponibles por hoy. El límite existe para mantener
      el sistema gratuito y accesible para todos los visitantes.
      <br><br>
      Si querés saber más sobre el sistema o sobre mi perfil,
      <a href="https://gaxoblanco.com/#contact" style="color:var(--accent-green)">
        contactame directamente por WhatsApp
      </a>.
    </div>
  </div>
</div>""",
            status_code=200,  # HTMX necesita 200 para insertar el HTML
        )
    return _rate_limit_exceeded_handler(request, exc)

app.add_exception_handler(RateLimitExceeded, _playground_rate_limit_handler)

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


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    """
    Dashboard público del sistema RAG.
    Sirve el panel de control con métricas, arquitectura y playground.
    Sin autenticación — público.
    """
    eval_data = _cargar_eval()
    return templates.TemplateResponse("dashboard.html", {
        "request":   request,
        "eval_data": eval_data,
    })


@app.post("/playground", response_class=HTMLResponse)
@limiter.limit("5/day")
def playground(
    request:  Request,
    question: str = Form(...),
):
    """
    Endpoint público del playground del dashboard.
    Recibe una pregunta via form, llama a responder(), devuelve fragmento HTML.

    Sin API key — público.
    Rate limit: 5 requests por día por IP.
    Sin historial conversacional — cada pregunta es independiente.
    Sin contextos expuestos — los chunks no llegan al browser.
    """
    pregunta = question.strip() if question else ""

    if not pregunta:
        return HTMLResponse(_resultado_html(
            pregunta="(pregunta vacía)",
            answer="La pregunta no puede estar vacía.",
            sources=[],
            blocked=True,
        ))

    es_valido, motivo = _validar_input(pregunta)
    if not es_valido:
        print(f"[playground] Bloqueado — {motivo}")
        return HTMLResponse(_resultado_html(
            pregunta=pregunta,
            answer="No entendí la pregunta. ¿Podés reformularla?",
            sources=[],
            blocked=True,
        ))

    from app.rag_chain import limpiar_historial
    limpiar_historial()

    resultado = responder(pregunta, include_contexts=True, include_trace=True)

    return HTMLResponse(_resultado_html(
        pregunta=pregunta,
        answer=resultado["answer"],
        sources=resultado["sources"],
        blocked=resultado["blocked"],
        contexts=resultado.get("contexts", []),
        trace=resultado.get("trace", {}),
    ))


def _resultado_html(pregunta: str, answer: str, sources: list, blocked: bool, contexts: list = [], trace: dict = {}) -> str:
    """
    Genera el fragmento HTML que HTMX inserta en #results.
    Diseño consistente con el dashboard.
    """
    badge = (
        '<span class="badge badge-blocked">bloqueado</span>'
        if blocked else
        '<span class="badge badge-ok">ok</span>'
    )
    def _esc(t: str) -> str:
        return t.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")

    source_tags = "".join(
        f'<span class="source-tag">{_esc(s)}</span>' for s in sources
    ) or '<span class="source-tag">—</span>'

    # Timeline del pipeline
    def _check(v): return "✓" if v else "✗"
    def _col(v): return "trace-ok" if v else "trace-fail"

    timeline_html = ""
    if trace and not blocked:
        intent       = trace.get("intent", "—")
        fuentes      = " · ".join(trace.get("fuentes_activadas", [])) or "ninguna"
        g_entrada    = trace.get("guardia_entrada", True)
        g_relevancia = trace.get("guardia_relevancia", True)
        g_salida     = trace.get("guardia_salida", True)
        chunks_n     = trace.get("chunks_count", 0)
        chunks_f     = trace.get("chunks_por_fuente", {})
        proyecto     = trace.get("proyecto_activo") or "—"
        historial_n  = trace.get("historial_turnos", 0)

        chunks_detalle = " · ".join(
            f"{f} ×{n}" for f, n in sorted(chunks_f.items(), key=lambda x: -x[1])
        ) or "—"

        bloqueado_en = trace.get("bloqueado_en")
        timeline_html = f"""<div class="trace-timeline">
  <div class="trace-step">
    <span class="trace-label">intent</span>
    <span class="trace-value">{intent}</span>
  </div>
  <div class="trace-step">
    <span class="trace-label">fuentes activadas</span>
    <span class="trace-value">{fuentes}</span>
  </div>
  <div class="trace-step {_col(g_entrada)}">
    <span class="trace-label">guardia entrada</span>
    <span class="trace-value">{_check(g_entrada)} {'pasó' if g_entrada else 'bloqueó'}</span>
  </div>
  <div class="trace-step {_col(g_relevancia)}">
    <span class="trace-label">guardia relevancia</span>
    <span class="trace-value">{_check(g_relevancia)} {'pasó' if g_relevancia else 'bloqueó'}</span>
  </div>
  <div class="trace-step">
    <span class="trace-label">chunks recuperados</span>
    <span class="trace-value">{chunks_n} — {chunks_detalle}</span>
  </div>
  <div class="trace-step">
    <span class="trace-label">proyecto activo</span>
    <span class="trace-value">{proyecto}</span>
  </div>
  <div class="trace-step">
    <span class="trace-label">historial</span>
    <span class="trace-value">{historial_n} turnos previos</span>
  </div>
  <div class="trace-step {_col(g_salida)}">
    <span class="trace-label">guardia salida</span>
    <span class="trace-value">{_check(g_salida)} {'pasó' if g_salida else 'bloqueó'}</span>
  </div>
</div>"""

    chunk_preview = ""
    if contexts and not blocked:
        primer_chunk = _esc(contexts[0][:200].strip())
        chunk_preview = f"""  <details class="chunk-preview">
    <summary>ver chunk recuperado</summary>
    <div class="chunk-content">{primer_chunk}…</div>
  </details>"""

    return f"""
<div class="result-item">
  <div class="result-header">
    <span class="result-q">{_esc(pregunta)}</span>
    {badge}
  </div>
  <div class="result-body">
    <div class="result-answer">{_esc(answer)}</div>
    <div class="result-sources">
      <i class="ti ti-database" style="font-size:14px" aria-hidden="true"></i>
      {source_tags}
    </div>
    {chunk_preview}
  </div>
</div>
"""


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