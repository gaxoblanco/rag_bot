# MODELO.md
## RAG Personal · Gastón Blanco

> Detalle del nodo de modelo, prompt template, parámetros de retrieval y router de intents.
> Documento vivo — actualizar cuando se ajusten parámetros o cambie el provider.

---

## Índice

1. [Nodo de modelo](#1-nodo-de-modelo)
2. [Prompt template](#2-prompt-template)
3. [Parámetros de retrieval](#3-parametros-de-retrieval)
4. [Router de intents](#4-router-de-intents)
5. [Puntos de ajuste](#5-puntos-de-ajuste)

---

## 1. Nodo de modelo

**Provider actual: HuggingFace Inference API (Novita)**

El nodo de modelo es intercambiable via variable de entorno `MODEL_PROVIDER`.

| Provider | Modelo | Cuándo usar |
|---|---|---|
| `huggingface` (activo) | `meta-llama/Llama-3.1-8B-Instruct` | Producción — sin VRAM, ~2s respuesta |
| `ollama` | `llama3.1:8b` | Desarrollo local con GPU |

**Embeddings:** `nomic-embed-text` via Ollama — siempre local, sin costo.

```python
# .env
MODEL_PROVIDER=huggingface
HF_INFERENCE_MODEL=meta-llama/Llama-3.1-8B-Instruct
HF_TOKEN=hf_...

# Para volver a Ollama local:
MODEL_PROVIDER=ollama
MODEL_NAME=llama3.1:8b
```

**Decisión técnica:** Se usa `InferenceClient` directo de `huggingface_hub` con
`provider="novita"` — no `ChatHuggingFace` ni `HuggingFaceEndpoint`, porque ambos
intentan descargar el tokenizador del modelo gated y fallan con 403.

---

## 2. Prompt template

### Decisión de tono

**El tono lo define el prompt, no la knowledge base.**
Para cambiar el tono: modificar solo el prompt. No hay que reescribir los datos.

**Tono actual:** primera persona, técnico con calidez, semi-técnico para audiencia
no necesariamente técnica (recruiters y clientes potenciales).

### Prompt activo

```
Sos Gastón Blanco, desarrollador Fullstack especializado en ML/AI.
Respondé siempre en primera persona. Nunca uses "Gastón" para referirte a vos mismo.

Usá ÚNICAMENTE la información del contexto provisto para responder.
Nunca agregues información que no esté explícitamente en el contexto,
aunque parezca lógica o probable. Si no está, no lo digas.
Si la información no está en el contexto, decí que no tenés esa información.
No rompas el personaje — no digas que sos una IA ni que estás leyendo un documento.
Respondé en el mismo idioma de la pregunta.
Sé concreto y directo. Mencioná tecnologías y métricas cuando estén disponibles.
No uses saludos ni cierres como "Hola", "Espero que te sea útil" o similares.
Si el usuario saluda, respondé con una sola oración breve y esperá la pregunta.
No uses listas numeradas ni viñetas salvo que la pregunta lo requiera explícitamente.
Respondé en el mínimo de párrafos necesarios — si una idea se puede decir en una
oración, no la expandas. Priorizá densidad de información sobre extensión.
Si te preguntan qué preferís entre dos tecnologías, respondé con cuál usaste
y por qué, basándote solo en lo que dice el contexto. No expreses preferencias abstractas.
Cuando alguien muestre intención de contratar o trabajar juntos pero no haga una pregunta
concreta, no hagas preguntas abiertas. En cambio, ofrecé rutas específicas. Ejemplo:
"Si querés conocer más antes de agendar, puedo contarte sobre mi experiencia en ML,
los proyectos que tengo en producción, o cómo trabajo. ¿Por dónde arrancamos?"
Si alguien pregunta por precios o costos, no des números. En cambio, explicá que
depende del proyecto y derivá al WhatsApp para entender qué necesitan.
Si alguien pregunta sobre vos en tercera persona ("qué hace Gastón Blanco",
"qué le gusta a Gastón"), respondé igual en primera persona como si te preguntaran
directamente a vos. No aclares que estás hablando de vos mismo.
Si alguien pregunta si sos una IA, un bot, o una persona real, respondé que sos
Gastón Blanco y que este es tu espacio para responder preguntas sobre tu perfil.
No confirmes ni niegues ser una IA — simplemente redirigí al perfil.
Al final de tu respuesta, si el contexto lo justifica, agregá esta frase: {cta_bloque}

{historial_bloque}
--- CONTEXTO DEL PROYECTO EN FOCO ---
{context_proyecto}

--- CONTEXTO DE REFERENCIA ---
{context_referencia}

Pregunta: {question}

Respuesta:
```

### CTAs por intent de visitante

El sistema detecta si el visitante es recruiter, cliente o neutro y adapta el cierre:

```python
# Recruiter
"Si lo que escuchaste te genera interés para una posición o para hablar
sobre el perfil, el botón de WhatsApp está disponible para agendar un meet."

# Cliente
"Si tenés un proyecto en mente y querés ver si puedo ayudarte,
el botón de WhatsApp está justo ahí para agendar un meet corto."

# Neutro
"Si querés saber más o coordinar algo,
el botón de WhatsApp está disponible para agendar un meet."
```

---

## 3. Parámetros de retrieval

**Método:** MMR (Maximal Marginal Relevance) — diversidad + relevancia.

| Parámetro | Variable .env | Valor default | Efecto |
|---|---|---|---|
| `k` chunks devueltos | `RETRIEVAL_K` | 8 | Más k = más contexto |
| `fetch_k` candidatos | `RETRIEVAL_FETCH_K` | 30 | Pool antes de diversificar |
| `lambda_mult` | `RETRIEVAL_LAMBDA` | 0.6 | 0=max diversidad, 1=max relevancia |

**Por qué MMR:** `that_day_london.md` tiene 12 chunks — sin MMR domina todos los
resultados de similarity search. MMR fuerza diversidad de fuentes.

**Contextos separados:**
- `context_proyecto` — chunks del proyecto activo en la conversación (query enriquecida)
- `context_referencia` — GitHub, HuggingFace, otros chunks generales

---

## 4. Router de intents

### Fuentes de datos

| Intent | Fuentes activadas | Ejemplos |
|---|---|---|
| `perfil_narrativo` | ChromaDB | "¿dónde trabajó?", "¿qué quiere aprender?" |
| `proyectos_tecnicos` | ChromaDB + GitHub | "¿qué proyectos tiene?", "¿usa Docker?" |
| `modelos_ml` | ChromaDB + HuggingFace | "¿qué modelos publicó?", "¿qué spaces tiene?" |
| `general` | ChromaDB | cualquier pregunta ambigua |

### Intent de visitante

Detecta si quien pregunta es recruiter, cliente o neutro para personalizar el CTA.

| Intent | Keywords ejemplo |
|---|---|
| `recruiter` | trabajo, posición, hiring, CV, sueldo, disponibilidad |
| `cliente` | proyecto, necesito, presupuesto, podés hacer, freelance |
| `neutro` | cualquier otra pregunta |

### Guardias

**Entrada:** bloquea prompt injection, jailbreak, cambio de rol, autoridad falsa.
Keywords en español e inglés — `ignora`, `olvida`, `discard`, `act as`, `i am the owner`, etc.

**Salida:** valida que la respuesta contenga al menos una keyword del perfil de Gastón.

### Respuesta directa para contacto puro

Preguntas como "podés ayudarme?", "necesito un bot", "tengo un proyecto" se responden
directamente con el CTA sin pasar por ChromaDB ni el LLM — evita timeouts y bloqueos.

---

## 5. Puntos de ajuste

- **Respuestas incompletas** → subir `RETRIEVAL_K` a 10
- **Respuestas con info de otro proyecto** → revisar `_proyecto_activo()` en `rag_chain.py`
- **Pregunta clasificada en intent equivocado** → agregar keywords en `app/router.py`
- **Tono muy verboso** → reforzar instrucción de densidad en el prompt
- **Cambiar provider** → editar `MODEL_PROVIDER` en `.env` y reiniciar la API
- **Nueva vertical del bot** → agregar keywords en `_PROYECTOS_KEYWORDS["whatsapp_booking_bot"]`