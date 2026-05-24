"""
check_chroma.py
---------------
Lista todas las fuentes unicas ingresadas en ChromaDB.
Usar para verificar los nombres exactos antes de armar el golden dataset.

Correr dentro del contenedor:
    docker compose -f docker/docker-compose.yml exec api python scripts/check_chroma.py
"""

import chromadb
import os

client = chromadb.HttpClient(
    host=os.getenv("CHROMA_HOST", "chroma"),
    port=int(os.getenv("CHROMA_PORT", "8000"))
)

collection = client.get_collection("gaston_rag")

results = collection.get(include=["metadatas"])
fuentes  = sorted(set(m.get("fuente", "sin_fuente") for m in results["metadatas"]))
tipos    = sorted(set(m.get("tipo",   "sin_tipo")   for m in results["metadatas"]))

print(f"Total chunks: {len(results['ids'])}")

print(f"\nFuentes — {len(fuentes)} archivos ingresados:")
for f in fuentes:
    count = sum(1 for m in results["metadatas"] if m.get("fuente") == f)
    print(f"  {count:3d} chunks  ->  {f}")

print(f"\nTipos de chunk:")
for t in tipos:
    count = sum(1 for m in results["metadatas"] if m.get("tipo") == t)
    print(f"  {count:3d} chunks  ->  {t}")
