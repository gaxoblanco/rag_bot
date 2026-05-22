# RAG Personal — Arquitectura
## Gastón Blanco · gaston_rag

> **Documento vivo.** Se actualiza durante el desarrollo.
> Última actualización: Fase 6 + deploy producción — Mayo 2026

---

## Índice

1. [Visión general](#1-vision-general)
2. [Responsabilidad de cada archivo](#2-responsabilidad-de-cada-archivo)
3. [Stack tecnológico](#3-stack-tecnologico)
4. [Modelo](#4-modelo)
5. [Fuentes de datos](#5-fuentes-de-datos)
6. [Seguridad](#6-seguridad)
7. [Infraestructura y deploy](#7-infraestructura-y-deploy)
8. [Puntos de extensión futura](#8-puntos-de-extension-futura)
9. [Historial de decisiones](#9-historial-de-decisiones)

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
Guardia de relevancia (bloquea preguntas off-topic sin keywords de perfil)
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

**Estado actual:** Fase 6 completada. Deploy en producción — `https://rag.gaxoblanco.com`

---

## 2. Responsabilidad de cada archivo

Cada archivo tiene una responsabilidad clara y no se mete en la del otro.
Cuando algo falla o querés cambiar algo, sabés exactamente dónde ir.

```
scripts/ingest.py   — Setup (se corre una vez o cuando cambian los docs)
                      Lee los .md de data/, los chunkea, los vectoriza
                      con Ollama y los guarda en ChromaDB.
                      Ingesta incremental por hash MD5 — solo procesa
                      archivos nuevos o modificados.

app/main.py         — Puerta de entrada
                      Recibe el HTTP request, valida API key,
                      aplica filtros de input (longitud, repetición,
                      caracteres) y llama a responder().

app/rag_chain.py    — Cerebro / orquestador
                      Coordina todo el flujo de una query:
                      llama al router, construye el contexto,
                      arma el prompt, llama al LLM,
                      guarda el historial conversacional.

app/router.py       — Especialista en decisiones
                      Solo toma decisiones, no ejecuta nada.
                      Responde: ¿es injection? ¿es off-topic?
                      ¿qué fuentes consultar? ¿recruiter o cliente?

app/config.py       — Variables de configuración
                      Centraliza todos los parámetros del sistema.
                      Un solo lugar para ajustar comportamiento.
```

**La regla de dependencias:** `main` llama a `rag_chain`, `rag_chain` llama a `router`.
Nunca al revés. `router` no sabe que existe `rag_chain`.

---

## 3. Stack tecnológico

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

## 4. Modelo

Nodo intercambiable — `MODEL_PROVIDER` en `.env` define el provider sin cambiar código.
Prompt con intención comercial — CTA adaptado según intent del visitante.
Historial conversacional con detección de proyecto activo.

→ **`docs/MODELO.md`**

---

## 5. Fuentes de datos

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

## 6. Seguridad

- `X-API-Key` header con `secrets.compare_digest` — evita timing attacks
- Rate limit: 20 req/min por IP via slowapi
- Guardia de entrada: injection/jailbreak en ES + EN
- Guardia de salida: valida que respuesta sea sobre el perfil

→ **`docs/SEGURIDAD.md`**

---

## 7. Infraestructura y deploy

Tres contenedores Docker. Ollama solo sirve embeddings en producción.

→ **`docs/INFRAESTRUCTURA.md`**

**Estado producción:**
- VPS Donweb — 4GB RAM, Ubuntu 24, `149.50.128.92`
- Nginx reverse proxy → `localhost:8080` (puerto interno, no expuesto)
- SSL Let's Encrypt — certificado automático via certbot snap
- Dominio: `rag.gaxoblanco.com` → registro A apuntando al VPS
- Landing: `gaxoblanco.com` → `chat.js` apunta a `https://rag.gaxoblanco.com`
- Tres contenedores activos: `gaston-rag-api`, `gaston-rag-chroma`, `gaston-rag-ollama`

---

## 8. Puntos de extensión futura

| Extensión | Estado |
|---|---|
| Deploy en Donweb VPS | ✅ Completado — `149.50.128.92` |
| HTTPS con Let's Encrypt | ✅ Completado — `https://rag.gaxoblanco.com` |
| Integración landing page | ✅ Completado — `gaxoblanco.com` |
| Cerrar puerto 8080 con iptables | ✅ Completado — DROP desde exterior, ACCEPT solo 127.0.0.1 |
| Re-ingesta automática vía webhook | ❌ Descartado — knowledge base local, frecuencia de cambio baja |

---

## 9. Historial de decisiones

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
| Deploy | Nginx como reverse proxy | Exponer puerto 8080 directo | HTTPS + puerto interno no expuesto al exterior |
| Deploy | certbot via snap | certbot apt | Versión apt desactualizada en Ubuntu 24 — conflicto de dependencias |
| Deploy | torch CPU-only en Dockerfile | torch default | torch default descarga nvidia_cublas (423MB) innecesario en VPS sin GPU |
| Deploy | guardia_relevancia como capa separada | Ampliar guardia_entrada | Separación de responsabilidades — injection vs off-topic son problemas distintos |