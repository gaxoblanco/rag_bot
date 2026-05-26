"""
scripts/ingest.py
-----------------
Lee los archivos .md de data/, detecta cambios por hash MD5,
y solo re-ingesta los archivos nuevos o modificados.

Uso:
    python scripts/ingest.py           # ingesta incremental
    python scripts/ingest.py --reset   # borra ChromaDB y re-ingesta todo
    docker compose -f docker/docker-compose.yml exec api python scripts/ingest.pydocker compose -f docker/docker-compose.yml exec api python scripts/ingest.py
"""

import os
import sys
import json
import hashlib
import argparse
from pathlib import Path

import chromadb
from langchain_ollama import OllamaEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from dotenv import load_dotenv

# ── Configuración ─────────────────────────────────────────────────────────────

load_dotenv()

ROOT_DIR        = Path(__file__).parent.parent
DATA_DIR        = ROOT_DIR / "data"
STATE_FILE      = DATA_DIR / ".ingest_state.json"

CHROMA_HOST       = os.getenv("CHROMA_HOST", "localhost")
CHROMA_PORT       = int(os.getenv("CHROMA_PORT", "8000"))
CHROMA_COLLECTION = "gaston_rag"

# Lo usamos para conversión de texto a vectores.
# Asegúrate de tener un modelo de embedding compatible en Ollama, como "nomic-embed-text".
OLLAMA_HOST            = os.getenv("OLLAMA_HOST", "localhost")
OLLAMA_PORT            = os.getenv("OLLAMA_PORT", "11434")
OLLAMA_EMBEDDING_MODEL = os.getenv("OLLAMA_EMBEDDING_MODEL", "nomic-embed-text")

CHUNK_SIZE    = 500
CHUNK_OVERLAP = 50

# Agregar nuevas carpetas acá cuando se creen en data/
FOLDER_TO_TYPE = {
    "experiencia" : "experiencia",
    "proyectos"   : "proyecto_detalle",
    "stack"       : "stack_tecnologico",
    "decisiones"  : "decision_tecnica",
    "orientacion" : "orientacion_profesional",
}

# ── Hashes ────────────────────────────────────────────────────────────────────
# Para evitar re-ingestar archivos que no cambiaron, calculamos un hash MD5
# de su contenido y lo guardamos en un JSON. En la próxima ejecución, comparamos
# el hash actual con el guardado para detectar cambios.

def calcular_hash(path: Path) -> str:
    return hashlib.md5(path.read_bytes()).hexdigest()

def cargar_estado() -> dict:
    if STATE_FILE.exists():
        with open(STATE_FILE, encoding="utf-8") as f:
            return json.load(f)
    return {}

def guardar_estado(estado: dict) -> None:
    with open(STATE_FILE, "w", encoding="utf-8") as f:
        json.dump(estado, f, indent=2)

def detectar_cambios(estado_guardado: dict) -> tuple[list[Path], list[str]]:
    archivos_actuales = {
        str(p.relative_to(ROOT_DIR)): p
        for p in DATA_DIR.rglob("*.md")
        if not p.name.startswith(".")
    }
    a_ingestar = []
    eliminados = []

    for key, path in archivos_actuales.items():
        hash_actual   = calcular_hash(path)
        hash_guardado = estado_guardado.get(key)
        if hash_actual != hash_guardado:
            estado = "nuevo" if hash_guardado is None else "modificado"
            print(f"[cambio] {estado}: {key}")
            a_ingestar.append(path)
        else:
            print(f"[skip]   sin cambios: {key}")

    for key in estado_guardado:
        if key not in archivos_actuales:
            print(f"[cambio] eliminado: {key}")
            eliminados.append(key)

    return a_ingestar, eliminados

# ── ChromaDB ──────────────────────────────────────────────────────────────────

def conectar_chroma() -> chromadb.HttpClient:
    print(f"[chroma] Conectando a {CHROMA_HOST}:{CHROMA_PORT}...")
    client = chromadb.HttpClient(host=CHROMA_HOST, port=CHROMA_PORT)
    client.heartbeat()
    print("[chroma] Conexión OK")
    return client

def obtener_coleccion(client: chromadb.HttpClient, reset: bool) -> chromadb.Collection:
    if reset:
        print(f"[chroma] Borrando colección '{CHROMA_COLLECTION}'...")
        try:
            client.delete_collection(CHROMA_COLLECTION)
        except Exception:
            pass
    collection = client.get_or_create_collection(
        name     = CHROMA_COLLECTION,
        metadata = {"hnsw:space": "cosine"}
    )
    print(f"[chroma] Colección lista ({collection.count()} documentos existentes)")
    return collection

def borrar_chunks_de_archivo(collection: chromadb.Collection, nombre: str) -> None:
    results = collection.get(where={"fuente": nombre})
    if results["ids"]:
        collection.delete(ids=results["ids"])
        print(f"[chroma] Borrados {len(results['ids'])} chunks de '{nombre}'")

