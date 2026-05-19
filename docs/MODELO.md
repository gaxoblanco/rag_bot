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

**Provider actual: Ollama local**
- Embeddings: `nomic-embed-text` — genera los vectores para ChromaDB
- LLM: `phi3:mini` — genera las respuestas

Ambos corren en el mismo servicio Ollama, sin costo por token, sin dependencia externa.

```python
# app/config.py
OLLAMA_HOST            = os.getenv("OLLAMA_HOST", "ollama")
OLLAMA_PORT            = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")
MODEL_NAME             = os.getenv("MODEL_NAME", "phi3:mini")
```

```python
# app/rag_chain.py
from langchain_ollama import OllamaEmbeddings, ChatOllama

embeddings = OllamaEmbeddings(
    model    = config.OLLAMA_EMBEDDING_MODEL,
    base_url = f"http://{config.OLLAMA_HOST}:{config.OLLAMA_PORT}",
)

llm = ChatOllama(
    model    = config.MODEL_NAME,
    base_url = f"http://{config.OLLAMA_HOST}:{config.OLLAMA_PORT}",
)
```

---

## 2. Prompt template

### Decisión de tono

**El tono lo define el prompt, no la knowledge base.**
Los archivos en `data/` pueden estar en primera o tercera persona — no importa.
Para cambiar el tono: modificar el prompt aquí. No hay que reescribir los datos.

**Tono actual:** primera persona — el modelo responde *como* Gastón.

### Prompt activo

```
Sos Gastón Blanco, desarrollador Fullstack especializado en ML/AI.
Respondé en primera persona, como si fueras vos hablando directamente.

Usá ÚNICAMENTE la información del contexto provisto para responder.
Si la información no está en el contexto, decí que no tenés esa información.
No rompas el personaje — no digas que sos una IA ni que estás leyendo un documento.
Respondé en el mismo idioma de la pregunta.
Sé concreto. Mencioná tecnologías y métricas cuando estén disponibles.

Contexto:
{context}

Pregunta: {question}

Respuesta:
```

### Variante — tercera persona (desactivada)

Reemplazar la primera línea por:
```
Sos un asistente que responde preguntas sobre Gastón Blanco,
desarrollador Fullstack especializado en ML/AI.
```

---

## 3. Parámetros de retrieval

| Parámetro | Valor actual | Rango sugerido | Efecto |
|---|---|---|---|
| `k` chunks recuperados | 4 | 3–6 | Más k = más contexto |
| Chunk size | 500 tokens | 300–700 | Tamaño de cada fragmento |
| Chunk overlap | 50 tokens | 20–100 | Evita cortar ideas a la mitad |
| Similarity threshold | 0.7 | 0.6–0.85 | Filtra chunks poco relevantes |

---

## 4. Router de intents

Clasifica cada pregunta antes de decidir qué fuentes consultar.

| Intent | Fuentes activadas | Ejemplos |
|---|---|---|
| `perfil_narrativo` | ChromaDB | "¿dónde trabajó?", "¿qué quiere aprender?" |
| `proyectos_tecnicos` | ChromaDB + GitHub | "¿qué proyectos tiene?", "¿usa Docker?" |
| `modelos_ml` | ChromaDB + HuggingFace | "¿qué modelos publicó?" |
| `general` | ChromaDB | cualquier pregunta ambigua |

**Implementación actual:** pendiente — Fase 4.

---

## 5. Puntos de ajuste

- **Respuestas incompletas** → subir `k` a 5–6
- **Respuestas con info irrelevante** → bajar `k` a 3, subir similarity a 0.8
- **Pregunta clasificada en intent equivocado** → agregar keywords en `app/router.py`
- **Tono muy técnico** → suavizar instrucción de tono en el prompt
- **Respuestas lentas** → phi3:mini es lento en CPU — considerar tinyllama como alternativa más liviana