# INFRAESTRUCTURA.md
## RAG Personal · Gastón Blanco

> Detalle del servidor, contenedores Docker, volúmenes y comandos de operación.
> Actualizar cuando cambie el servidor o se modifique la arquitectura de contenedores.

---

## Índice

1. [Servidor](#1-servidor)
2. [Arquitectura Docker](#2-arquitectura-docker)
3. [Volúmenes persistentes](#3-volumenes-persistentes)
4. [Red interna](#4-red-interna)
5. [Budget de RAM](#5-budget-de-ram)
6. [Comandos de operación](#6-comandos-de-operacion)
7. [Antes del primer deploy](#7-antes-del-primer-deploy)

---

## 1. Servidor

**Donweb VPS**

| Recurso | Disponible |
|---|---|
| vCPU | 2 Standard |
| RAM | 4 GB |
| Storage | 10 GB SSD |
| Transferencia | 1 TB/mes |

**Servicios existentes corriendo:**
- WhatsApp Bot (Flask) — Docker — puerto 5000
- spaCy ML service — Docker — puerto 8000
- Redis — Docker

**Puerto asignado para este proyecto:** 8080

---

## 2. Arquitectura Docker

```
internet → :8080 → gaston-rag-api
                        │ red interna gaston-rag-network
               ┌────────┴────────┐
          chroma:8000      ollama:11434
```

| Contenedor | Imagen | Rol |
|---|---|---|
| gaston-rag-api | build local | FastAPI + LangChain |
| gaston-rag-chroma | chromadb/chroma:0.6.3 | Base vectorial |
| gaston-rag-ollama | ollama/ollama:0.6.8 | Embeddings (nomic-embed-text) |

**Nota producción:** Ollama solo sirve embeddings.
El LLM corre en HuggingFace Inference API — sin carga local.

---

## 3. Volúmenes persistentes

| Volumen | Contenedor | Qué guarda |
|---|---|---|
| `chroma_data` | chroma | Knowledge base vectorial |
| `ollama_models` | ollama | nomic-embed-text (~274 MB) |

`docker compose down` baja los contenedores pero **no toca los volúmenes**.
`docker compose down -v` borra todo — usar solo para empezar de cero.

---

## 4. Red interna

Todos los contenedores en `gaston-rag-network`.
ChromaDB y Ollama sin puertos públicos — solo accesibles desde la API.

---

## 5. Budget de RAM

| Servicio | RAM estimada |
|---|---|
| WhatsApp Bot + spaCy (existente) | ~1.2 GB |
| gaston-rag-api | ~300 MB |
| gaston-rag-chroma | ~150 MB |
| gaston-rag-ollama (solo embeddings) | ~400 MB |
| SO + overhead | ~400 MB |
| **Total estimado** | **~2.45 GB** |

---

## 6. Comandos de operación

```bash
# Levantar todo
docker compose -f docker/docker-compose.yml up -d

# Bajar todo (datos persisten)
docker compose -f docker/docker-compose.yml down

# Bajar todo y borrar datos
docker compose -f docker/docker-compose.yml down -v

# Ver logs en tiempo real
docker compose -f docker/docker-compose.yml logs -f api

# Reiniciar solo la API
docker compose -f docker/docker-compose.yml restart api

# Re-ingestar knowledge base
docker compose -f docker/docker-compose.yml exec api python scripts/ingest.py

# Verificar provider activo
docker compose -f docker/docker-compose.yml exec api python -c \
  "import os; from dotenv import load_dotenv; load_dotenv('/app/.env'); \
  print('MODEL_PROVIDER:', os.getenv('MODEL_PROVIDER'))"

# Chat de QA
docker compose -f docker/docker-compose.yml exec -it api python scripts/chat.py \
  --key TU_API_KEY --url http://localhost:8000
```

---

## 7. Antes del primer deploy en Donweb

```bash
# Verificar RAM disponible
free -h

# Ver consumo de servicios existentes
docker stats --no-stream

# Ver puertos ocupados
ss -tlnp | grep LISTEN
```

**Variables requeridas en `.env` de producción:**

```env
# Provider
MODEL_PROVIDER=huggingface
HF_INFERENCE_MODEL=meta-llama/Llama-3.1-8B-Instruct
HF_TOKEN=hf_...

# Conectores
GITHUB_TOKEN=github_...
GITHUB_USERNAME=gaxoblanco
HF_USERNAME=gaxoblanco

# ChromaDB
CHROMA_HOST=chroma
CHROMA_PORT=8000

# Ollama (solo embeddings)
OLLAMA_HOST=ollama
OLLAMA_PORT=11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# Seguridad
GASTON_RAG_API_KEY=...

# Retrieval (opcionales — tienen defaults)
RETRIEVAL_K=8
RETRIEVAL_FETCH_K=30
RETRIEVAL_LAMBDA=0.6
```