# docker/Dockerfile

FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias — capa separada para aprovechar cache
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Código y datos
COPY app/     ./app/
COPY scripts/ ./scripts/
COPY data/       ./data/
COPY connectors/ ./connectors/

EXPOSE 8000

# Al arrancar: ingesta incremental, luego levanta la API
CMD ["sh", "-c", "python scripts/ingest.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]