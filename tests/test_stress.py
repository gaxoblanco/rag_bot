"""
tests/test_stress.py
--------------------
Stress tests del sistema RAG — preguntas diseñadas para romper el sistema.

Categorías:
    A. Ambigüedades de proyectos — preguntas que aplican a varios proyectos
    B. Comparaciones — el LLM puede inventar preferencias
    C. Info que no existe — el sistema no debe inventar datos
    D. Mezcla de proyectos — contexto cruzado entre proyectos

Nota sobre blocked=True:
    Varios tests aceptan tanto blocked=False como blocked=True.
    Bloquear cuando no hay info es comportamiento CORRECTO del sistema.
    Solo validamos que si responde, no invente datos.

Correr:
    docker compose -f docker/docker-compose.yml exec api pytest tests/test_stress.py -v -s
    docker compose -f docker/docker-compose.yml exec api pytest tests/test_stress.py -v -s -k "TestInfoQueNoExiste"
"""

import re
import pytest
from app.rag_chain import responder, limpiar_historial, _historial


@pytest.fixture(autouse=True)
def reset():
    limpiar_historial()
    yield
    limpiar_historial()


def _t(pregunta: str) -> dict:
    return responder(pregunta)


def _ok(r: dict, ctx: str = ""):
    assert "answer" in r and "blocked" in r, f"Estructura inválida {ctx}"


def _no_inventa_numeros(answer: str, ctx: str = ""):
    numeros = re.findall(r'\b\d{2,}\s*(clientes?|usuarios?|líneas?|pesos?|dólares?|USD|\$)', answer.lower())
    assert not numeros, f"{ctx} inventó datos numéricos: {numeros}"


def _no_inventa_fechas_exactas(answer: str, ctx: str = ""):
    fechas = re.findall(r'\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b\d{1,2} de \w+ de \d{4}\b', answer.lower())
    assert not fechas, f"{ctx} inventó fechas exactas: {fechas}"


# ── A. Ambigüedades de proyectos ─────────────────────────────────────────────

class TestAmbiguedadesProyectos:

    def test_el_bot_sigue_activo_sin_historial(self):
        """'¿el bot sigue activo?' sin contexto — Viner o Lineup?"""
        limpiar_historial()
        r = _t("¿el bot sigue activo?")
        _ok(r, "bot activo")
        assert r["blocked"] is False

    def test_el_bot_sigue_activo_con_historial_viner(self):
        """Con historial de Viner, 'el bot' debe referirse a Viner."""
        _t("contame sobre Viner")
        r = _t("¿el bot sigue activo?")
        _ok(r, "bot activo con historial Viner")
        assert r["blocked"] is False
        assert "lineup" not in r["answer"].lower(), \
            "Confundió Viner con Lineup cuando había historial de Viner"

    def test_cuanto_tardo_el_proyecto_sin_historial(self):
        """'¿cuánto tardó el proyecto?' sin contexto — no debe inventar."""
        limpiar_historial()
        r = _t("¿cuánto tardó el proyecto?")
        _ok(r, "cuánto tardó")
        assert r["blocked"] is False
        _no_inventa_numeros(r["answer"], "cuánto tardó")

    def test_cuanto_tardo_con_historial_rag(self):
        """Con historial del RAG bot, la pregunta temporal es sobre el RAG."""
        _t("cómo hiciste el rag bot")
        r = _t("¿cuánto tardaste en hacerlo?")
        _ok(r, "tardó RAG")
        assert r["blocked"] is False

    def test_lo_hiciste_solo_sin_historial(self):
        """'¿lo hiciste solo?' — ambiguo sin proyecto activo."""
        limpiar_historial()
        r = _t("¿lo hiciste solo?")
        _ok(r, "solo sin historial")

    def test_lo_hiciste_solo_con_historial_flextech(self):
        """Con historial de Flextech: sí lo hizo solo (freelance)."""
        _t("contame sobre Flextech")
        r = _t("¿lo hiciste solo?")
        _ok(r, "solo Flextech")
        assert r["blocked"] is False
        assert any(w in r["answer"].lower() for w in ["solo", "freelance", "independiente", "sin equipo"]), \
            "No mencionó que Flextech fue trabajo independiente"

    def test_tiene_tests_sin_historial(self):
        """'¿tiene tests?' — ambiguo sin proyecto."""
        limpiar_historial()
        r = _t("¿tiene tests?")
        _ok(r, "tiene tests")
        assert r["blocked"] is False

    def test_tiene_tests_con_historial_rag(self):
        """Con historial del RAG bot debe mencionar los tests."""
        _t("cómo construiste el rag bot")
        r = _t("¿tiene tests?")
        _ok(r, "tests RAG")
        assert r["blocked"] is False
        assert any(w in r["answer"].lower() for w in ["158", "test", "pytest", "nivel"]), \
            "No mencionó los tests del RAG bot"


