"""
tests/test_rag_eval.py
----------------------
Evaluacion de calidad del sistema RAG — Nivel 2.

A diferencia del nivel 1 (comportamiento determinista), este archivo
evalua la CALIDAD de las respuestas usando RAGAS como framework
y Ollama (llama3.1:8b) como LLM juez via LangchainLLMWrapper.

Metricas evaluadas (reference-free — no requieren respuestas esperadas):
    - faithfulness       — la respuesta esta soportada por los chunks recuperados
    - answer_relevancy   — la respuesta es pertinente a la pregunta

Thresholds:
    - faithfulness      >= 0.7
    - answer_relevancy  >= 0.7

IMPORTANTE — este archivo NO corre con el suite normal de nivel 1.
Cada evaluacion hace llamadas reales al LLM y al LLM juez (lento).

Correr:
    # Solo evaluacion RAG
    pytest tests/test_rag_eval.py -v -s

    # Suite completa nivel 1 (excluye este archivo)
    pytest tests/ -v --ignore=tests/test_rag_eval.py

Requisitos:
    pip install -r requirements-dev.txt
    Ollama corriendo con llama3.1:8b disponible
"""

import os
import sys
import pytest
from datasets import Dataset
from ragas import evaluate, RunConfig
from ragas.metrics import faithfulness, answer_relevancy
from ragas.llms import LangchainLLMWrapper
from ragas.embeddings import LangchainEmbeddingsWrapper
from langchain_ollama import ChatOllama, OllamaEmbeddings

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.rag_chain import responder, limpiar_historial

# ── Configuracion ─────────────────────────────────────────────────────────────

OLLAMA_HOST     = os.getenv("OLLAMA_HOST", "ollama")
OLLAMA_PORT     = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_BASE_URL = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}"

# Thresholds — ajustar tras la primera corrida si son demasiado estrictos
THRESHOLD_FAITHFULNESS      = 0.7
THRESHOLD_ANSWER_RELEVANCY  = 0.7

# ── LLM juez ──────────────────────────────────────────────────────────────────

def _get_run_config() -> RunConfig:
    """
    Configuracion de ejecucion para RAGAS.
    max_workers=1: deshabilita el paralelismo — Ollama sin GPU no puede
                   responder multiples requests simultaneos sin timeout.
    timeout=180:   3 minutos por evaluacion individual.
    """
    return RunConfig(max_workers=1, timeout=180)


def _get_evaluator_llm():
    """LLM juez para RAGAS — llama3.1:8b via Ollama con LangchainLLMWrapper."""
    llm = ChatOllama(
        model="llama3.1:8b",
        base_url=OLLAMA_BASE_URL,
        timeout=180,
    )
    return LangchainLLMWrapper(llm)


def _get_evaluator_embeddings():
    """Embeddings para RAGAS — nomic-embed-text via Ollama."""
    embeddings = OllamaEmbeddings(
        model="nomic-embed-text",
        base_url=OLLAMA_BASE_URL,
    )
    return LangchainEmbeddingsWrapper(embeddings)


# ── Golden dataset ─────────────────────────────────────────────────────────────
# Fuentes verificadas contra ChromaDB — Mayo 2026:
#   decisiones_tecnicas (12), experiencia_y_perfil (8), flextech (3),
#   lineup (11), objetivos_profesionales (10), preferencias (10),
#   tecnologias (21), that_day_london (13), whatsapp_booking_bot (19)

GOLDEN_DATASET = [
    # Proyectos tecnicos
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
    # Stack y tecnologias
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
    # Experiencia laboral
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
    # Orientacion profesional
    {
        "id": "orientacion_futuro",
        "pregunta": "¿a dónde querés ir profesionalmente?",
        "chunks_esperados": ["objetivos_profesionales"],
    },
    # Perfil general
    {
        "id": "perfil_general",
        "pregunta": "contame sobre vos",
        "chunks_esperados": ["experiencia_y_perfil"],
    },
    # Decisiones tecnicas
    {
        "id": "decisiones_arquitectura",
        "pregunta": "¿por qué usaste ChromaDB en contenedor separado en el rag_bot?",
        "chunks_esperados": ["decisiones_tecnicas"],
    },
]

# ── Helper ────────────────────────────────────────────────────────────────────

def _evaluar_pregunta(caso: dict) -> dict:
    """
    Llama a responder() con include_contexts=True.
    Retorna el dict listo para RAGAS.
    Falla el test si la respuesta fue bloqueada (no deberia en el golden dataset).
    Skipea si ChromaDB no devolvio contexto.
    """
    limpiar_historial()
    resultado = responder(caso["pregunta"], include_contexts=True)

    if resultado["blocked"]:
        pytest.fail(
            f"[{caso['id']}] Pregunta bloqueada — no deberia estar en el dataset: "
            f"'{caso['pregunta']}'"
        )

    contexts = resultado.get("contexts", [])
    if not contexts:
        pytest.skip(
            f"[{caso['id']}] Sin contexto — ChromaDB no devolvio chunks para: "
            f"'{caso['pregunta']}'"
        )

    return {
        "question": caso["pregunta"],
        "answer":   resultado["answer"],
        "contexts": contexts,
    }


