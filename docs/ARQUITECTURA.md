# RAG Personal — Arquitectura
## Gastón Blanco · gaston_rag

> **Documento vivo.** Se actualiza durante el desarrollo.
> Última actualización: Fase 6 completada — Mayo 2026

---

## Índice

1. [Visión general](#1-vision-general)
2. [Stack tecnológico](#2-stack-tecnologico)
3. [Modelo](#3-modelo)
4. [Fuentes de datos](#4-fuentes-de-datos)
5. [Seguridad](#5-seguridad)
6. [Infraestructura y deploy](#6-infraestructura-y-deploy)
7. [Puntos de extensión futura](#7-puntos-de-extension-futura)
8. [Historial de decisiones](#8-historial-de-decisiones)

---

## 1. Visión general

Sistema RAG que responde preguntas sobre el perfil profesional de Gastón Blanco.
Objetivo: captar clientes y recruiters desde la landing page personal.

**Flujo de una query:**
```
Pregunta
   │
   ├── Detección de saludo → limpiar historial
   ├── Detección de contacto puro → respuesta directa con CTA
   ├── Detección de intent visitante → recruiter | cliente | neutro
   │
   ▼
Guardia de entrada (bloquea injection/jailbreak — ES + EN)
   │
   ▼
Router de fuentes
   ├── ChromaDB (siempre) — MMR k=8, fetch_k=30, lambda=0.6
   ├── GitHub API (proyectos/repos)
   └── HuggingFace API (modelos/spaces)
   │
   ▼
Construcción de contexto separado
   ├── context_proyecto — query enriquecida con proyecto_activo del historial
   └── context_referencia — GitHub, HuggingFace, chunks generales
   │
   ▼
LLM intercambiable (HuggingFace Inference API / Ollama)
   │
   ▼
Guardia de salida (valida que respuesta sea sobre Gastón)
   │
   ▼
Guardar en historial conversacional (proyecto_activo detectado)
   │
   ▼
Respuesta + CTA según intent del visitante
```

**Estado actual:** Fase 6 completada. Pendiente: deploy en Donweb.

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
| LangChain HuggingFace | langchain-huggingface | 0.1.2 |
| HuggingFace Hub | huggingface-hub | 0.30.2 |
| Embeddings | nomic-embed-text via Ollama | — |
| LLM producción | Llama-3.1-8B via HF Inference API / Novita | — |
| LLM desarrollo | llama3.1:8b via Ollama | — |
| Rate limiting | slowapi | 0.1.9 |
| Variables de entorno | python-dotenv | 1.1.0 |

---

## 3. Modelo

Nodo intercambiable — `MODEL_PROVIDER` en `.env` define el provider sin cambiar código.
Prompt con intención comercial — CTA adaptado según intent del visitante.
Historial conversacional con detección de proyecto activo.

→ **`docs/MODELO.md`**

---

## 4. Fuentes de datos

ChromaDB guarda la narrativa propia (87+ chunks en `data/`).
GitHub y HuggingFace se consultan en tiempo real.

```
data/
├── decisiones/    — decisiones técnicas del proyecto
├── experiencia/   — Flextech, That Day in London
├── orientacion/   — objetivos profesionales
├── perfil/        — experiencia_y_perfil, preferencias
├── proyectos/     — Lineup, WhatsApp Booking Bot
└── stack/         — tecnologías
```

→ **`docs/FUENTES.md`**

---

## 5. Seguridad

- `X-API-Key` header con `secrets.compare_digest` — evita timing attacks
- Rate limit: 20 req/min por IP via slowapi
- Guardia de entrada: injection/jailbreak en ES + EN
- Guardia de salida: valida que respuesta sea sobre el perfil

→ **`docs/SEGURIDAD.md`**

---

## 6. Infraestructura y deploy

Tres contenedores Docker. Ollama solo sirve embeddings en producción.

→ **`docs/INFRAESTRUCTURA.md`**

---

## 7. Puntos de extensión futura

| Extensión | Prerequisito |
|---|---|
| Deploy en Donweb | Fase 6 completa ✅ |
| Integración landing page | Deploy completo |
| Re-ingesta automática vía webhook | Deploy estable |

---

## 8. Historial de decisiones

| Fecha | Decisión | Alternativa descartada | Razón |
|---|---|---|---|
| Inicio | ChromaDB en contenedor separado | ChromaDB embedded | Datos persisten independiente del ciclo de vida de la API |
| Inicio | nomic-embed-text via Ollama | APIs externas | Sin costo, sin dependencia externa |
| Inicio | LinkedIn excluido | Scraping | Términos de servicio |
| Inicio | GitHub + HF en tiempo real | Duplicar en ChromaDB | No duplicar datos que ya tienen API |
| Fase 1 | Ollama nativo en Windows para desarrollo | Imagen Docker de Ollama | Timeout en descarga dentro de Docker |
| Fase 2 | Ingesta incremental por hash MD5 | Re-ingestar siempre | Solo procesa archivos que cambiaron |
| Fase 4 | MMR k=8, fetch_k=30, lambda=0.6 | similarity_search k=4 | that_day_london dominaba resultados |
| Fase 5 | HuggingFace Inference API / Novita | Ollama en VPS sin GPU | VPS sin GPU — ~2s respuesta, sin costo fijo |
| Fase 5 | InferenceClient directo | ChatHuggingFace | ChatHuggingFace descarga tokenizador de modelo gated → 403 |
| Fase 5 | Nodo intercambiable via MODEL_PROVIDER | Provider hardcodeado | Permite cambiar entre HF y Ollama sin refactor |
| Fase 6 | Contextos separados context_proyecto/context_referencia | Contexto único | Evita que preguntas de seguimiento mezclen proyectos |
| Fase 6 | Historial con proyecto_activo | Solo pregunta/respuesta | Enriquece queries ambiguas con proyecto del turno anterior |
| Fase 6 | Detección de intent visitante (recruiter/cliente/neutro) | Prompt único | CTA personalizado según audiencia — objetivo comercial |
| Fase 6 | Respuesta directa para contacto puro | Pasar por LLM | Evita timeouts y bloqueos en preguntas sin keywords técnicas |