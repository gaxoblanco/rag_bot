# TESTS.md
## RAG Personal · Gastón Blanco

> Estado y referencia de la suite de tests unitarios (Nivel 1).
> Última actualización: Mayo 2026 — Nivel 1 completado, 158/158 passing.

---

## Índice

1. [Resumen ejecutivo](#1-resumen-ejecutivo)
2. [Cómo correr los tests](#2-como-correr)
3. [Cobertura por archivo](#3-cobertura)
4. [Bugs encontrados y corregidos](#4-bugs)
5. [Decisiones de diseño de tests](#5-decisiones)
6. [Configuración del entorno](#6-configuracion)

---

## 1. Resumen ejecutivo

| Archivo | Tests | Estado |
|---|---|---|
| `tests/test_router.py` | 55 | ✅ 55/55 |
| `tests/test_main.py` | 26 | ✅ 26/26 |
| `tests/test_rag_chain.py` | 49 | ✅ 49/49 |
| `tests/test_ingest.py` | 28 | ✅ 28/28 |
| **Total** | **158** | **✅ 158/158** |

**Bugs encontrados durante el proceso: 7**
Todos corregidos antes de cerrar nivel 1.

---

## 2. Cómo correr los tests

```bash
# Suite completa
docker compose -f docker/docker-compose.yml exec api pytest tests/ -v

# Output compacto
docker compose -f docker/docker-compose.yml exec api pytest tests/ -v --tb=short

# Archivo individual
docker compose -f docker/docker-compose.yml exec api pytest tests/test_router.py -v
docker compose -f docker/docker-compose.yml exec api pytest tests/test_main.py -v
docker compose -f docker/docker-compose.yml exec api pytest tests/test_rag_chain.py -v
docker compose -f docker/docker-compose.yml exec api pytest tests/test_ingest.py -v
```

---

## 3. Cobertura por archivo

### `tests/test_router.py` — lógica pura del router

Cubre las 6 funciones públicas de `app/router.py`. Sin mocks — pura lógica sin I/O.

| Clase | Qué testea |
|---|---|
| `TestValidarInput` | Longitud, palabra larga, repetición, chars de control, tildes, string vacío |
| `TestGuardiaEntrada` | Injection/jailbreak ES+EN, case insensitive |
| `TestGuardiaRelevancia` | Off-topic bloqueado, keywords de perfil pasan, variantes con/sin tilde |
| `TestGuardiaSalida` | Respuesta sobre perfil pasa, genérica falla, vacía falla |
| `TestClasificarFuentes` | ChromaDB siempre presente, GitHub y HF por keywords |
| `TestDetectarIntentVisitante` | Recruiter, cliente, neutro, contacto directo |

---

### `tests/test_main.py` — capa HTTP de FastAPI

Cubre `app/main.py`. Usa `TestClient` de FastAPI. `responder()` mockeado para aislar del LLM.

| Clase | Qué testea |
|---|---|
| `TestHealth` | GET /health sin auth, siempre 200 |
| `TestAuth` | X-API-Key ausente/inválida/vacía → 401, válida → 200 |
| `TestPreguntaVacia` | String vacío y solo espacios → 400 |
| `TestFiltrosInput` | Longitud >200, char repetido >40%, palabra repetida >4, chars inválidos, bordes exactos, unicode fuera del español |
| `TestEstructuraRespuesta` | Campos answer/sources/blocked presentes, strip() aplicado, responder() no se llama si input inválido |

**Casos de borde incluidos:**
- Exactamente 4 repeticiones de palabra → pasa / exactamente 5 → bloquea
- `"a a a a a a a a a a"` → el `replace(" ", "")` antes del ratio da 100% → bloquea
- `"   ¿   "` → strip() deja `"¿"`, pasa todos los filtros, llega a `responder()`
- Caracteres japoneses → bloqueados (`\w` reemplazado por `[a-zA-Z0-9_]`)

---

### `tests/test_rag_chain.py` — pipeline RAG completo

Cubre `app/rag_chain.py`. Mockea `PROMPT_TEMPLATE` completo para evitar validación Pydantic del LLM. Conectores mockeados en `app.rag_chain.*` (donde se usan, no donde se definen).

| Clase | Qué testea |
|---|---|
| `TestEstructuraRetorno` | `{answer, sources, blocked}` siempre presentes en todos los caminos |
| `TestSaludo` | Respuesta directa, historial limpio, sin vectorstore |
| `TestGuardiaEntrada` | Injection bloqueada, sin historial, sin sources |
| `TestGuardiaRelevancia` | Off-topic bloqueado, sin LLM |
| `TestInputInvalido` | String largo bloqueado antes de todo |
| `TestContactoDirecto` | CTA sin vectorstore, WhatsApp en respuesta |
| `TestSinContexto` | ChromaDB vacío → respuesta genérica, no bloqueado |
| `TestErrorLLM` | Excepción en LLM → no bloqueado, mensaje de error |
| `TestGuardiaSalida` | LLM genera off-topic → bloqueado / válido → pasa |
| `TestFlujoFeliz` | Camino completo, sources contiene chromadb |
| `TestHistorial` | Se guarda, campos correctos, no se guarda si bloqueado, limpiar_historial |
| `TestHistorialProyectoActivo` | proyecto_activo guardado, None si no hay proyecto, cambio de proyecto resetea |
| `TestHistorialLimite` | Deque nunca supera MAX_HISTORIAL=3, conserva las más recientes |
| `TestGithubFalla` | Excepción en conector → no explota, github no en sources, chromadb sigue |
| `TestGuardiaRelevanciaTildes` | Variantes con/sin tilde de off-topic bloqueadas, de perfil pasan |

**Decisión clave de mock:**
`PROMPT_TEMPLATE` se parchea completo (`patch("app.rag_chain.PROMPT_TEMPLATE", mock_chain)`) para que `chain.invoke()` devuelva strings directamente. Mockear `_get_llm()` falla porque LangChain/Pydantic valida que el output sea un string real.

---

### `tests/test_ingest.py` — ingesta incremental

Cubre `scripts/ingest.py`. Usa `tmp_path` de pytest para archivos temporales. Sin ChromaDB ni Ollama.

| Clase | Qué testea |
|---|---|
| `TestCalcularHash` | MD5 hexadecimal de 32 chars, mismo contenido mismo hash, cambio mínimo cambia hash |
| `TestEstado` | cargar_estado devuelve {} si no existe, lee JSON, guardar_estado crea archivo, ida y vuelta exacta |
| `TestDetectarCambios` | Nuevo, sin cambios, modificado, eliminado, directorio vacío, múltiples archivos, escenario mixto |
| `TestProcesarArchivo` | Vacío retorna [], campos requeridos, tipo por carpeta, tipo "general" para carpeta desconocida, IDs únicos, fuente sin extensión, chunks desde 0 |

---

## 4. Bugs encontrados y corregidos

| # | Archivo | Función | Bug | Fix |
|---|---|---|---|---|
| 1 | `router.py` | `validar_input` | String vacío `""` devolvía `True` | Agregar check `if not texto` al inicio |
| 2 | `router.py` | `guardia_relevancia` | `"política"` con tilde no matcheaba `"politica"` sin tilde en `_OFFTOPIC_SEÑALES` | Agregar `"últimas noticias"` y variantes con tilde |
| 3 | `router.py` | `detectar_intent_visitante` | `"necesito desarrollar"` no detectaba cliente | Agregar variantes `"necesito desarrollar/construir/crear"` a `_CLIENTE_KEYWORDS` |
| 4 | `main.py` | `_validar_input` | `"¿"` solo bloqueado por ratio 1/1 (falso positivo) | Mínimo `total_chars > 5` antes de calcular ratio |
| 5 | `main.py` | `_validar_input` | `\w` en regex permitía unicode genérico (japonés, etc.) | Reemplazar `\w` por `[a-zA-Z0-9_]` |
| 6 | `router.py` | `guardia_relevancia` | `"ia"` matcheaba como substring en `"noticias"`, `"política"` | Separar keywords cortas en `_PERFIL_KEYWORDS_WORD`, chequear con `re.search(r"\b...\b")` |
| 7 | `router.py` | `detectar_intent_visitante` | `"rol"` matcheaba como substring en `"desarrollar"` | Separar `"rol"` en `_RECRUITER_KEYWORDS_WORD`, chequear con `re.search(r"\b...\b")` |

**Patrón común de los bugs 6 y 7:** keywords cortas (2-3 chars) usadas con `in` matchean como substring de palabras más largas. La solución sistemática es `re.search(r"\b" + re.escape(kw) + r"\b", texto)`.

---

## 5. Decisiones de diseño de tests

**Mock de conectores externos:** siempre parchear en el módulo que los usa (`app.rag_chain.get_github_projects`), no donde se definen (`connectors.github_connector.get_github_projects`). La regla de `unittest.mock` es parchear el namespace donde el nombre es buscado.

**Mock del LLM:** no mockear `_get_llm()` directamente — LangChain construye objetos `Generation` con Pydantic y valida que el texto sea un string real. Solución: parchear `PROMPT_TEMPLATE` completo para cortocircuitar toda la chain.

**Estado global de rag_chain:** el historial y los singletons `_vectorstore`/`_llm` son globales. El fixture `limpiar_estado` (autouse=True) los resetea antes y después de cada test para evitar contaminación entre tests.

**Imports después de setear env:** `test_main.py` setea `USER_RAG_API_KEY` antes del import de `app.main` porque `main.py` lee esa variable en el momento del import.

---

## 6. Configuración del entorno

**Dependencias agregadas a `requirements.txt`:**
```
pytest==8.3.5
pytest-asyncio==0.24.0
httpx==0.27.0
```

**Volumen agregado en `docker-compose.yml`:**
```yaml
- ../tests:/app/tests
```

**`tests/conftest.py`** — agrega la raíz del proyecto al path para que los imports funcionen dentro del contenedor:
```python
import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
```

**Warning de pytest-asyncio** — aparece en cada run pero no afecta los tests. Se silencia agregando a `pytest.ini` o `pyproject.toml`:
```ini
[pytest]
asyncio_mode = strict
asyncio_default_fixture_loop_scope = function
```
