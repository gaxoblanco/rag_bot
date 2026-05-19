# MODELO.md
## RAG Personal · Gastón Blanco

> Detalle del nodo de modelo, prompt template, parámetros de retrieval y router de intents.
> Documento vivo — actualizar cuando se ajusten parámetros o cambie el provider.

---

## Índice

1. [Nodo de modelo — diseño intercambiable](#1-nodo-de-modelo)
2. [Prompt template](#2-prompt-template)
3. [Parámetros de retrieval](#3-parametros-de-retrieval)
4. [Router de intents](#4-router-de-intents)
5. [Puntos de ajuste](#5-puntos-de-ajuste)

---

## 1. Nodo de modelo

Diseñado para ser intercambiable sin tocar el resto del código.
Dos variables en `app/config.py` controlan todo.

```python
# app/config.py
MODEL_PROVIDER = "deepseek"   # "deepseek" | "ollama"
MODEL_NAME     = "deepseek-chat"  # "phi3:mini" cuando sea Ollama
```

```python
# app/rag_chain.py — el resto del código no sabe qué provider usa
if config.MODEL_PROVIDER == "deepseek":
    llm = ChatOpenAI(
        base_url="https://api.deepseek.com",
        api_key=os.getenv("DEEPSEEK_API_KEY"),
        model=config.MODEL_NAME
    )
elif config.MODEL_PROVIDER == "ollama":
    llm = ChatOllama(
        base_url=f"http://{os.getenv('OLLAMA_HOST')}:11434",
        model=config.MODEL_NAME
    )
```

**Para migrar a Ollama local:** cambiar las dos variables. Nada más.

---

## 2. Prompt template

### Decisión de tono

**El tono lo define el prompt, no la knowledge base.**
Los archivos en `data/` pueden estar escritos en primera o tercera persona — no importa.
El modelo responde según lo que el prompt le indique.
Para cambiar el tono: modificar el prompt aquí. No hay que reescribir ningún archivo de datos.

**Tono actual:** primera persona — el modelo responde *como* Gastón, no *sobre* Gastón.
Esto genera más conexión con reclutadores y clientes que consultan el bot.

### Prompt activo

```
Sos Gastón Blanco, desarrollador Fullstack especializado en ML/AI.
Respondé en primera persona, como si fueras vos hablando directamente.

Usá ÚNICAMENTE la información del contexto provisto para responder.
Si la información no está en el contexto, decí explícitamente que
no tenés esa información — no inferras ni inventes.
Respondé en el mismo idioma de la pregunta.
Sé concreto. Mencioná tecnologías y métricas cuando estén disponibles en el contexto.
No rompas el personaje — no digas que sos una IA ni que estás leyendo un documento.

Contexto:
{context}

Pregunta: {question}

Respuesta:
```

### Variante — tercera persona (desactivada)

Si se quiere un tono más formal o de ficha técnica, reemplazar el prompt activo por:

```
Sos un asistente que responde preguntas sobre Gastón Blanco,
desarrollador Fullstack especializado en ML/AI.

Respondé ÚNICAMENTE basándote en el contexto provisto.
Si la información no está en el contexto, decí explícitamente
que no tenés esa información — no inferras ni inventes.
Respondé en el mismo idioma de la pregunta.
Sé preciso. Citá tecnologías y métricas cuando estén disponibles.

Contexto:
{context}

Pregunta: {question}

Respuesta:
```

---

## 3. Parámetros de retrieval

| Parámetro | Valor actual | Rango sugerido | Efecto |
|---|---|---|---|
| `k` chunks recuperados | 4 | 3–6 | Más k = más contexto, más tokens, más costo |
| Chunk size | 500 tokens | 300–700 | Chunks grandes = más contexto por chunk |
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

**Implementación MVP:** clasificación por keywords en `app/router.py`.
**Implementación futura:** LLM-based router para mayor precisión.

---

## 5. Puntos de ajuste

- **Respuestas incompletas** → subir `k` a 5–6
- **Respuestas con info irrelevante** → bajar `k` a 3, subir similarity threshold a 0.8
- **Respuestas en idioma incorrecto** → agregar forzado de idioma al prompt
- **Pregunta clasificada en intent equivocado** → agregar keywords en `app/router.py`
- **Tono muy técnico** → suavizar instrucción de tono en el prompt template