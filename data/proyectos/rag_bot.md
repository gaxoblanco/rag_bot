# RAG Bot — Portfolio técnico interactivo
## Categoría: proyecto_detalle
## Período: Mayo 2026 — Presente (en producción)

Sistema RAG personal en producción en rag.gaxoblanco.com. Responde preguntas
sobre mi perfil profesional en lenguaje natural, consultando una knowledge base
vectorial propia. Construido con Python, FastAPI, LangChain, ChromaDB, Ollama,
Llama 3.1 8B via HuggingFace Inference API. Deploy en VPS Donweb con Docker,
Nginx y SSL. 158 tests unitarios, evaluación RAGAS con faithfulness 0.709.
Dashboard público con playground interactivo, métricas de evaluación y trazabilidad
del pipeline completo.

Preguntas frecuentes sobre este proyecto: qué es el RAG bot, cómo funciona este sistema,
cómo construiste esto, qué es un RAG, cómo funciona esta página, qué tecnologías usaste
para este proyecto, cómo deployaste esto, cómo evaluás el RAG, qué es RAGAS,
cómo funciona el dashboard, rag.gaxoblanco.com, cómo construiste este proyecto,
qué es este proyecto, cómo hiciste esto, cómo está construido, cómo lo armaste,
qué tecnologías usaste acá, cómo funciona el sistema de preguntas, qué hay detrás,
cómo funciona el chat, qué motor usa, cómo generás las respuestas,
cómo funciona el sistema de búsqueda, retrieval augmented generation.

---

## Por qué existe

Necesitaba un portfolio que demostrara lo que sé hacer, no que lo listara.
Un CV dice "sé Python y LangChain". Este sistema lo demuestra en tiempo real.
Quien visita la página no lee sobre el RAG — lo usa.

El segundo objetivo es operacional: el RAG responde todas las preguntas sobre
el perfil antes de una conversación real. Cuando alguien agenda un meet via Viner,
ya sabe con quién está hablando.

---

## Arquitectura

Pipeline completo de una query:

1. **Guardia de entrada** — bloquea injection y jailbreak en español e inglés.
   Keywords cortas con `re.search + \b` para evitar substring match.

2. **Guardia de relevancia** — bloquea preguntas off-topic sin keywords del perfil.
   Condicionada al historial: con conversación activa, preguntas ambiguas pasan.

3. **Router de fuentes** — decide qué fuentes consultar.
   ChromaDB siempre. GitHub en tiempo real si pregunta sobre repos.
   HuggingFace en tiempo real si pregunta sobre modelos.

4. **Retrieval MMR** — ChromaDB con Maximal Marginal Relevance.
   k=8, fetch_k=30, lambda=0.6. Dos contextos separados:
   `context_proyecto` (proyecto activo del historial) y `context_referencia`
   (GitHub, HuggingFace, chunks generales de otros proyectos).

5. **LLM** — Llama 3.1 8B via HuggingFace Inference API con Novita.
   ~2 segundos en producción. En desarrollo: Ollama local con GTX 1070.
   Provider intercambiable via `MODEL_PROVIDER` en `.env` sin cambiar código.

6. **Guardia de salida** — valida que la respuesta contenga keywords del perfil.
   Condicionada al historial: con conversación activa, respuestas narrativas
   sin keywords pasan si tienen más de 5 palabras.

7. **Historial conversacional** — detecta proyecto activo en cada respuesta.
   Enriquece queries ambiguas de seguimiento con el contexto del turno anterior.
   Cuando el proyecto activo está agotado temáticamente, pivotea a otros proyectos.

---

## Knowledge base

129 chunks en ChromaDB al momento del deploy. 9 fuentes de datos:

- `tecnologias` — stack con contexto real de uso por proyecto
- `whatsapp_booking_bot` — Viner, el bot de turnos
- `decisiones_tecnicas` — decisiones de arquitectura documentadas
- `that_day_london` — experiencia laboral
- `lineup` — proyecto personal de playlists con OCR + Spotify
- `objetivos_profesionales` — orientación y futuro
- `preferencias` — forma de trabajar y stack preferido
- `experiencia_y_perfil` — trayectoria y perfil general
- `flextech` — proyecto freelance

