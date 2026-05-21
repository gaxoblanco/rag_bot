"""
scripts/chat.py
---------------
Chat interactivo para testear el endpoint /ask como si fuera la landing page.
Útil para QA manual — validar respuestas, tono, sources y seguridad.

Uso:
    python scripts/chat.py                        # apunta a localhost:8080
    python scripts/chat.py --url http://servidor:8080
    python scripts/chat.py --url http://servidor:8080 --key MI_API_KEY

Comandos especiales durante el chat:
    /salir    — termina la sesión
    /sources  — muestra las fuentes de la última respuesta
    /tiempo   — muestra el tiempo de la última respuesta
    /ayuda    — muestra estos comandos
"""

import sys
import time
import argparse
from pathlib import Path

import requests
from dotenv import load_dotenv
import os

# ── Config ────────────────────────────────────────────────────────────────────

load_dotenv(Path(__file__).parent.parent / ".env")

DEFAULT_URL = "http://localhost:8080"
DEFAULT_KEY = os.getenv("GASTON_RAG_API_KEY", "")

# ── Helpers ───────────────────────────────────────────────────────────────────

def separator(char="─", width=60):
    print(char * width)

def print_header(url: str):
    separator("═")
    print("  gaston_rag — Chat de QA")
    print(f"  Endpoint: {url}")
    print("  /ayuda para comandos · /salir para terminar")
    separator("═")
    print()

def print_ayuda():
    print()
    print("  Comandos disponibles:")
    print("  /salir   — termina la sesión")
    print("  /sources — fuentes de la última respuesta")
    print("  /tiempo  — tiempo de la última respuesta")
    print("  /ayuda   — muestra esta ayuda")
    print()

def check_health(url: str) -> bool:
    """Verifica que la API esté corriendo antes de empezar."""
    try:
        r = requests.get(f"{url}/health", timeout=5)
        r.raise_for_status()
        data = r.json()
        print(f"  ✓ API online — versión {data.get('version', '?')}")
        return True
    except requests.exceptions.ConnectionError:
        print(f"  ✗ No se puede conectar a {url}")
        print("    ¿Está corriendo Docker? docker compose up -d")
        return False
    except Exception as e:
        print(f"  ✗ Error al verificar health: {e}")
        return False

def preguntar(url: str, key: str, question: str) -> dict:
    """Envía una pregunta al endpoint /ask y devuelve el resultado."""
    headers = {
        "Content-Type": "application/json",
        "X-API-Key": key,
    }
    payload = {"question": question}

    t_inicio = time.time()
    response = requests.post(f"{url}/ask", json=payload, headers=headers, timeout=30)
    t_total  = time.time() - t_inicio

    if response.status_code == 401:
        raise ValueError("API key inválida — verificar GASTON_RAG_API_KEY en .env")
    if response.status_code == 429:
        raise ValueError("Rate limit alcanzado — esperá un momento")
    response.raise_for_status()

    data = response.json()
    data["_tiempo"] = round(t_total, 2)
    return data

# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Chat QA para gaston_rag")
    parser.add_argument("--url", default=DEFAULT_URL, help="URL base de la API")
    parser.add_argument("--key", default=DEFAULT_KEY, help="API key (X-API-Key)")
    args = parser.parse_args()

    if not args.key:
        print("Error: API key no encontrada.")
        print("Agregá GASTON_RAG_API_KEY al .env o pasala con --key TU_KEY")
        sys.exit(1)

    print_header(args.url)

    # Verificar que la API está corriendo
    if not check_health(args.url):
        sys.exit(1)

    print()
    separator()
    print()

    ultimo_resultado = None

    while True:
        try:
            entrada = input("Vos: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n\n  Sesión terminada.")
            break

        if not entrada:
            continue

        # Comandos especiales
        if entrada.lower() == "/salir":
            print("\n  Sesión terminada.")
            break

        if entrada.lower() == "/ayuda":
            print_ayuda()
            continue

        if entrada.lower() == "/sources":
            if ultimo_resultado and ultimo_resultado.get("sources"):
                print(f"\n  Fuentes: {', '.join(ultimo_resultado['sources'])}\n")
            else:
                print("\n  Sin fuentes disponibles.\n")
            continue

        if entrada.lower() == "/tiempo":
            if ultimo_resultado:
                print(f"\n  Tiempo de respuesta: {ultimo_resultado.get('_tiempo', '?')}s\n")
            else:
                print("\n  Sin datos aún.\n")
            continue

        # Pregunta normal
        try:
            resultado = preguntar(args.url, args.key, entrada)
            ultimo_resultado = resultado

            print()

            if resultado.get("blocked"):
                print("  [BLOQUEADO] La pregunta fue rechazada por el sistema de seguridad.")
            else:
                print(f"Gastón: {resultado['answer']}")
                if resultado.get("sources"):
                    print(f"\n  [{resultado['_tiempo']}s · fuentes: {', '.join(resultado['sources'])}]")
                else:
                    print(f"\n  [{resultado['_tiempo']}s]")

            print()

        except ValueError as e:
            print(f"\n  Error: {e}\n")
        except requests.exceptions.Timeout:
            print("\nGastón: No entendí bien la pregunta. ¿Podés reformularla con más detalle?\n")
        except Exception as e:
            print(f"\n  Error inesperado: {e}\n")


if __name__ == "__main__":
    main()