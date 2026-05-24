"""
tests/test_ingest.py
--------------------
Tests unitarios para scripts/ingest.py

Cubren la lógica de ingesta incremental sin depender de ChromaDB ni Ollama:
    - calcular_hash     — MD5 correcto y sensible a cambios de contenido
    - cargar_estado     — lee JSON existente o devuelve {} si no existe
    - guardar_estado    — escribe JSON legible y recargable
    - detectar_cambios  — nuevo / modificado / sin cambios / eliminado
    - procesar_archivo  — chunks con metadata correcta, archivo vacío

Las funciones que dependen de ChromaDB u Ollama (conectar_chroma,
ingestar_archivo, verificar_query) no se testean aquí — requieren
servicios reales y están cubiertas por tests de integración.

Correr:
    pytest tests/test_ingest.py -v
    pytest tests/test_ingest.py -v --tb=short
"""

import json
import pytest
from pathlib import Path

# ── Fixture base ──────────────────────────────────────────────────────────────

@pytest.fixture
def tmp_data(tmp_path):
    """
    Crea una estructura de directorios temporal que imita data/.
    Retorna la ruta base (tmp_path) para que los tests creen archivos ahí.

    tmp_path es un fixture de pytest que crea un directorio temporal
    único por test y lo limpia automáticamente al terminar.
    """
    (tmp_path / "proyectos").mkdir()
    (tmp_path / "experiencia").mkdir()
    (tmp_path / "stack").mkdir()
    return tmp_path


# ── calcular_hash ─────────────────────────────────────────────────────────────

class TestCalcularHash:

    def test_hash_es_string_hexadecimal(self, tmp_path):
        from scripts.ingest import calcular_hash
        archivo = tmp_path / "test.md"
        archivo.write_text("contenido de prueba", encoding="utf-8")
        resultado = calcular_hash(archivo)
        assert isinstance(resultado, str)
        # MD5 siempre es 32 caracteres hexadecimales
        assert len(resultado) == 32
        assert all(c in "0123456789abcdef" for c in resultado)

    def test_mismo_contenido_mismo_hash(self, tmp_path):
        from scripts.ingest import calcular_hash
        archivo1 = tmp_path / "a.md"
        archivo2 = tmp_path / "b.md"
        archivo1.write_text("mismo contenido", encoding="utf-8")
        archivo2.write_text("mismo contenido", encoding="utf-8")
        assert calcular_hash(archivo1) == calcular_hash(archivo2)

    def test_contenido_diferente_hash_diferente(self, tmp_path):
        from scripts.ingest import calcular_hash
        archivo1 = tmp_path / "a.md"
        archivo2 = tmp_path / "b.md"
        archivo1.write_text("contenido A", encoding="utf-8")
        archivo2.write_text("contenido B", encoding="utf-8")
        assert calcular_hash(archivo1) != calcular_hash(archivo2)

    def test_cambio_minimo_cambia_hash(self, tmp_path):
        """Un solo caracter de diferencia debe cambiar el hash."""
        from scripts.ingest import calcular_hash
        archivo = tmp_path / "test.md"
        archivo.write_text("contenido original", encoding="utf-8")
        hash_original = calcular_hash(archivo)
        archivo.write_text("contenido origina1", encoding="utf-8")  # 'l' → '1'
        assert calcular_hash(archivo) != hash_original

    def test_hash_estable_sin_cambios(self, tmp_path):
        """Llamar dos veces al mismo archivo sin modificarlo da el mismo hash."""
        from scripts.ingest import calcular_hash
        archivo = tmp_path / "test.md"
        archivo.write_text("contenido estable", encoding="utf-8")
        assert calcular_hash(archivo) == calcular_hash(archivo)


# ── cargar_estado / guardar_estado ────────────────────────────────────────────