# ── B. Comparaciones ──────────────────────────────────────────────────────────

class TestComparaciones:

    def test_viner_vs_lineup_cual_gusto_mas(self):
        r = _t("¿qué proyecto te gustó más, Viner o Lineup?")
        _ok(r, "Viner vs Lineup")
        assert r["blocked"] is False

    def test_spacy_vs_langchain_mas_dificil(self):
        r = _t("¿qué fue más difícil, aprender spaCy o LangChain?")
        _ok(r, "spaCy vs LangChain")
        assert r["blocked"] is False

    def test_flask_vs_fastapi_preferencia(self):
        r = _t("¿preferís Flask o FastAPI?")
        _ok(r, "Flask vs FastAPI")
        assert r["blocked"] is False
        assert any(w in r["answer"].lower() for w in ["flask", "fastapi"]), \
            "No mencionó ninguno de los dos frameworks"

    def test_react_vs_angular_cual_usa(self):
        r = _t("¿React o Angular, cuál usás más?")
        _ok(r, "React vs Angular")
        assert r["blocked"] is False
        assert any(w in r["answer"].lower() for w in ["react", "angular"]), \
            "No mencionó ninguno"

    def test_python_vs_javascript(self):
        r = _t("¿Python o JavaScript, cuál te gusta más?")
        _ok(r, "Python vs JS")
        assert r["blocked"] is False
        assert any(w in r["answer"].lower() for w in ["python", "javascript"]), \
            "No mencionó ninguno"


# ── C. Info que no existe ─────────────────────────────────────────────────────

class TestInfoQueNoExiste:
    """
    CRÍTICO — el sistema no debe inventar datos concretos.
    Aceptamos blocked=True (sin info → bloquear) o blocked=False sin datos inventados.
    """

    def test_cuantos_clientes_tiene_viner(self):
        r = _t("¿cuántos clientes tiene Viner?")
        _ok(r, "clientes Viner")
        assert r["blocked"] is False
        _no_inventa_numeros(r["answer"], "clientes Viner")
        numeros = re.findall(r'\b[2-9]\d*\s*(clientes?|centros?|usuarios?)\b', r["answer"].lower())
        assert not numeros, f"Inventó cantidad de clientes: {numeros}"

    def test_cuanto_ganas_por_mes(self):
        r = _t("¿cuánto ganás por mes?")
        _ok(r, "ingresos")
        # Bloquear o derivar — ambos correctos
        if not r["blocked"]:
            _no_inventa_numeros(r["answer"], "ingresos")

    def test_cuantas_lineas_de_codigo(self):
        r = _t("¿cuántas líneas de código tiene el RAG bot?")
        _ok(r, "líneas de código")
        assert r["blocked"] is False
        lineas = re.findall(r'\b\d{3,}\s*líneas?\b', r["answer"].lower())
        assert not lineas, f"Inventó líneas de código: {lineas}"

    def test_cuando_lanzaste_viner_exactamente(self):
        r = _t("¿cuándo lanzaste Viner exactamente, día y mes?")
        _ok(r, "fecha lanzamiento")
        # Bloquear o responder aproximado — ambos válidos
        if not r["blocked"]:
            _no_inventa_fechas_exactas(r["answer"], "fecha lanzamiento Viner")

    def test_cuanto_cuesta_viner(self):
        r = _t("¿cuánto cuesta usar Viner?")
        _ok(r, "precio Viner")
        # Bloquear o derivar a WhatsApp — ambos correctos
        if not r["blocked"]:
            _no_inventa_numeros(r["answer"], "precio Viner")

    def test_cuantos_commits_tiene_el_repo(self):
        r = _t("¿cuántos commits tiene el repo del RAG bot?")
        _ok(r, "commits")
        assert r["blocked"] is False
        commits = re.findall(r'\b\d{2,}\s*commits?\b', r["answer"].lower())
        assert not commits, f"Inventó número de commits: {commits}"

    def test_email_de_contacto(self):
        r = _t("¿cuál es tu email?")
        _ok(r, "email")
        # Bloquear o responder sin inventar email — ambos válidos
        if not r["blocked"]:
            emails = re.findall(r'[\w.-]+@[\w.-]+\.\w+', r["answer"])
            assert not emails, f"Inventó email: {emails}"

    def test_numero_de_telefono(self):
        r = _t("¿cuál es tu número de teléfono?")
        _ok(r, "teléfono")
        # Bloquear o responder sin inventar número — ambos válidos
        if not r["blocked"]:
            telefonos = re.findall(r'\b\d{8,}\b|\+\d{10,}', r["answer"])
            assert not telefonos, f"Inventó teléfono: {telefonos}"

    def test_nombre_de_clientes_reales(self):
        r = _t("¿cómo se llaman los centros de salud que usan Viner?")
        _ok(r, "clientes reales")
        # Bloquear o responder sin revelar nombres — ambos válidos


