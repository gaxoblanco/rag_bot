"""
connectors/huggingface_connector.py
------------------------------------
Obtiene modelos y spaces públicos de HuggingFace para enriquecer el contexto del RAG.
No duplica datos que ya están en ChromaDB — solo trae lo que vive en HuggingFace.

Funciones principales:
    get_hf_models(username)  -> list[dict]
    get_hf_spaces(username)  -> list[dict]
    get_hf_all(username)     -> dict con "modelos" y "spaces"
"""

import os
from huggingface_hub import HfApi
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

# ── Configuración ─────────────────────────────────────────────────────────────

HF_TOKEN    = os.getenv("HF_TOKEN")
HF_USERNAME = os.getenv("HF_USERNAME", "gaxoblanco")

MODELCARD_MAX_CHARS = 800

# ── Funciones ─────────────────────────────────────────────────────────────────

def get_hf_models(username: str = HF_USERNAME) -> list[dict]:
    """Obtiene los modelos públicos de un usuario de HuggingFace."""
    if not HF_TOKEN:
        print("[huggingface] HF_TOKEN no configurado — saltando conector")
        return []

    try:
        api     = HfApi(token=HF_TOKEN)
        modelos = list(api.list_models(author=username))

        resultados = []
        for modelo in modelos:
            descripcion = ""
            try:
                card = api.model_info(modelo.modelId, token=HF_TOKEN)
                if card.cardData and card.cardData.get("model-index"):
                    descripcion = str(card.cardData.get("model-index", ""))[:MODELCARD_MAX_CHARS]
            except Exception:
                pass

            resultados.append({
                "nombre"              : modelo.modelId,
                "task"                : modelo.pipeline_tag or "no especificado",
                "descripcion"         : descripcion,
                "url"                 : f"https://huggingface.co/{modelo.modelId}",
                "ultima_actualizacion": modelo.lastModified.isoformat() if modelo.lastModified else "",
            })

        print(f"[huggingface] {len(resultados)} modelos obtenidos para '{username}'")
        return resultados

    except Exception as e:
        print(f"[huggingface] Error al obtener modelos: {e}")
        return []


def get_hf_spaces(username: str = HF_USERNAME) -> list[dict]:
    """Obtiene los spaces públicos de un usuario de HuggingFace."""
    if not HF_TOKEN:
        print("[huggingface] HF_TOKEN no configurado — saltando conector")
        return []

    try:
        api    = HfApi(token=HF_TOKEN)
        spaces = list(api.list_spaces(author=username))

        resultados = []
        for space in spaces:
            resultados.append({
                "nombre"              : space.id,
                "sdk"                 : space.sdk or "no especificado",   # streamlit, gradio, etc.
                "descripcion"         : space.cardData.get("title", "") if space.cardData else "",
                "url"                 : f"https://huggingface.co/spaces/{space.id}",
                "ultima_actualizacion": space.lastModified.isoformat() if space.lastModified else "",
            })

        print(f"[huggingface] {len(resultados)} spaces obtenidos para '{username}'")
        return resultados

    except Exception as e:
        print(f"[huggingface] Error al obtener spaces: {e}")
        return []


def get_hf_all(username: str = HF_USERNAME) -> dict:
    """Obtiene modelos y spaces en una sola llamada."""
    return {
        "modelos": get_hf_models(username),
        "spaces" : get_hf_spaces(username),
    }


def formatear_para_contexto(modelos: list[dict], spaces: list[dict]) -> str:
    """Convierte modelos y spaces a texto plano para el contexto del LLM."""
    lineas = []

    if modelos:
        lineas.append("## Modelos publicados en HuggingFace\n")
        for m in modelos:
            lineas.append(f"### {m['nombre']}")
            lineas.append(f"Task: {m['task']}")
            if m["descripcion"]:
                lineas.append(m["descripcion"])
            lineas.append(f"URL: {m['url']}\n")

    if spaces:
        lineas.append("## Spaces publicados en HuggingFace\n")
        for s in spaces:
            lineas.append(f"### {s['nombre']}")
            lineas.append(f"SDK: {s['sdk']}")
            if s["descripcion"]:
                lineas.append(s["descripcion"])
            lineas.append(f"URL: {s['url']}\n")

    return "\n".join(lineas)


# ── Test desde terminal ───────────────────────────────────────────────────────

if __name__ == "__main__":
    resultado = get_hf_all()

    modelos = resultado["modelos"]
    spaces  = resultado["spaces"]

    if modelos:
        print(f"\n{len(modelos)} modelos encontrados:")
        for m in modelos:
            print(f"  - {m['nombre']} (task: {m['task']})")

    if spaces:
        print(f"\n{len(spaces)} spaces encontrados:")
        for s in spaces:
            print(f"  - {s['nombre']} (sdk: {s['sdk']})")

    if not modelos and not spaces:
        print("Sin resultados.")