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
- WhatsApp Bot (Flask) — Docker
- spaCy ML service — Docker

---

## 2. Arquitectura Docker

Tres contenedores coordinados por `docker-compose.yml`.
La API es el único punto de entrada desde el exterior.

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
| gaston-rag-ollama | ollama/ollama:0.6.8 | Embeddings (+ LLM local futuro) |

---

## 3. Volúmenes persistentes

| Volumen | Contenedor | Qué guarda |
|---|---|---|
| `chroma_data` | chroma | Knowledge base vectorial |
| `ollama_models` | ollama | Modelos descargados |

`docker compose down` baja los contenedores pero **no toca los volúmenes**.
Para borrar datos: `docker compose down -v` — usar solo si se quiere empezar de cero.

---

## 4. Red interna

Todos los contenedores del proyecto en `gaston-rag-network`.
ChromaDB y Ollama no tienen puertos públicos — solo accesibles desde la API internamente.

---

## 5. Budget de RAM

| Servicio | RAM estimada | Límite Docker |
|---|---|---|
| WhatsApp Bot + spaCy (existente) | ~1.2 GB | — |
| gaston-rag-api | ~300 MB | 512 MB |
| gaston-rag-chroma | ~150 MB | 256 MB |
| gaston-rag-ollama (solo embeddings) | ~400 MB | 768 MB |
| SO + overhead | ~400 MB | — |
| **Total estimado** | **~2.45 GB** | dentro de 4 GB |

⚠️ Verificar baseline real antes del primer deploy — ver sección 7.

---

## 6. Comandos de operación

```bash
# Levantar todo
docker compose up -d

# Bajar todo (los datos persisten)
docker compose down

# Bajar todo y borrar datos — CUIDADO
docker compose down -v

# Ver logs en tiempo real
docker compose logs -f api
docker compose logs -f chroma

# Reiniciar solo la API (sin tocar datos)
docker compose restart api

# Ver uso de recursos
docker stats

# Bajar el modelo de embeddings (primera vez)
docker exec gaston-rag-ollama ollama pull nomic-embed-text

# Re-ingestar knowledge base
docker exec gaston-rag-api python scripts/ingest.py
```

---

## 7. Antes del primer deploy

Correr en el servidor con los servicios existentes activos:

```bash
# Ver RAM disponible real
free -h

# Ver consumo de los servicios existentes
docker stats --no-stream

# Ver puertos ocupados
ss -tlnp | grep LISTEN
```

Verificar que el puerto 8080 esté libre antes de levantar la API.
Si el RAM disponible es menor a 2 GB libres, reducir el límite de ollama
o migrar al modelo TinyLlama 1.1B (~600MB) en lugar de nomic-embed-text.