class TestEstado:

    def test_cargar_estado_devuelve_dict_vacio_si_no_existe(self, tmp_path, monkeypatch):
        from scripts import ingest
        monkeypatch.setattr(ingest, "STATE_FILE", tmp_path / "noexiste.json")
        estado = ingest.cargar_estado()
        assert estado == {}

    def test_cargar_estado_lee_json_existente(self, tmp_path, monkeypatch):
        from scripts import ingest
        state_file = tmp_path / ".ingest_state.json"
        state_file.write_text(
            json.dumps({"data/proyectos/lineup.md": "abc123"}),
            encoding="utf-8"
        )
        monkeypatch.setattr(ingest, "STATE_FILE", state_file)
        estado = ingest.cargar_estado()
        assert estado == {"data/proyectos/lineup.md": "abc123"}

    def test_guardar_estado_crea_archivo(self, tmp_path, monkeypatch):
        from scripts import ingest
        state_file = tmp_path / ".ingest_state.json"
        monkeypatch.setattr(ingest, "STATE_FILE", state_file)
        ingest.guardar_estado({"data/stack/tecnologias.md": "def456"})
        assert state_file.exists()

    def test_guardar_y_cargar_ida_y_vuelta(self, tmp_path, monkeypatch):
        """guardar_estado + cargar_estado deben ser inversos exactos."""
        from scripts import ingest
        state_file = tmp_path / ".ingest_state.json"
        monkeypatch.setattr(ingest, "STATE_FILE", state_file)
        estado_original = {
            "data/proyectos/lineup.md"   : "abc123",
            "data/stack/tecnologias.md"  : "def456",
            "data/experiencia/flextech.md": "ghi789",
        }
        ingest.guardar_estado(estado_original)
        estado_cargado = ingest.cargar_estado()
        assert estado_cargado == estado_original

    def test_guardar_estado_es_json_legible(self, tmp_path, monkeypatch):
        """El archivo debe ser JSON válido que cualquier herramienta pueda leer."""
        from scripts import ingest
        state_file = tmp_path / ".ingest_state.json"
        monkeypatch.setattr(ingest, "STATE_FILE", state_file)
        ingest.guardar_estado({"clave": "valor"})
        with open(state_file, encoding="utf-8") as f:
            contenido = json.load(f)
        assert contenido == {"clave": "valor"}


# ── detectar_cambios ──────────────────────────────────────────────────────────

