# RAG Personal — Arquitectura
## Gastón Blanco · gaston_rag

> **Documento vivo.** Se actualiza durante el desarrollo.
> Última actualización: Fase 2 completada — Mayo 2026

---

## Índice

1. [Visión general](#1-vision-general)
2. [Stack tecnológico](#2-stack-tecnologico)
3. [Modelo](#3-modelo) → detalle en `docs/MODELO.md`
4. [Fuentes de datos](#4-fuentes-de-datos) → detalle en `docs/FUENTES.md`
5. [Seguridad](#5-seguridad) → detalle en `docs/SEGURIDAD.md`
6. [Infraestructura y deploy](#6-infraestructura-y-deploy) → detalle en `docs/INFRAESTRUCTURA.md`
7. [Puntos de extensión futura](#7-puntos-de-extension-futura)
8. [Historial de decisiones](#8-historial-de-decisiones)

---

## 1. Visión general

Sistema RAG que responde preguntas sobre el perfil profesional de Gastón Blanco
consultando tres fuentes de datos complementarias.

**Principio de diseño central:**
No duplicar datos que ya existen con API. ChromaDB guarda solo lo que no existe
en ningún otro lado — narrativa, contexto, decisiones, orientación profesional.

**Flujo de una query:**
```
Pregunta
   │
   ▼
Router (clasificador de intent)
   │
   ├── ChromaDB (siempre)
   ├── GitHub API (si pregunta sobre proyectos/repos)
   └── HuggingFace API (si pregunta sobre modelos)
   │
   ▼
Construcción de contexto unificado
   │
   ▼
Nodo de modelo (Ollama local — phi3:mini)
   │
   ▼
Respuesta + fuentes consultadas
```

**Estado actual:** Fase 2 completada — 87 chunks en ChromaDB, API levantada.

---

## 2. Stack tecnológico

| Componente | Tecnología | Versión fija |
|---|---|---|
| Lenguaje | Python | 3.11 |
| API framework | FastAPI | 0.115.12 |
| ASGI server | Uvicorn | 0.34.0 |
| Base vectorial | ChromaDB | 0.6.3 |
| LangChain core | langchain | 0.3.22 |
| LangChain Chroma | langchain-chroma | 0.2.2 |
| LangChain Ollama | langchain-ollama | 0.2.3 |
| LangChain splitters | langchain-text-splitters | 0.3.7 |
| Embeddings | nomic-embed-text via Ollama | — |
| LLM | phi3:mini via Ollama | — |
| Conector GitHub | PyGithub | 2.6.1 |
| Conector HuggingFace | huggingface-hub | 0.30.2 |
| Rate limiting | slowapi | 0.1.9 |
| Variables de entorno | python-dotenv | 1.1.0 |

---

## 3. Modelo

Nodo de modelo local — Ollama corre `phi3:mini` sin dependencias externas ni costo por token.
El prompt, los parámetros de retrieval y el router de intents se documentan en detalle en:

→ **`docs/MODELO.md`**

---

## 4. Fuentes de datos

Tres fuentes complementarias. ChromaDB guarda la narrativa propia.
GitHub y HuggingFace se consultan en tiempo real via API.
LinkedIn excluido — sus datos entran manualmente por ChromaDB.

→ **`docs/FUENTES.md`**

---

## 5. Seguridad

Tokens externos, exposición del endpoint, datos sensibles, rate limiting.

→ **`docs/SEGURIDAD.md`**

---

## 6. Infraestructura y deploy

Tres contenedores Docker, dos volúmenes persistentes, red interna.

→ **`docs/INFRAESTRUCTURA.md`**

---

## 7. Puntos de extensión futura

| Extensión | Prerequisito |
|---|---|
| Chat UI | Fase 6 completa |
| Memoria de conversación con ventana deslizante | Definir estrategia de limpieza |
| Router LLM-based | Fase 4 en producción con casos fallando |
| Re-ingesta automática vía GitHub webhook | Fase 3 estable |
| Autenticación en endpoint público | Si se expone con datos más sensibles |

---

## 8. Historial de decisiones

| Fecha | Decisión | Alternativa descartada | Razón |
|---|---|---|---|
| Inicio | ChromaDB en contenedor separado | ChromaDB embedded en API | Datos persisten independiente del ciclo de vida de la API |
| Inicio | nomic-embed-text via Ollama | APIs externas de embeddings | Sin costo, sin dependencia externa, privacidad |
| Inicio | LinkedIn excluido | Scraping | Términos de servicio — datos van a ChromaDB manual |
| Inicio | GitHub + HF como fuentes en tiempo real | Duplicar en ChromaDB | No duplicar datos que ya tienen API |
| Inicio | Todo el proyecto en Docker | Instalación directa | Aislamiento, fácil deploy y rollback |
| Inicio | Versiones fijas en requirements y Docker | latest | Seguridad y reproducibilidad |
| Inicio | docs/ para detalle, ARQUITECTURA.md como índice | Un solo documento largo | Fácil de mantener, cada tema actualizable por separado |
| Fase 1 | Ollama nativo en Windows + contenedor sin límite de RAM | Imagen Docker de Ollama con límites | La imagen Docker fallaba por timeout en descarga — Ollama nativo resolvió el problema |
| Fase 1 | phi3:mini como LLM local | DeepSeek API, Anthropic API | Sin costo por token, sin dependencia externa, corre en el servidor |
| Fase 2 | Ingesta incremental por hash MD5 | Re-ingestar siempre | Eficiencia — solo procesa archivos que cambiaron |