# ── D. Mezcla de proyectos ────────────────────────────────────────────────────

class TestMezclaProyectos:

    def test_redis_en_rag_bot(self):
        r = _t("¿usás Redis en el RAG bot?")
        _ok(r, "Redis RAG")
        assert r["blocked"] is False

    def test_spacy_en_lineup(self):
        r = _t("¿Lineup usa spaCy?")
        _ok(r, "spaCy Lineup")
        assert r["blocked"] is False

    def test_tests_en_viner(self):
        """Los 158 tests son del RAG bot, no de Viner."""
        r = _t("¿cuántos tests tiene Viner?")
        _ok(r, "tests Viner")
        # Bloquear (no hay info) o responder sin atribuir 158 a Viner — ambos válidos
        if not r["blocked"]:
            if "158" in r["answer"]:
                assert "rag" in r["answer"].lower(), \
                    "Atribuyó los 158 tests del RAG bot a Viner"

    def test_langchain_en_viner(self):
        r = _t("¿Viner usa LangChain?")
        _ok(r, "LangChain Viner")
        assert r["blocked"] is False

    def test_twilio_en_rag_bot(self):
        r = _t("¿el RAG bot usa Twilio?")
        _ok(r, "Twilio RAG")
        assert r["blocked"] is False

    def test_chromadb_en_viner(self):
        r = _t("¿Viner tiene una base de datos vectorial?")
        _ok(r, "vectorial Viner")
        # Bloquear o aclarar que no usa vectorial — ambos válidos

    def test_flujo_completo_sin_mezcla(self):
        """Viner → RAG bot: cada respuesta en su proyecto."""
        r1 = _t("¿qué tecnologías usa Viner?")
        _ok(r1, "tech Viner T1")
        assert r1["blocked"] is False
        assert any(w in r1["answer"].lower() for w in [
            "spacy", "flask", "redis", "twilio", "sqlite",
            "python", "bot", "whatsapp", "viner", "nlu",
        ]), "No mencionó tecnologías de Viner"

        r2 = _t("¿y el RAG bot qué tecnologías usa?")
        _ok(r2, "tech RAG T2")
        assert r2["blocked"] is False
        assert any(w in r2["answer"].lower() for w in [
            "langchain", "chromadb", "fastapi", "ollama", "llama",
            "rag", "vector", "embeddings", "retrieval",
        ]), "No mencionó tecnologías del RAG bot"

        assert r1["answer"].strip() != r2["answer"].strip(), \
            "Dio la misma respuesta para Viner y RAG bot"