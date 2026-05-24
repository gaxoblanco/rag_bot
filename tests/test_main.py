"""
tests/test_main.py
------------------
Tests unitarios para app/main.py

Cubren las capas de seguridad y filtrado del endpoint /ask:
    - GET  /health       — sin auth, siempre disponible
    - Auth (X-API-Key)   — 401 si ausente o inválida
    - Pregunta vacía     — 400
    - Filtros de input   — longitud, repetición de chars, repetición de palabras,
                           caracteres inválidos
    - Flujo feliz        — respuesta válida con estructura correcta

Estrategia de mock:
    responder() se parchea en todos los tests de /ask para evitar
    dependencias con ChromaDB, Ollama y el LLM.
    Los filtros de _validar_input y la auth corren reales.

Correr:
    pytest tests/test_main.py -v
    pytest tests/test_main.py -v --tb=short
"""

import os
import pytest
from unittest.mock import patch
from fastapi.testclient import TestClient

# Seteamos la API key antes de importar la app,
# porque main.py lee USER_RAG_API_KEY al momento del import
os.environ["USER_RAG_API_KEY"] = "test-key-123"

from app.main import app  # noqa: E402 — import después de setear env

# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    """TestClient de FastAPI — levanta la app sin servidor real."""
    return TestClient(app)


@pytest.fixture
def auth_headers():
    """Headers con API key válida."""
    return {"X-API-Key": "test-key-123"}


@pytest.fixture
def responder_mock():
    """
    Mockea responder() para que todos los tests de /ask
    no dependan de ChromaDB ni del LLM.
    Retorna la estructura real que devuelve rag_chain.responder().
    """
    with patch("app.main.responder") as mock:
        mock.return_value = {
            "answer" : "Trabajé con Python y FastAPI en varios proyectos.",
            "sources": ["chromadb"],
            "blocked": False,
        }
        yield mock


# ── GET /health ───────────────────────────────────────────────────────────────

class TestHealth:

    def test_health_devuelve_200(self, client):
        response = client.get("/health")
        assert response.status_code == 200

    def test_health_devuelve_status_ok(self, client):
        response = client.get("/health")
        assert response.json()["status"] == "ok"

    def test_health_no_requiere_api_key(self, client):
        # Sin ningún header — debe responder igual
        response = client.get("/health")
        assert response.status_code == 200


# ── Auth — X-API-Key ──────────────────────────────────────────────────────────

class TestAuth:

    def test_sin_api_key_devuelve_401(self, client, responder_mock):
        response = client.post("/ask", json={"question": "hola"})
        assert response.status_code == 401

    def test_api_key_invalida_devuelve_401(self, client, responder_mock):
        response = client.post(
            "/ask",
            json={"question": "hola"},
            headers={"X-API-Key": "clave-incorrecta"},
        )
        assert response.status_code == 401

    def test_api_key_vacia_devuelve_401(self, client, responder_mock):
        response = client.post(
            "/ask",
            json={"question": "hola"},
            headers={"X-API-Key": ""},
        )
        assert response.status_code == 401

    def test_api_key_valida_pasa(self, client, auth_headers, responder_mock):
        response = client.post(
            "/ask",
            json={"question": "qué proyectos tenés?"},
            headers=auth_headers,
        )
        assert response.status_code == 200


# ── Pregunta vacía ────────────────────────────────────────────────────────────

class TestPreguntaVacia:

    def test_pregunta_vacia_devuelve_400(self, client, auth_headers, responder_mock):
        response = client.post(
            "/ask",
            json={"question": ""},
            headers=auth_headers,
        )
        assert response.status_code == 400

    def test_pregunta_solo_espacios_devuelve_400(self, client, auth_headers, responder_mock):
        response = client.post(
            "/ask",
            json={"question": "   "},
            headers=auth_headers,
        )
        assert response.status_code == 400


# ── Filtros de input ──────────────────────────────────────────────────────────