# ── Tests por metrica ─────────────────────────────────────────────────────────

def _extraer_score(resultado, key):
    """
    Extrae el score numerico del resultado de RAGAS.
    RAGAS 0.2.x puede devolver float o lista segun el numero de muestras.
    Retorna None si todas las evaluaciones fallaron por timeout.
    """
    val = resultado[key]
    if isinstance(val, list):
        vals = [v for v in val if v is not None]
        return sum(vals) / len(vals) if vals else None
    return val if val is not None else None


@pytest.mark.parametrize("caso", GOLDEN_DATASET, ids=[c["id"] for c in GOLDEN_DATASET])
def test_faithfulness(caso):
    """La respuesta esta soportada por los chunks recuperados — sin alucinaciones."""
    muestra = _evaluar_pregunta(caso)
    dataset = Dataset.from_list([muestra])

    resultado = evaluate(
        dataset,
        metrics=[faithfulness],
        llm=_get_evaluator_llm(),
        embeddings=_get_evaluator_embeddings(),
        run_config=_get_run_config(),
        raise_exceptions=False,
    )

    score = _extraer_score(resultado, "faithfulness")

    if score is None:
        pytest.skip(f"[{caso['id']}] Timeout en evaluacion — reintentar")

    print(f"\n[{caso['id']}] faithfulness: {score:.3f}  (threshold: {THRESHOLD_FAITHFULNESS})")
    print(f"  Respuesta: {muestra['answer'][:150]}...")

    assert score >= THRESHOLD_FAITHFULNESS, (
        f"[{caso['id']}] Faithfulness bajo: {score:.3f}\n"
        f"Pregunta:  {caso['pregunta']}\n"
        f"Respuesta: {muestra['answer'][:300]}"
    )


@pytest.mark.parametrize("caso", GOLDEN_DATASET, ids=[c["id"] for c in GOLDEN_DATASET])
def test_answer_relevancy(caso):
    """La respuesta es pertinente a la pregunta."""
    muestra = _evaluar_pregunta(caso)
    dataset = Dataset.from_list([muestra])

    resultado = evaluate(
        dataset,
        metrics=[answer_relevancy],
        llm=_get_evaluator_llm(),
        embeddings=_get_evaluator_embeddings(),
        run_config=_get_run_config(),
        raise_exceptions=False,
    )

    score = _extraer_score(resultado, "answer_relevancy")

    if score is None:
        pytest.skip(f"[{caso['id']}] Timeout en evaluacion — reintentar")

    print(f"\n[{caso['id']}] answer_relevancy: {score:.3f}  (threshold: {THRESHOLD_ANSWER_RELEVANCY})")

    assert score >= THRESHOLD_ANSWER_RELEVANCY, (
        f"[{caso['id']}] Answer relevancy bajo: {score:.3f}\n"
        f"Pregunta:  {caso['pregunta']}\n"
        f"Respuesta: {muestra['answer'][:300]}"
    )



def test_resumen_dataset_completo():
    """
    Corre todas las preguntas del golden dataset de una vez y muestra
    scores promedio por metrica. No hace assert — es informativo.
    Util para calibrar thresholds en la primera corrida.

    Correr solo este test:
        pytest tests/test_rag_eval.py::test_resumen_dataset_completo -v -s
    """
    muestras = []

    for caso in GOLDEN_DATASET:
        limpiar_historial()
        resultado = responder(caso["pregunta"], include_contexts=True)
        if resultado["blocked"] or not resultado.get("contexts"):
            print(f"[SKIP] {caso['id']} — bloqueado o sin contexto")
            continue
        muestras.append({
            "question": caso["pregunta"],
            "answer":   resultado["answer"],
            "contexts": resultado["contexts"],
        })

    if not muestras:
        pytest.skip("Ninguna pregunta genero contexto")

    dataset  = Dataset.from_list(muestras)
    resultado = evaluate(
        dataset,
        metrics=[faithfulness, answer_relevancy],
        llm=_get_evaluator_llm(),
        embeddings=_get_evaluator_embeddings(),
        run_config=_get_run_config(),
        raise_exceptions=False,
    )

    print("\n" + "=" * 60)
    print("RESUMEN — Evaluacion RAG completa")
    print("=" * 60)
    print(f"Preguntas evaluadas : {len(muestras)}/{len(GOLDEN_DATASET)}")
    def _score(key):
        val = resultado[key]
        if isinstance(val, list):
            vals = [v for v in val if v is not None]
            return f"{sum(vals)/len(vals):.3f} ({len(vals)}/{len(val)} ok)" if vals else "N/A (todos timeout)"
        return f"{val:.3f}" if val is not None else "N/A (timeout)"

    print(f"faithfulness        : {_score('faithfulness')}  (threshold: {THRESHOLD_FAITHFULNESS})")
    print(f"answer_relevancy    : {_score('answer_relevancy')}  (threshold: {THRESHOLD_ANSWER_RELEVANCY})")
    print("=" * 60)
    # Sin assert — informativo para calibracion de thresholds