class TestDetectarCambios:

    def _setup(self, tmp_data, monkeypatch):
        """Configura ingest para usar tmp_data como DATA_DIR y ROOT_DIR."""
        from scripts import ingest
        monkeypatch.setattr(ingest, "DATA_DIR", tmp_data)
        monkeypatch.setattr(ingest, "ROOT_DIR", tmp_data)
        monkeypatch.setattr(ingest, "STATE_FILE", tmp_data / ".ingest_state.json")

    def test_archivo_nuevo_detectado(self, tmp_data, monkeypatch):
        """Un archivo sin hash previo debe aparecer en a_ingestar."""
        from scripts.ingest import detectar_cambios
        self._setup(tmp_data, monkeypatch)
        (tmp_data / "proyectos" / "lineup.md").write_text("# Lineup", encoding="utf-8")

        a_ingestar, eliminados = detectar_cambios({})

        assert len(a_ingestar) == 1
        assert a_ingestar[0].name == "lineup.md"
        assert eliminados == []

    def test_archivo_sin_cambios_salteado(self, tmp_data, monkeypatch):
        """Un archivo cuyo hash coincide con el guardado no debe procesarse."""
        from scripts import ingest
        from scripts.ingest import detectar_cambios, calcular_hash
        self._setup(tmp_data, monkeypatch)

        archivo = tmp_data / "proyectos" / "lineup.md"
        archivo.write_text("# Lineup", encoding="utf-8")
        hash_actual = calcular_hash(archivo)

        # El estado guardado ya tiene el hash correcto
        estado = {str(archivo.relative_to(tmp_data)): hash_actual}
        a_ingestar, eliminados = detectar_cambios(estado)

        assert a_ingestar == []
        assert eliminados == []

    def test_archivo_modificado_detectado(self, tmp_data, monkeypatch):
        """Un archivo cuyo hash difiere del guardado debe re-procesarse."""
        from scripts.ingest import detectar_cambios
        self._setup(tmp_data, monkeypatch)

        archivo = tmp_data / "proyectos" / "lineup.md"
        archivo.write_text("# Lineup actualizado", encoding="utf-8")

        # Estado guardado tiene un hash viejo (diferente al actual)
        estado = {str(archivo.relative_to(tmp_data)): "hash_viejo_incorrecto"}
        a_ingestar, eliminados = detectar_cambios(estado)

        assert len(a_ingestar) == 1
        assert a_ingestar[0].name == "lineup.md"

    def test_archivo_eliminado_detectado(self, tmp_data, monkeypatch):
        """Un archivo en el estado guardado que ya no existe debe aparecer en eliminados."""
        from scripts.ingest import detectar_cambios
        self._setup(tmp_data, monkeypatch)

        # No creamos ningún archivo en disco
        estado = {"proyectos/lineup.md": "abc123"}
        a_ingestar, eliminados = detectar_cambios(estado)

        assert "proyectos/lineup.md" in eliminados
        assert a_ingestar == []

    def test_directorio_vacio_no_falla(self, tmp_data, monkeypatch):
        """Sin archivos .md, detectar_cambios retorna listas vacías sin explotar."""
        from scripts.ingest import detectar_cambios
        self._setup(tmp_data, monkeypatch)

        a_ingestar, eliminados = detectar_cambios({})

        assert a_ingestar == []
        assert eliminados == []

    def test_multiples_archivos_detectados(self, tmp_data, monkeypatch):
        """Varios archivos nuevos deben aparecer todos en a_ingestar."""
        from scripts.ingest import detectar_cambios
        self._setup(tmp_data, monkeypatch)

        (tmp_data / "proyectos" / "lineup.md").write_text("# Lineup", encoding="utf-8")
        (tmp_data / "proyectos" / "whatsapp.md").write_text("# WhatsApp Bot", encoding="utf-8")
        (tmp_data / "stack" / "tecnologias.md").write_text("# Stack", encoding="utf-8")

        a_ingestar, eliminados = detectar_cambios({})

        assert len(a_ingestar) == 3
        nombres = {p.name for p in a_ingestar}
        assert nombres == {"lineup.md", "whatsapp.md", "tecnologias.md"}

    def test_mix_nuevo_sin_cambios_eliminado(self, tmp_data, monkeypatch):
        """Escenario real: un nuevo, uno sin cambios, uno eliminado al mismo tiempo."""
        from scripts.ingest import detectar_cambios, calcular_hash
        self._setup(tmp_data, monkeypatch)

        # Archivo que existe y no cambió
        sin_cambios = tmp_data / "stack" / "tecnologias.md"
        sin_cambios.write_text("# Stack tecnológico", encoding="utf-8")
        hash_sin_cambios = calcular_hash(sin_cambios)

        # Archivo nuevo (no está en el estado guardado)
        nuevo = tmp_data / "proyectos" / "lineup.md"
        nuevo.write_text("# Lineup", encoding="utf-8")

        # El estado guardado incluye tecnologias (sin cambios) y uno eliminado
        estado = {
            str(sin_cambios.relative_to(tmp_data)): hash_sin_cambios,
            "experiencia/flextech.md": "hash_de_archivo_eliminado",
        }
        a_ingestar, eliminados = detectar_cambios(estado)

        assert len(a_ingestar) == 1
        assert a_ingestar[0].name == "lineup.md"
        assert "experiencia/flextech.md" in eliminados


# ── procesar_archivo ──────────────────────────────────────────────────────────