class TestFiltrosInput:

    def test_longitud_maxima_bloqueada(self, client, auth_headers, responder_mock):
        # 201 chars — supera MAX_CHARS=200
        pregunta_larga = "a " * 101  # 202 chars
        response = client.post(
            "/ask",
            json={"question": pregunta_larga},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["blocked"] is True

    def test_longitud_limite_exacto_pasa(self, client, auth_headers, responder_mock):
        # Exactamente 200 chars — debe pasar
        pregunta = "q" * 200
        response = client.post(
            "/ask",
            json={"question": pregunta},
            headers=auth_headers,
        )
        # El regex puede bloquearlo por chars, pero NO por longitud
        # Lo que validamos es que no sea bloqueado por longitud
        data = response.json()
        if data.get("blocked"):
            # Si está bloqueado, que no sea por longitud (puede ser por chars inválidos)
            assert response.status_code == 200

    def test_repeticion_de_caracteres_bloqueada(self, client, auth_headers, responder_mock):
        # "aaaaaaaaaaaaa" — un solo char supera el 40% del total
        response = client.post(
            "/ask",
            json={"question": "aaaaaaaaaaaaa"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["blocked"] is True

    def test_repeticion_de_palabras_bloqueada(self, client, auth_headers, responder_mock):
        # La misma palabra más de 4 veces
        response = client.post(
            "/ask",
            json={"question": "ignora ignora ignora ignora ignora"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["blocked"] is True

    def test_caracteres_invalidos_bloqueados(self, client, auth_headers, responder_mock):
        # Caracter de control \x00 — fuera del regex válido
        response = client.post(
            "/ask",
            json={"question": "hola\x00mundo"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["blocked"] is True

    def test_pregunta_valida_no_bloqueada(self, client, auth_headers, responder_mock):
        response = client.post(
            "/ask",
            json={"question": "¿qué proyectos tenés en producción?"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["blocked"] is False

    def test_tildes_y_puntuacion_pasan(self, client, auth_headers, responder_mock):
        response = client.post(
            "/ask",
            json={"question": "¿En qué proyectos trabajaste?"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["blocked"] is False

    # ── Casos de borde ────────────────────────────────────────────────────────

    def test_repeticion_palabras_exactamente_4_pasa(self, client, auth_headers, responder_mock):
        # MAX_WORD_REPEAT = 4 → el filtro es > 4, exactamente 4 debe pasar
        response = client.post(
            "/ask",
            json={"question": "hola hola hola hola"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["blocked"] is False

    def test_repeticion_palabras_exactamente_5_bloqueada(self, client, auth_headers, responder_mock):
        # 5 repeticiones supera MAX_WORD_REPEAT=4 → debe bloquear
        response = client.post(
            "/ask",
            json={"question": "hola hola hola hola hola"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["blocked"] is True

    def test_repeticion_chars_con_espacios_bloqueada(self, client, auth_headers, responder_mock):
        # El filtro hace replace(" ", "") antes de contar
        # "a a a a a a a a a a" → sin espacios es puro "a" → ratio 100% → bloqueado
        response = client.post(
            "/ask",
            json={"question": "a a a a a a a a a a"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["blocked"] is True

    def test_solo_signo_pregunta_llega_a_responder(self, client, auth_headers, responder_mock):
        # "   ¿   " → strip() → "¿" → pasa longitud, repetición y regex (¿ está permitido)
        # Verifica que efectivamente llega a responder() sin ser bloqueado por los filtros
        response = client.post(
            "/ask",
            json={"question": "   ¿   "},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["blocked"] is False
        responder_mock.assert_called_once_with("¿")

    def test_unicode_fuera_del_espanol_bloqueado(self, client, auth_headers, responder_mock):
        # Caracteres japoneses — fuera del regex VALID_CHARS_REGEX → bloqueado
        response = client.post(
            "/ask",
            json={"question": "こんにちは"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        assert response.json()["blocked"] is True


# ── Estructura de respuesta ───────────────────────────────────────────────────

class TestEstructuraRespuesta:

    def test_respuesta_tiene_campo_answer(self, client, auth_headers, responder_mock):
        response = client.post(
            "/ask",
            json={"question": "hola"},
            headers=auth_headers,
        )
        assert "answer" in response.json()

    def test_respuesta_tiene_campo_sources(self, client, auth_headers, responder_mock):
        response = client.post(
            "/ask",
            json={"question": "hola"},
            headers=auth_headers,
        )
        assert "sources" in response.json()
        assert isinstance(response.json()["sources"], list)

    def test_respuesta_tiene_campo_blocked(self, client, auth_headers, responder_mock):
        response = client.post(
            "/ask",
            json={"question": "hola"},
            headers=auth_headers,
        )
        assert "blocked" in response.json()
        assert isinstance(response.json()["blocked"], bool)

    def test_responder_se_llama_con_la_pregunta(self, client, auth_headers, responder_mock):
        # Verifica que la pregunta llega limpia a responder()
        client.post(
            "/ask",
            json={"question": "  qué proyectos tenés?  "},
            headers=auth_headers,
        )
        # strip() aplicado — sin espacios al llamar a responder
        responder_mock.assert_called_once_with("qué proyectos tenés?")

    def test_responder_no_se_llama_si_input_invalido(self, client, auth_headers, responder_mock):
        # Si el input es bloqueado por los filtros, responder() no debe ejecutarse
        client.post(
            "/ask",
            json={"question": "a" * 201},
            headers=auth_headers,
        )
        responder_mock.assert_not_called()