# ── Chunking e ingesta ────────────────────────────────────────────────────────
# Para cada archivo, leemos su contenido, lo dividimos en chunks con overlap,
# y lo subimos a ChromaDB con su embedding y metadata.

def procesar_archivo(path: Path) -> list[dict]:
    carpeta   = path.parent.name
    tipo      = FOLDER_TO_TYPE.get(carpeta, "general")
    nombre    = path.stem
    contenido = path.read_text(encoding="utf-8").strip()

    if not contenido:
        return []

    splitter = RecursiveCharacterTextSplitter(
        chunk_size    = CHUNK_SIZE,
        chunk_overlap = CHUNK_OVERLAP,
        separators    = ["\n## ", "\n### ", "\n\n", "\n", " "],
    )

    return [
        {
            "id"      : f"{nombre}_{i}",
            "texto"   : parte,
            "metadata": {
                "tipo"   : tipo,
                "fuente" : nombre,
                "carpeta": carpeta,
                "chunk"  : i,
            }
        }
        for i, parte in enumerate(splitter.split_text(contenido))
    ]

def ingestar_archivo(
    path       : Path,
    collection : chromadb.Collection,
    embeddings : OllamaEmbeddings,
) -> None:
    nombre = path.stem
    borrar_chunks_de_archivo(collection, nombre)

    chunks = procesar_archivo(path)
    if not chunks:
        print(f"[skip] {path.name} — vacío")
        return

    BATCH_SIZE = 10
    for i in range(0, len(chunks), BATCH_SIZE):
        lote     = chunks[i : i + BATCH_SIZE]
        textos   = [c["texto"] for c in lote]
        vectores = embeddings.embed_documents(textos)
        collection.upsert(
            ids        = [c["id"] for c in lote],
            documents  = textos,
            embeddings = vectores,
            metadatas  = [c["metadata"] for c in lote],
        )

    print(f"[ok]     {path.name} → {len(chunks)} chunks cargados")

# ── Verificación ──────────────────────────────────────────────────────────────
# Para probar que todo funciona, hacemos una query de ejemplo y mostramos los resultados.

def verificar_query(collection: chromadb.Collection, embeddings: OllamaEmbeddings) -> None:
    print("\n[test] Verificando con query de prueba...")
    query   = "¿qué proyectos tiene Gastón en producción?"
    vector  = embeddings.embed_query(query)
    results = collection.query(query_embeddings=[vector], n_results=3)
    for i, (doc, meta) in enumerate(
        zip(results["documents"][0], results["metadatas"][0])
    ):
        print(f"  [{i+1}] {meta['tipo']} / {meta['fuente']}: {doc[:100]}...")

# ── Main ──────────────────────────────────────────────────────────────────────
# 1 - Conecta a ChromaDB y obtiene la colección (creándola si no existe).
# 2 - Carga el estado guardado (hashes) o inicia uno nuevo si --reset.
# 3 - Escanea data/ y detecta archivos nuevos, modificados o eliminados.
# 4 - Para cada archivo nuevo/modificado, lo procesa y lo ingesta en ChromaDB.
# 5 - Para cada archivo eliminado, borra sus chunks de ChromaDB.
# 6 - Guarda el nuevo estado (hashes) para la próxima ejecución.

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--reset", action="store_true",
                        help="Borra ChromaDB y re-ingesta todo desde cero")
    args = parser.parse_args()

    print("=" * 60)
    print("gaston_rag — ingesta incremental")
    print("=" * 60)

    client     = conectar_chroma()
    collection = obtener_coleccion(client, reset=args.reset)

    print(f"\n[ollama] Cargando embeddings: {OLLAMA_EMBEDDING_MODEL}")
    embeddings = OllamaEmbeddings(
        model    = OLLAMA_EMBEDDING_MODEL,
        base_url = f"http://{OLLAMA_HOST}:{OLLAMA_PORT}",
    )

    estado_guardado = {} if args.reset else cargar_estado()
    estado_nuevo    = dict(estado_guardado)

    print(f"\n[data] Escaneando {DATA_DIR}...")
    a_ingestar, eliminados = detectar_cambios(estado_guardado)

    for key in eliminados:
        borrar_chunks_de_archivo(collection, Path(key).stem)
        del estado_nuevo[key]

    if not a_ingestar and not eliminados:
        print("\n[ok] Knowledge base al día — nada que actualizar")
    else:
        print(f"\n[ingesta] Procesando {len(a_ingestar)} archivo(s)...")
        for path in a_ingestar:
            ingestar_archivo(path, collection, embeddings)
            key = str(path.relative_to(ROOT_DIR))
            estado_nuevo[key] = calcular_hash(path)

        guardar_estado(estado_nuevo)
        print(f"\n[chroma] Total: {collection.count()} documentos")

    if collection.count() > 0:
        verificar_query(collection, embeddings)

    print("\n" + "=" * 60)
    print("Ingesta completada")
    print("=" * 60)

if __name__ == "__main__":
    main()