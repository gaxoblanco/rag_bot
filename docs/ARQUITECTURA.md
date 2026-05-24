# RAG Personal — Arquitectura
## Gastón Blanco · gaston_rag

> **Documento vivo.** Se actualiza durante el desarrollo.
> Última actualización: Fase 7 + dashboard + tests — Mayo 2026

---

## Índice

1. [Visión general](#1-vision-general)
2. [Responsabilidad de cada archivo](#2-responsabilidad-de-cada-archivo)
3. [Stack tecnológico](#3-stack-tecnologico)
4. [Modelo](#4-modelo)
5. [Fuentes de datos](#5-fuentes-de-datos)
6. [Seguridad](#6-seguridad)
7. [Infraestructura y deploy](#7-infraestructura-y-deploy)
8. [Tests](#8-tests)
9. [Dashboard](#9-dashboard)
10. [Puntos de extensión futura](#10-puntos-de-extension-futura)
11. [Historial de decisiones](#11-historial-de-decisiones)

---

## 1. Visión general

Sistema RAG que responde preguntas sobre el perfil profesional de Gastón Blanco.
Objetivo: captar clientes y recruiters desde la landing page personal.

**Flujo de una query:**
```
Pregunta
   │
   ├── Detección de saludo → limpiar historial
   ├── Detección de contacto puro → respuesta directa con CTA
   ├── Detección de intent visitante → recruiter | cliente | neutro
   │
   ▼
Guardia de entrada (bloquea injection/jailbreak — ES + EN)
   │
   ▼
Guardia de relevancia (bloquea preguntas off-topic sin keywords de perfil)
   │
   ▼
Router de fuentes
   ├── ChromaDB (siempre) — MMR k=8, fetch_k=30, lambda=0.6
   ├── GitHub API (proyectos/repos)
   └── HuggingFace API (modelos/spaces)
   │
   ▼
Construcción de contexto separado
   ├── context_proyecto — query enriquecida con proyecto_activo del historial
   └── context_referencia — GitHub, HuggingFace, chunks generales
   │
   ▼
LLM intercambiable (HuggingFace Inference API / Ollama)
   │
   ▼
Guardia de salida (valida que respuesta sea sobre Gastón)
   │
   ▼
Guardar en historial conversacional (proyecto_activo detectado)
   │
   ▼
Respuesta + CTA según intent del visitante
```

**Estado actual:** Fase 7 completada. Tests nivel 1 (158/158) + evaluación RAG nivel 2 + dashboard público.

---

## 2. Responsabilidad de cada archivo

```
scripts/ingest.py        — Ingesta incremental por hash MD5.
                           Lee .md de data/, chunkea, vectoriza con Ollama,
                           guarda en ChromaDB. Solo procesa archivos modificados.
                           Al terminar exporta eval_results.json si corresponde.

scripts/check_chroma.py  — Utilidad: lista fuentes y chunk counts en ChromaDB.
                           Útil para verificar ingesta y armar el golden dataset.

app/main.py              — Puerta de entrada + dashboard.
                           GET  /           → dashboard público (Jinja2 + HTMX)
                           POST /playground → endpoint público, rate limit 5/día
                           GET  /health     → status sin auth
                           POST /ask        → respuesta RAG con X-API-Key

app/rag_chain.py         — Cerebro / orquestador.
                           Coordina router → retrieval → prompt → LLM → historial.
                           responder(pregunta, include_contexts=False) — el flag
                           include_contexts=True expone los chunks para evaluación
                           RAGAS (no llega al endpoint productivo).

app/router.py            — Especialista en decisiones. Sin I/O, pura lógica.
                           Responde: ¿injection? ¿off-topic? ¿fuentes? ¿intent?
                           Keywords cortas con re.search + \b para evitar
                           substring match (ia, ai, ml, rag, bot, rol, hi, hey).

app/config.py            — Variables de configuración centralizadas.

app/templates/
└── dashboard.html       — Dashboard público. Jinja2 + HTMX.
                           Paleta de gaxoblanco.com (DM Sans, DM Mono, dark theme).
                           Tabs: playground / métricas / arquitectura / stack.

data/
└── eval_results.json    — Resultados cacheados de la última evaluación RAGAS.
                           Generado por test_rag_eval.py, leído por el dashboard.
                           No requiere RAGAS instalado en producción.
```

**La regla de dependencias:** `main` llama a `rag_chain`, `rag_chain` llama a `router`.
Nunca al revés. `router` no sabe que existe `rag_chain`.

---

## 3. Stack tecnológico

| Componente | Tecnología | Versión fija |
|---|---|---|
| Lenguaje | Python | 3.11 |
| API framework | FastAPI | 0.115.12 |
| ASGI server | Uvicorn | 0.34.0 |
| Templates | Jinja2 | 3.1.6 |
| Frontend interactivo | HTMX | 1.9.12 |
| Form parsing | python-multipart | 0.0.20 |
| Base vectorial | ChromaDB | 0.6.3 |
| LangChain core | langchain | 0.3.22 |
| LangChain Chroma | langchain-chroma | 0.2.2 |
| LangChain Ollama | langchain-ollama | 0.2.3 |
| LangChain HuggingFace | langchain-huggingface | 0.1.2 |
| HuggingFace Hub | huggingface-hub | 0.30.2 |
| Embeddings | nomic-embed-text via Ollama | — |
| LLM producción | Llama-3.1-8B via HF Inference API / Novita | — |
| LLM desarrollo | llama3.1:8b via Ollama | — |
| Rate limiting | slowapi | 0.1.9 |
| Variables de entorno | python-dotenv | 1.1.0 |

**Dependencias de desarrollo** (solo en `requirements-dev.txt`, no en producción):

| Componente | Tecnología | Versión fija |
|---|---|---|
| Testing nivel 1 | pytest | 8.3.5 |
| Testing async | pytest-asyncio | 0.24.0 |
| HTTP testing | httpx | 0.27.0 |
| Evaluación RAG | ragas | 0.2.15 |
| Datasets RAGAS | datasets | 3.6.0 |
| LLM juez RAGAS | openai (Ollama compat.) | 1.82.0 |

---

## 4. Modelo

Nodo intercambiable — `MODEL_PROVIDER` en `.env` define el provider sin cambiar código.
Prompt con intención comercial — CTA adaptado según intent del visitante.
Historial conversacional con detección de proyecto activo.

→ **`docs/MODELO.md`**

---

## 5. Fuentes de datos

ChromaDB guarda la narrativa propia (107 chunks en `data/`).
GitHub y HuggingFace se consultan en tiempo real.

```
data/
├── decisiones/       — decisiones técnicas documentadas por proyecto
├── experiencia/      — Flextech, That Day in London
├── orientacion/      — objetivos profesionales
├── perfil/           — experiencia_y_perfil (con resumen HyDE), preferencias
├── proyectos/        — Lineup, WhatsApp Booking Bot
├── stack/            — tecnologías con contexto real de uso
└── eval_results.json — resultados cacheados de evaluación RAGAS
```

**Nota HyDE en `experiencia_y_perfil.md`:** el archivo tiene un párrafo de resumen
antes del primer `##` con keywords de búsqueda naturales ("contame sobre vos",
"presentate", etc.). Esto mejora el retrieval para preguntas abiertas de perfil
sin alterar el contenido narrativo.

→ **`docs/FUENTES.md`**

---

## 6. Seguridad

**Endpoint `/ask` (chatbot):**
- `X-API-Key` header con `secrets.compare_digest` — evita timing attacks
- Rate limit: 20 req/min por IP via slowapi

**Endpoint `/playground` (dashboard público):**
- Sin API key — público
- Rate limit: 5 req/día por IP — más restrictivo que `/ask`
- Mismos filtros de input que `/ask`
- Sin `include_contexts` — los chunks no se exponen al browser
- Sin historial conversacional

**Pipeline:**
- Guardia de entrada: injection/jailbreak en ES + EN
- Keywords cortas con `re.search + \b` para evitar substring match
- Guardia de relevancia: off-topic bloqueado
- Guardia de salida: valida que respuesta sea sobre el perfil

→ **`docs/SEGURIDAD.md`**

---

## 7. Infraestructura y deploy

Tres contenedores Docker. Ollama solo sirve embeddings en producción.

→ **`docs/INFRAESTRUCTURA.md`**

**Estado producción:**
- VPS Donweb — 4GB RAM, Ubuntu 24, `149.50.128.92`
- Nginx reverse proxy → `localhost:8080` (puerto interno, no expuesto)
- SSL Let's Encrypt — certificado automático via certbot snap
- Dominio: `rag.gaxoblanco.com` → registro A apuntando al VPS
- Landing: `gaxoblanco.com` → `chat.js` apunta a `https://rag.gaxoblanco.com`
- Tres contenedores activos: `gaston-rag-api`, `gaston-rag-chroma`, `gaston-rag-ollama`

---

## 8. Tests

→ **`docs/TESTS.md`** — suite completa nivel 1
→ **`docs/TESTS_RAG.md`** — evaluación RAG nivel 2

**Resumen:**

| Suite | Archivo | Tests | Estado |
|---|---|---|---|
| Router (lógica pura) | `test_router.py` | 55 | ✅ 55/55 |
| API HTTP | `test_main.py` | 26 | ✅ 26/26 |
| Pipeline RAG | `test_rag_chain.py` | 49 | ✅ 49/49 |
| Ingesta incremental | `test_ingest.py` | 28 | ✅ 28/28 |
| **Nivel 1 total** | | **158** | **✅ 158/158** |
| Evaluación RAGAS | `test_rag_eval.py` | 11 preguntas | faithfulness 0.709 · answer_relevancy 0.698 |

**Correr tests:**
```bash
# Nivel 1 — siempre, rápido
docker compose -f docker/docker-compose.yml exec api pytest tests/ -v --ignore=tests/test_rag_eval.py --tb=short

# Nivel 2 — manual, cuando cambia el prompt o la knowledge base
docker compose -f docker/docker-compose.yml exec api pytest tests/test_rag_eval.py::test_resumen_dataset_completo -v -s
```

**Nota:** `test_rag_eval.py` requiere `requirements-dev.txt` instalado en el contenedor.
No corre en producción.

---

## 9. Dashboard

Panel de control público en `rag.gaxoblanco.com`.
Reemplaza la página en blanco con un portfolio técnico interactivo.

→ **`docs/DASHBOARD.md`**

**Tabs:**
- **playground** — 5 preguntas por sesión via `/playground`, respuestas en tiempo real con HTMX
- **métricas** — scores RAGAS cacheados, barras por pregunta, chunk counts por fuente
- **arquitectura** — flujo completo de una query con parámetros reales
- **stack** — tecnologías con versiones exactas

**Sin RAGAS en producción** — las métricas vienen de `data/eval_results.json`,
generado en desarrollo por `test_rag_eval.py` y commiteado junto con el código.
RAGAS implica +2gb extras.

---

## 10. Puntos de extensión futura

| Extensión | Estado |
|---|---|
| Deploy en Donweb VPS | ✅ Completado |
| HTTPS con Let's Encrypt | ✅ Completado |
| Integración landing page | ✅ Completado |
| Cerrar puerto 8080 con iptables | ✅ Completado |
| Tests nivel 1 — 158/158 | ✅ Completado |
| Evaluación RAG nivel 2 (RAGAS) | ✅ Completado — faithfulness 0.709 |
| Dashboard público con playground | ✅ Completado |
| Re-ingesta automática vía webhook | ❌ Descartado — knowledge base local |
| Context precision reference-free | ⏳ Pendiente — RAGAS 0.2.x no lo soporta sin ground truth |
| Historial de evaluaciones (gráfico de tendencia) | ⏳ Futuro — requiere persistir múltiples eval_results |

---

## 11. Historial de decisiones

| Fecha | Decisión | Alternativa descartada | Razón |
|---|---|---|---|
| Inicio | ChromaDB en contenedor separado | ChromaDB embedded | Datos persisten independiente del ciclo de vida de la API |
| Inicio | nomic-embed-text via Ollama | APIs externas | Sin costo, sin dependencia externa |
| Inicio | LinkedIn excluido | Scraping | Términos de servicio |
| Inicio | GitHub + HF en tiempo real | Duplicar en ChromaDB | No duplicar datos que ya tienen API |
| Fase 1 | Ollama nativo en Windows para desarrollo | Imagen Docker de Ollama | Timeout en descarga dentro de Docker |
| Fase 2 | Ingesta incremental por hash MD5 | Re-ingestar siempre | Solo procesa archivos que cambiaron |
| Fase 4 | MMR k=8, fetch_k=30, lambda=0.6 | similarity_search k=4 | that_day_london dominaba resultados |
| Fase 5 | HuggingFace Inference API / Novita | Ollama en VPS sin GPU | VPS sin GPU — ~2s respuesta, sin costo fijo |
| Fase 5 | InferenceClient directo | ChatHuggingFace | ChatHuggingFace descarga tokenizador de modelo gated → 403 |
| Fase 5 | Nodo intercambiable via MODEL_PROVIDER | Provider hardcodeado | Permite cambiar entre HF y Ollama sin refactor |
| Fase 6 | Contextos separados context_proyecto/context_referencia | Contexto único | Evita que preguntas de seguimiento mezclen proyectos |
| Fase 6 | Historial con proyecto_activo | Solo pregunta/respuesta | Enriquece queries ambiguas con proyecto del turno anterior |
| Fase 6 | Detección de intent visitante (recruiter/cliente/neutro) | Prompt único | CTA personalizado según audiencia — objetivo comercial |
| Fase 6 | Respuesta directa para contacto puro | Pasar por LLM | Evita timeouts y bloqueos en preguntas sin keywords técnicas |
| Deploy | Nginx como reverse proxy | Exponer puerto 8080 directo | HTTPS + puerto interno no expuesto al exterior |
| Deploy | certbot via snap | certbot apt | Versión apt desactualizada en Ubuntu 24 — conflicto de dependencias |
| Deploy | torch CPU-only en Dockerfile | torch default | torch default descarga nvidia_cublas (423MB) innecesario en VPS sin GPU |
| Deploy | guardia_relevancia como capa separada | Ampliar guardia_entrada | Separación de responsabilidades — injection vs off-topic son problemas distintos |
| Fase 7 | re.search + \b para keywords cortas | keyword in texto | "ia" matcheaba "noticias", "rol" matcheaba "desarrollar", "hi" matcheaba "hiciste" |
| Fase 7 | requirements-dev.txt separado | pytest + ragas en requirements.txt | RAGAS pesa ~300MB — no va a producción |
| Fase 7 | eval_results.json cacheado en data/ | RAGAS en producción | RAGAS no se instala en producción — métricas se generan en desarrollo y se commitean |
| Fase 7 | HTMX para dashboard | React / JS puro | Un solo stack Python — lógica de interacción en el servidor, sin JS propio |
| Fase 7 | Endpoint /playground separado de /ask | Exponer /ask público | Separa el rate limit y evita exponer la API key del chatbot productivo |
| Fase 7 | HyDE inverso en experiencia_y_perfil.md | Ajustar retrieval params | Queries de búsqueda en el documento mejoran el retrieval sin tocar el código |