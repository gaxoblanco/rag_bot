# TESTS_RAG.md
## RAG Personal · Gastón Blanco

> Planificación de la evaluación de calidad del sistema RAG (Nivel 2).
> Basado en investigación de frameworks actuales — Mayo 2026.
> Estado: planificación completa — pendiente de implementación.

---

## Índice

1. [Por qué nivel 2 es diferente](#1-diferencia)
2. [Decisión de framework — RAGAS](#2-framework)
3. [Métricas seleccionadas](#3-metricas)
4. [Lo que NO necesitamos escribir a mano](#4-sin-ground-truth)
5. [Golden dataset — solo preguntas](#5-golden-dataset)
6. [Arquitectura del test](#6-arquitectura)
7. [Thresholds recomendados](#7-thresholds)
8. [Qué NO evalúa el nivel 2](#8-limites)
9. [Plan de implementación](#9-plan)

---

## 1. Por qué nivel 2 es diferente

Los tests de nivel 1 verifican **comportamiento** — si el sistema bloquea,
si devuelve la estructura correcta, si el historial se guarda.
Son deterministas: dado un input, el output es siempre el mismo.

El nivel 2 verifica **calidad** — si el sistema responde bien preguntas reales
sobre el perfil. El LLM no es determinista: la misma pregunta puede generar
respuestas ligeramente distintas en cada ejecución.

**El problema central:** ¿cómo medir si una respuesta es "suficientemente buena"?

```
Pregunta: "¿qué hace el WhatsApp Booking Bot?"

Respuesta A: "El WhatsApp Booking Bot es un sistema de gestión de turnos
              que usa spaCy para NLU y Twilio para mensajería."

Respuesta B: "Desarrollé un bot para WhatsApp que permite agendar turnos
              usando procesamiento de lenguaje natural con spaCy."

¿Cuál es mejor? ¿Son ambas aceptables?
→ Ambas son válidas si están soportadas por el contexto recuperado.
  Eso es lo que mide RAGAS automáticamente, sin comparar strings.
```

**Supuesto corregido respecto al plan original:**
No necesitamos escribir respuestas de referencia para la mayoría de las métricas.
RAGAS evalúa reference-free usando un LLM como juez — compara la respuesta
contra el contexto recuperado, no contra una respuesta esperada hardcodeada.

---

## 2. Decisión de framework — RAGAS

**Framework elegido: RAGAS**

```bash
pip install ragas
```

**Por qué RAGAS sobre DeepEval:**

| Criterio | RAGAS | DeepEval |
|---|---|---|
| Integración con LangChain | Nativa — ya en el stack | Manual |
| Reference-free | Sí para 3/4 métricas | Sí |
| Complejidad de setup | Baja | Media |
| Ideal para | Experimentación, proyectos personales | CI/CD enterprise |
| Filosofía | Medición con scores | Unit testing con pass/fail |

RAGAS es la elección correcta para un proyecto personal con un solo developer.
DeepEval tiene más sentido cuando hay un equipo y pipelines de CI/CD formales.

**LLM juez:** Llama 3.1 8B via Ollama — ya está corriendo en el stack,
sin costo adicional. Si la calidad de evaluación es insuficiente,
se puede escalar a HuggingFace Inference API con el mismo modelo.

---

## 3. Métricas seleccionadas

### Faithfulness (fidelidad al contexto)
La respuesta está soportada por los chunks recuperados de ChromaDB.
Detecta alucinaciones: el LLM no debe inventar información fuera del contexto.

```
Contexto recuperado: "El bot usa spaCy para NLU y Twilio para mensajería."
Respuesta válida:    "Usa spaCy y Twilio."           ← soportado
Respuesta inválida:  "Usa Dialogflow y Twilio."      ← Dialogflow no está en contexto
```

**Reference-free:** sí. RAGAS extrae claims de la respuesta y verifica
cada uno contra el contexto. Score = claims soportados / claims totales.

---

### Answer Relevancy (relevancia de la respuesta)
La respuesta es pertinente a la pregunta. Detecta respuestas verídicas
pero que no responden lo que se preguntó.

```
Pregunta:  "¿cuánto cobrás por un proyecto?"
Inválida:  "Trabajé con Python y FastAPI."  ← verídico pero no responde
Válida:    "Depende del proyecto. Escribime por WhatsApp..."
```

**Reference-free:** sí. RAGAS genera preguntas inversas desde la respuesta
y mide si apuntan de vuelta a la pregunta original.

---

### Context Precision (precisión del retrieval)
Los chunks recuperados de ChromaDB son relevantes para la pregunta.
Evalúa el retrieval, no el LLM.

```
Pregunta: "¿qué hace Lineup?"
Chunks relevantes:   lineup.md            ← debe aparecer en top-k
Chunks irrelevantes: that_day_london.md   ← no debe dominar los resultados
```

**Reference-free:** sí. RAGAS evalúa si cada chunk recuperado es útil
para responder la pregunta usando el LLM juez.

---

### Context Recall (cobertura del retrieval)
¿Se recuperó toda la información necesaria para responder bien?

**Requiere ground truth:** sí. Esta es la única métrica que necesita
una respuesta de referencia escrita a mano.

**Decisión:** implementar context recall solo para las preguntas más críticas
(proyectos principales) donde vale la pena escribir la referencia.
Para el resto, las tres métricas anteriores son suficientes.

---

## 4. Lo que NO necesitamos escribir a mano

Este fue el supuesto incorrecto del plan original.

| Métrica | Necesita ground truth | Cómo evalúa |
|---|---|---|
| Faithfulness | ❌ No | Respuesta vs contexto recuperado |
| Answer Relevancy | ❌ No | Respuesta vs pregunta original |
| Context Precision | ❌ No | Chunks recuperados vs pregunta |
| Context Recall | ✅ Sí | Chunks recuperados vs respuesta esperada |

**En la práctica:** el golden dataset es solo una lista de preguntas.
RAGAS llama al sistema real, recolecta la respuesta y los chunks,
y evalúa todo automáticamente.

---

## 5. Golden dataset — solo preguntas

15 preguntas que cubren los casos más importantes.
Organizadas por lo que evalúan principalmente.

```python
# Fuentes verificadas contra ChromaDB (107 chunks, 9 fuentes — Mayo 2026):
#   decisiones_tecnicas (12), experiencia_y_perfil (8), flextech (3),
#   lineup (11), objetivos_profesionales (10), preferencias (10),
#   tecnologias (21), that_day_london (13), whatsapp_booking_bot (19)

GOLDEN_DATASET = [

    # ── Proyectos técnicos ───────────────────────────────────────────────────────
    {
        "id": "whatsapp_descripcion",
        "pregunta": "¿qué hace el WhatsApp Booking Bot?",
        "chunks_esperados": ["whatsapp_booking_bot"],
    },
    {
        "id": "whatsapp_stack",
        "pregunta": "¿qué tecnologías usa el bot de WhatsApp?",
        "chunks_esperados": ["whatsapp_booking_bot", "tecnologias"],
    },
    {
        "id": "lineup_descripcion",
        "pregunta": "¿qué es Lineup?",
        "chunks_esperados": ["lineup"],
    },
    {
        "id": "lineup_spotify",
        "pregunta": "¿cómo se conecta Lineup con Spotify?",
        "chunks_esperados": ["lineup"],
    },

    # ── Stack y tecnologías ──────────────────────────────────────────────────────
    {
        "id": "stack_general",
        "pregunta": "¿qué tecnologías usás?",
        "chunks_esperados": ["tecnologias"],
    },
    {
        "id": "stack_docker",
        "pregunta": "¿tenés experiencia con Docker?",
        "chunks_esperados": ["tecnologias", "whatsapp_booking_bot"],
    },
    {
        "id": "stack_python_js",
        "pregunta": "¿usás más Python o JavaScript?",
        "chunks_esperados": ["tecnologias"],
    },

    # ── Experiencia laboral ──────────────────────────────────────────────────────
    {
        "id": "experiencia_general",
        "pregunta": "¿dónde trabajaste antes?",
        "chunks_esperados": ["experiencia_y_perfil", "flextech", "that_day_london"],
    },
    {
        "id": "experiencia_flextech",
        "pregunta": "¿qué hiciste en Flextech?",
        "chunks_esperados": ["flextech"],
    },
    {
        "id": "experiencia_that_day",
        "pregunta": "¿qué hiciste en That Day in London?",
        "chunks_esperados": ["that_day_london"],
    },

    # ── Orientación profesional ──────────────────────────────────────────────────
    {
        "id": "orientacion_futuro",
        "pregunta": "¿a dónde querés ir profesionalmente?",
        "chunks_esperados": ["objetivos_profesionales"],
    },
    {
        "id": "orientacion_aprender",
        "pregunta": "¿qué querés aprender?",
        "chunks_esperados": ["objetivos_profesionales"],
    },

    # ── Perfil general ───────────────────────────────────────────────────────────
    {
        "id": "perfil_general",
        "pregunta": "contame sobre vos",
        "chunks_esperados": ["experiencia_y_perfil"],
    },

    # ── Decisiones técnicas ──────────────────────────────────────────────────────
    # decisiones_tecnicas tiene 12 chunks — buena fuente para testear retrieval
    {
        "id": "decisiones_arquitectura",
        "pregunta": "¿por qué elegiste ChromaDB en lugar de otras bases vectoriales?",
        "chunks_esperados": ["decisiones_tecnicas"],
    },

    # ── Preguntas de seguimiento — requieren 2 turnos ────────────────────────────
    {
        "id": "seguimiento_bot_nlu",
        "pregunta": "¿y qué NLU usaste?",
        "contexto_previo": "¿qué hace el WhatsApp Booking Bot?",
        "chunks_esperados": ["whatsapp_booking_bot"],
        "nota": "Ambigua sin historial — con historial debe resolver correctamente",
    },
    {
        "id": "seguimiento_lineup_tecnologia",
        "pregunta": "¿en qué lenguaje está hecho?",
        "contexto_previo": "¿qué es Lineup?",
        "chunks_esperados": ["lineup", "tecnologias"],
        "nota": "Ambigua sin historial — con historial debe resolver correctamente",
    },
]
```

**Total:** 16 preguntas — 14 independientes + 2 de seguimiento.
Las de seguimiento requieren correr 2 turnos: primero el `contexto_previo`,
luego la pregunta real, para que el historial esté cargado.

**Nota:** `interpretabilidad_ia` no está en ChromaDB — fue removida del dataset
o nunca se ingresó. No incluída en el golden dataset.
`preferencias` tiene 10 chunks de tipo `general` — no se usa en el dataset
porque las preguntas de preferencias tienden a ser ambiguas para RAGAS.

---

## 6. Arquitectura del test

```
tests/
└── test_rag_eval.py   ← NO corre junto con nivel 1
                          solo cuando se llama explícitamente
```

**Los tests de evaluación RAG no deben correr en el run normal de pytest.**
Son lentos (cada pregunta hace una llamada real al LLM + al LLM juez)
y tienen variabilidad por la no-determinismo del LLM.

```bash
# Nivel 1 — siempre, rápido, sin costo
pytest tests/ -v --ignore=tests/test_rag_eval.py

# Nivel 2 — manual, cuando se cambia el prompt, el retrieval o la knowledge base
pytest tests/test_rag_eval.py -v -s
```

**Flujo de una evaluación con RAGAS:**

```
Golden dataset (15 preguntas)
         │
         ▼
responder(pregunta)         ← llamada real al sistema
         │
         ├── answer         ─┐
         ├── sources         ├── se pasan a RAGAS como dataset
         └── contexto raw   ─┘  (hay que exponer los chunks del retrieval)
         │
         ▼
RAGAS evaluate()
         │
         ├── faithfulness      → score 0-1
         ├── answer_relevancy  → score 0-1
         └── context_precision → score 0-1
         │
         ▼
assert score >= threshold
print(resultado detallado por pregunta)
```

**Problema a resolver:** `responder()` actualmente no expone los chunks
recuperados de ChromaDB en el resultado — solo devuelve `{answer, sources, blocked}`.
Para RAGAS necesitamos el texto de los chunks, no solo el nombre de la fuente.
Hay que agregar `"contexts"` al retorno de `responder()` o crear una función
auxiliar que haga el retrieval y lo exponga para evaluación.

---

## 7. Thresholds recomendados

Basados en la literatura (RAGAS docs, 2025):

| Métrica | Threshold mínimo | Threshold producción |
|---|---|---|
| Faithfulness | 0.7 | 0.85 |
| Answer Relevancy | 0.7 | 0.80 |
| Context Precision | 0.6 | 0.75 |

Para este sistema (herramienta personal, no crítica):
usar thresholds mínimos en primera evaluación y ajustar según resultados.

**Criterio de aprobación del dataset completo:**
- Score promedio por métrica ≥ threshold
- Ninguna pregunta con score < 0.5 en faithfulness (alucinación grave)

---

## 8. Qué NO evalúa el nivel 2

**El tono** — si la respuesta suena como Gastón. Subjetivo, evaluación manual.

**El CTA** — cubierto por nivel 1 (`test_contacto_respuesta_contiene_cta`).

**Los guards** — cubiertos completamente por nivel 1. El nivel 2 solo
evalúa preguntas que deben pasar todos los filtros.

**Latencia** — no es parte de la calidad del RAG. Se monitorea en producción.

**Preguntas bloqueadas** — el nivel 2 asume que todas las preguntas
del golden dataset llegan al LLM. Si alguna es bloqueada por los guards,
es un error del dataset, no del RAG.

---

## 9. Plan de implementación

**Paso 1 — Exponer contexto en responder()**
Modificar `rag_chain.py` para que el resultado incluya los chunks recuperados:
```python
# Retorno actual
{"answer": str, "sources": list[str], "blocked": bool}

# Retorno extendido para evaluación
{"answer": str, "sources": list[str], "blocked": bool,
 "contexts": list[str]}  # textos de los chunks — solo para eval, no para producción
```
O bien crear `responder_con_contexto()` separada que no toque el endpoint productivo.

**Paso 2 — Instalar RAGAS en el contenedor**
Agregar a `requirements.txt`:
```
ragas==0.2.x
```

**Paso 3 — Leer los archivos data/ para verificar chunks_esperados**
Confirmar que los nombres en `chunks_esperados` del dataset coinciden
con los valores reales de `metadata["fuente"]` en ChromaDB.

**Paso 4 — Escribir test_rag_eval.py**
Estructura base con RAGAS, el dataset y los thresholds.

**Paso 5 — Primera corrida y calibración**
Correr contra el sistema real, ver los scores, ajustar thresholds
si son demasiado estrictos o laxos para este caso de uso.

**Paso 6 — (Opcional) Context Recall para preguntas críticas**
Escribir respuestas de referencia solo para whatsapp_bot y lineup,
agregar context_recall como métrica adicional para esos casos.
