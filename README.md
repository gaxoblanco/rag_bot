# rag_bot

Personal RAG system built with LangChain, ChromaDB and HuggingFace Inference API — conversational AI over custom knowledge base.

---

## What it does

Answers natural language questions by retrieving relevant chunks from a vector database and generating responses with a language model. Supports multiple data sources, conversational memory, and intent-based routing.

---

## Architecture

```
Question
   │
   ├── Greeting detection → clear history
   ├── Contact intent detection → direct CTA response
   ├── Visitor intent → recruiter | client | neutral
   │
   ▼
Entry guard (injection / jailbreak detection — ES + EN)
   │
   ▼
Source router
   ├── ChromaDB (always) — MMR retrieval k=8
   ├── GitHub API (if project-related question)
   └── HuggingFace API (if model-related question)
   │
   ▼
Dual context construction
   ├── context_project  — active project chunks (enriched query)
   └── context_reference — general profile, GitHub, HuggingFace
   │
   ▼
LLM (swappable: HuggingFace Inference API or Ollama)
   │
   ▼
Exit guard (validates response relevance)
   │
   ▼
Response + conversational history update
```

---

## Stack

| Component | Technology |
|---|---|
| Language | Python 3.11 |
| API | FastAPI + Uvicorn |
| Vector DB | ChromaDB 0.6.3 |
| Orchestration | LangChain 0.3.22 |
| Embeddings | nomic-embed-text via Ollama |
| LLM (production) | Llama 3.1 8B via HuggingFace Inference API / Novita |
| LLM (development) | llama3.1:8b via Ollama |
| Connectors | GitHub GraphQL API, HuggingFace Hub |
| Rate limiting | slowapi |
| Infra | Docker + Docker Compose |

---

## Project structure

```
rag_bot/
├── app/
│   ├── config.py          — centralized env vars
│   ├── main.py            — FastAPI endpoints
│   ├── rag_chain.py       — RAG pipeline + conversational memory
│   └── router.py          — intent classification + security guards
├── connectors/
│   ├── github_connector.py
│   └── huggingface_connector.py
├── data/                  — knowledge base (markdown files)
│   ├── decisiones/
│   ├── experiencia/
│   ├── orientacion/
│   ├── perfil/
│   ├── proyectos/
│   └── stack/
├── scripts/
│   ├── ingest.py          — incremental ingestion with MD5 check
│   ├── chat.py            — QA interactive chat (CLI)
│   └── test_similarity.py
├── docker/
│   ├── docker-compose.yml
│   └── Dockerfile
└── docs/
    ├── ARQUITECTURA.md
    ├── MODELO.md
    ├── INFRAESTRUCTURA.md
    ├── FUENTES.md
    └── SEGURIDAD.md
```

---

## Local setup

**Requirements:** Docker Desktop, Git.

```bash
# 1. Clone the repo
git clone https://github.com/gaxoblanco/rag_bot.git
cd rag_bot

# 2. Copy and fill the env file
cp .env.example .env

# 3. Start all services
docker compose -f docker/docker-compose.yml up -d

# 4. Ingest the knowledge base (runs automatically on API start)
docker compose -f docker/docker-compose.yml exec api python scripts/ingest.py
```

---

## Environment variables

```env
# LLM provider — "huggingface" | "ollama"
MODEL_PROVIDER=huggingface
HF_INFERENCE_MODEL=meta-llama/Llama-3.1-8B-Instruct
HF_TOKEN=hf_...

# External connectors
GITHUB_TOKEN=github_...
GITHUB_USERNAME=your_username
HF_USERNAME=your_username

# ChromaDB
CHROMA_HOST=chroma
CHROMA_PORT=8000

# Ollama (embeddings)
OLLAMA_HOST=ollama
OLLAMA_PORT=11434
OLLAMA_EMBEDDING_MODEL=nomic-embed-text

# API security
GASTON_RAG_API_KEY=your_secret_key

# Retrieval tuning (optional — defaults shown)
RETRIEVAL_K=8
RETRIEVAL_FETCH_K=30
RETRIEVAL_LAMBDA=0.6
```

---

## API

```
GET  /health        — system status (no auth)
POST /ask           — ask a question (requires X-API-Key header)
```

**Example request:**

```bash
curl -X POST http://localhost:8080/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your_secret_key" \
  -d '{"question": "what projects have you built?"}'
```

**Example response:**

```json
{
  "answer": "...",
  "sources": ["chromadb", "github"],
  "blocked": false
}
```

---

## Switching LLM provider

```env
# Production — HuggingFace Inference API (no GPU needed)
MODEL_PROVIDER=huggingface

# Development — local Ollama (requires GPU)
MODEL_PROVIDER=ollama
MODEL_NAME=llama3.1:8b
```

Restart the API after changing:
```bash
docker compose -f docker/docker-compose.yml restart api
```

---

## Knowledge base

Add or update markdown files in `data/` and re-ingest:

```bash
docker compose -f docker/docker-compose.yml exec api python scripts/ingest.py
```

Ingestion is incremental — only modified files are reprocessed (MD5 check).

---

## License

MIT
