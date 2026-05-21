# docker/Dockerfile
# gaston_rag — imagen de la API

FROM python:3.11-slim

WORKDIR /app

# curl para el healthcheck de ChromaDB
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Dependencias — capa separada para aprovechar cache de Docker
COPY requirements.txt .
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu && \
    pip install --no-cache-dir -r requirements.txt

# Código y datos
# Los volúmenes en docker-compose.yml sobreescriben estas carpetas en desarrollo,
# permitiendo cambios sin rebuild. En producción se usa lo copiado aquí.
COPY app/        ./app/
COPY scripts/    ./scripts/
COPY connectors/ ./connectors/
COPY data/       ./data/

EXPOSE 8000

# Al arrancar:
#   1. Ingesta incremental — solo procesa archivos nuevos o modificados
#   2. Levanta la API
CMD ["sh", "-c", "python scripts/ingest.py && uvicorn app.main:app --host 0.0.0.0 --port 8000"]