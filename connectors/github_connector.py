"""
connectors/github_connector.py
-------------------------------
Obtiene repos pineados de GitHub via GraphQL API.
No duplica datos que ya están en ChromaDB — solo trae lo que vive en GitHub.

Traigo los repos pineados para mostrar como representativos
— señal explícita de relevancia para el perfil.

Función principal: get_github_projects(username) -> list[dict]
"""

import os
import requests
from dotenv import load_dotenv
from pathlib import Path

load_dotenv(Path(__file__).parent.parent / ".env")

# ── Configuración ─────────────────────────────────────────────────────────────

GITHUB_TOKEN    = os.getenv("GITHUB_TOKEN")
GITHUB_USERNAME = os.getenv("GITHUB_USERNAME", "gaxoblanco")

README_MAX_CHARS = 600    # contexto acotado — solo lo esencial del README
GRAPHQL_URL      = "https://api.github.com/graphql"

# ── Query GraphQL — repos pineados ────────────────────────────────────────────

PINNED_REPOS_QUERY = """
query PinnedRepos($username: String!) {
  user(login: $username) {
    pinnedItems(first: 6, types: REPOSITORY) {
      nodes {
        ... on Repository {
          name
          description
          url
          primaryLanguage {
            name
          }
          object(expression: "HEAD:README.md") {
            ... on Blob {
              text
            }
          }
        }
      }
    }
  }
}
"""

# ── Funciones ─────────────────────────────────────────────────────────────────

def get_github_projects(username: str = GITHUB_USERNAME) -> list[dict]:
    """
    Obtiene los repos pineados de un usuario de GitHub via GraphQL.

    Devuelve lista de dicts con:
        - nombre
        - descripcion
        - lenguaje principal
        - readme (primeros README_MAX_CHARS caracteres)
        - url
    """
    if not GITHUB_TOKEN:
        print("[github] GITHUB_TOKEN no configurado — saltando conector")
        return []

    headers = {
        "Authorization": f"bearer {GITHUB_TOKEN}",
        "Content-Type" : "application/json",
    }

    payload = {
        "query"    : PINNED_REPOS_QUERY,
        "variables": {"username": username},
    }

    try:
        response = requests.post(GRAPHQL_URL, json=payload, headers=headers)
        response.raise_for_status()
        data = response.json()

        # Verificar errores de GraphQL
        if "errors" in data:
            print(f"[github] Error GraphQL: {data['errors']}")
            return []

        nodos = data["data"]["user"]["pinnedItems"]["nodes"]

        proyectos = []
        for repo in nodos:

            # README — primeros README_MAX_CHARS caracteres
            readme = ""
            readme_obj = repo.get("object")
            if readme_obj and readme_obj.get("text"):
                readme = readme_obj["text"][:README_MAX_CHARS]

            # Lenguaje principal
            lang_obj = repo.get("primaryLanguage")
            lenguaje = lang_obj["name"] if lang_obj else ""

            proyectos.append({
                "nombre"     : repo["name"],
                "descripcion": repo.get("description") or "",
                "lenguaje"   : lenguaje,
                "readme"     : readme,
                "url"        : repo["url"],
            })

        print(f"[github] {len(proyectos)} repos pineados obtenidos para '{username}'")
        return proyectos

    except requests.RequestException as e:
        print(f"[github] Error al conectar: {e}")
        return []


def formatear_para_contexto(proyectos: list[dict]) -> str:
    """
    Convierte la lista de repos pineados a texto plano para el contexto del LLM.
    Solo incluye nombre, descripción y README — sin ruido extra.
    """
    if not proyectos:
        return ""

    lineas = ["## Repositorios destacados en GitHub\n"]
    for p in proyectos:
        lineas.append(f"### {p['nombre']}")
        if p["descripcion"]:
            lineas.append(p["descripcion"])
        if p["lenguaje"]:
            lineas.append(f"Lenguaje principal: {p['lenguaje']}")
        if p["readme"]:
            lineas.append(f"\n{p['readme']}")
        lineas.append(f"URL: {p['url']}\n")

    return "\n".join(lineas)


# ── Test desde terminal ───────────────────────────────────────────────────────

if __name__ == "__main__":
    proyectos = get_github_projects()
    if proyectos:
        print(f"\n{len(proyectos)} repos pineados:\n")
        for p in proyectos:
            print(f"  - {p['nombre']} ({p['lenguaje']}): {p['descripcion'][:60]}")
        print("\n── Contexto generado ──────────────────────────────────")
        print(formatear_para_contexto(proyectos))
    else:
        print("Sin resultados.")