"""
scripts/test_similarity.py
--------------------------
Testea el score de similaridad de ChromaDB para queries de prueba.
Útil para debuggear qué chunks está trayendo el retrieval y con qué score.

Uso:
    python scripts/test_similarity.py
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import chromadb
from langchain_ollama import OllamaEmbeddings
from app import config

# ── Queries de prueba ─────────────────────────────────────────────────────────

QUERIES = [
    "¿qué proyectos tiene Gastón en producción?",
    "¿qué tecnologías usa Gastón?",
    "¿dónde trabajó Gastón?",
]

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    client = chromadb.HttpClient(
        host=config.CHROMA_HOST,
        port=config.CHROMA_PORT,
    )
    col = client.get_or_create_collection(config.CHROMA_COLLECTION)

    embeddings = OllamaEmbeddings(
        model=config.OLLAMA_EMBEDDING_MODEL,
        base_url=config.OLLAMA_BASE_URL,
    )

    for query in QUERIES:
        print(f"\n{'='*60}")
        print(f"Query: {query}")
        print("="*60)

        vector  = embeddings.embed_query(query)
        results = col.query(query_embeddings=[vector], n_results=6)

        for i, (doc, meta, dist) in enumerate(zip(
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )):
            score = 1 - dist
            print(f"\n[{i+1}] score={score:.3f} | {meta['tipo']} / {meta['fuente']}")
            print(f"     {doc[:100]}")


if __name__ == "__main__":
    main()