class TestProcesarArchivo:

    def test_archivo_vacio_retorna_lista_vacia(self, tmp_path):
        from scripts.ingest import procesar_archivo
        archivo = tmp_path / "vacio.md"
        archivo.write_text("", encoding="utf-8")
        chunks = procesar_archivo(archivo)
        assert chunks == []

    def test_archivo_solo_espacios_retorna_lista_vacia(self, tmp_path):
        from scripts.ingest import procesar_archivo
        archivo = tmp_path / "espacios.md"
        archivo.write_text("   \n\n   ", encoding="utf-8")
        chunks = procesar_archivo(archivo)
        assert chunks == []

    def test_archivo_con_contenido_genera_chunks(self, tmp_path):
        from scripts.ingest import procesar_archivo
        archivo = tmp_path / "proyectos" / "lineup.md"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text("# Lineup\n\nProyecto de playlists con Spotify.", encoding="utf-8")
        chunks = procesar_archivo(archivo)
        assert len(chunks) >= 1

    def test_chunk_tiene_campos_requeridos(self, tmp_path):
        from scripts.ingest import procesar_archivo
        archivo = tmp_path / "proyectos" / "lineup.md"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text("# Lineup\n\nProyecto de playlists con Spotify.", encoding="utf-8")
        chunks = procesar_archivo(archivo)
        for chunk in chunks:
            assert "id"       in chunk
            assert "texto"    in chunk
            assert "metadata" in chunk

    def test_metadata_tiene_campos_requeridos(self, tmp_path):
        from scripts.ingest import procesar_archivo
        archivo = tmp_path / "proyectos" / "lineup.md"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text("# Lineup\n\nProyecto de playlists con Spotify.", encoding="utf-8")
        chunks = procesar_archivo(archivo)
        meta = chunks[0]["metadata"]
        assert "tipo"    in meta
        assert "fuente"  in meta
        assert "carpeta" in meta
        assert "chunk"   in meta

    def test_tipo_asignado_por_carpeta_proyectos(self, tmp_path):
        from scripts.ingest import procesar_archivo
        archivo = tmp_path / "proyectos" / "lineup.md"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text("# Lineup\n\nProyecto de playlists.", encoding="utf-8")
        chunks = procesar_archivo(archivo)
        assert chunks[0]["metadata"]["tipo"] == "proyecto_detalle"

    def test_tipo_asignado_por_carpeta_stack(self, tmp_path):
        from scripts.ingest import procesar_archivo
        archivo = tmp_path / "stack" / "tecnologias.md"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text("# Stack\n\nPython, Docker, FastAPI.", encoding="utf-8")
        chunks = procesar_archivo(archivo)
        assert chunks[0]["metadata"]["tipo"] == "stack_tecnologico"

    def test_tipo_general_para_carpeta_desconocida(self, tmp_path):
        from scripts.ingest import procesar_archivo
        archivo = tmp_path / "nueva_carpeta" / "test.md"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text("# Contenido nuevo", encoding="utf-8")
        chunks = procesar_archivo(archivo)
        assert chunks[0]["metadata"]["tipo"] == "general"

    def test_ids_son_unicos_en_un_archivo(self, tmp_path):
        """Cada chunk debe tener un ID único para que ChromaDB no colisione."""
        from scripts.ingest import procesar_archivo
        # Contenido largo para generar múltiples chunks
        contenido = "# Proyecto\n\n" + ("Texto de prueba. " * 50)
        archivo = tmp_path / "proyectos" / "largo.md"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(contenido, encoding="utf-8")
        chunks = procesar_archivo(archivo)
        ids = [c["id"] for c in chunks]
        assert len(ids) == len(set(ids))  # sin duplicados

    def test_fuente_es_nombre_sin_extension(self, tmp_path):
        """metadata['fuente'] debe ser el stem del archivo, sin .md."""
        from scripts.ingest import procesar_archivo
        archivo = tmp_path / "proyectos" / "whatsapp_booking_bot.md"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text("# WhatsApp Bot\n\nBot de turnos.", encoding="utf-8")
        chunks = procesar_archivo(archivo)
        assert chunks[0]["metadata"]["fuente"] == "whatsapp_booking_bot"

    def test_chunks_numerados_desde_cero(self, tmp_path):
        """El índice de chunk debe empezar en 0."""
        from scripts.ingest import procesar_archivo
        contenido = "# Proyecto\n\n" + ("Texto. " * 50)
        archivo = tmp_path / "proyectos" / "largo.md"
        archivo.parent.mkdir(parents=True, exist_ok=True)
        archivo.write_text(contenido, encoding="utf-8")
        chunks = procesar_archivo(archivo)
        assert chunks[0]["metadata"]["chunk"] == 0