**Patrón HyDE inverso:** los archivos clave tienen un párrafo de resumen antes
del primer `##` con keywords de búsqueda naturales en el mismo chunk que el título.
Mejora el retrieval para queries abiertas sin tocar el código.

---

## Ingesta incremental

`scripts/ingest.py` procesa solo los archivos `.md` que cambiaron desde la
última ingesta — detección por hash MD5. Si el archivo no cambió, se saltea.
Al terminar, exporta `data/eval_results.json` con métricas cacheadas para el dashboard.

---

## Tests

**Nivel 1 — 158 tests unitarios, todos pasando:**

| Suite | Tests |
|---|---|
| `test_router.py` — lógica pura del router | 55 |
| `test_main.py` — capa HTTP FastAPI | 26 |
| `test_rag_chain.py` — pipeline RAG mockeado | 49 |
| `test_ingest.py` — ingesta incremental | 28 |

**Nivel 2 — evaluación RAGAS con LLM juez:**
- faithfulness: 0.709 (threshold 0.70) ✅
- answer_relevancy: 0.698 (threshold 0.70) ≈
- 9/11 preguntas evaluadas (golden dataset de 11 preguntas)
- LLM juez: llama3.1:8b via Ollama con GTX 1070

**Nivel 3 — 26 tests de conversación multi-turno:**
Escenarios reales: cambio brusco de tema, preguntas ambiguas con historial,
saludo en medio de conversación, escalada off-topic, seguimiento sin antecedente,
cambio de idioma, intent que cambia entre turnos. 26/26 pasando.

---

## Dashboard

Panel de control público en `rag.gaxoblanco.com`. Sin RAGAS en producción —
las métricas vienen de `eval_results.json` generado en desarrollo y commiteado.

**Playground** — 5 preguntas por sesión. Muestra la respuesta del LLM,
las fuentes consultadas, el trace completo del pipeline (intent detectado,
fuentes activadas, guardia de entrada/relevancia/salida, chunks por fuente,
proyecto activo, turnos de historial) y el primer chunk recuperado expandible.

**Métricas** — scores RAGAS por pregunta con barras coloreadas, chunk counts por fuente.

**Arquitectura** — flujo paso a paso de una query con parámetros reales.

**Stack** — tecnologías con versiones exactas.

---

## Decisiones técnicas

**ChromaDB en contenedor separado:** los datos vectoriales sobreviven independientemente
del ciclo de vida de la API. Con ChromaDB embedded, un rebuild borra la knowledge base.

**nomic-embed-text via Ollama:** embeddings locales sin costo ni dependencia externa.
274 MB, corre en CPU en producción (VPS sin GPU).

**InferenceClient directo:** `ChatHuggingFace` intenta descargar el tokenizador
del modelo gated y falla con 403. `InferenceClient` llama solo al endpoint de
inferencia sin descargar nada localmente.

**RAGAS no va a producción:** +2GB de dependencias para métricas que se generan
en desarrollo. Las métricas se cachean en `eval_results.json` y se commitean.

**HTMX para el dashboard:** un solo stack Python. La lógica de interacción
vive en el servidor, sin JavaScript propio. FastAPI devuelve fragmentos HTML
que HTMX inserta en la página.

---

## Stack completo

- Python 3.11 + FastAPI 0.115 + Uvicorn
- LangChain 0.3 + langchain-chroma 0.2 + langchain-ollama 0.2
- ChromaDB 0.6.3 (contenedor separado con volumen persistente)
- nomic-embed-text via Ollama 0.6.8 (embeddings locales)
- Llama 3.1 8B via HuggingFace Inference API / Novita (producción)
- llama3.1:8b via Ollama + GTX 1070 (desarrollo)
- Jinja2 3.1 + HTMX 1.9 (dashboard)
- slowapi (rate limiting: 20/min en /ask, 5/día en /playground)
- pytest 8.3 + RAGAS 0.2.15 (testing y evaluación)
- Docker Compose (3 contenedores) + Nginx + Let's Encrypt
- VPS Donweb — 4GB RAM, Ubuntu 24