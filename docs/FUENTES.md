# FUENTES.md
## RAG Personal · Gastón Blanco

> Detalle de las tres fuentes de datos del sistema.
> Documento vivo — actualizar cuando se agreguen categorías o cambien los conectores.

---

## Índice

1. [Principio general](#1-principio-general)
2. [ChromaDB — knowledge base](#2-chromadb)
3. [GitHub API](#3-github-api)
4. [HuggingFace API](#4-huggingface-api)
5. [LinkedIn — excluido](#5-linkedin)
6. [Agregar una categoría nueva](#6-agregar-categoria-nueva)

---

## 1. Principio general

No duplicar datos que ya existen con API.
Cada fuente tiene una responsabilidad clara y no se pisa con las otras.

| Fuente | Responsabilidad |
|---|---|
| ChromaDB | Narrativa, contexto, decisiones, orientación — lo que no existe en ninguna API |
| GitHub | Repos públicos, READMEs, lenguajes, actividad |
| HuggingFace | Modelos, spaces y datasets públicos |

---

## 2. ChromaDB

### Categorías actuales

Cada chunk en ChromaDB tiene un campo `tipo` en su metadata.
Las categorías pueden crecer — ver sección 6.

| Categoría (`tipo`) | Qué contiene |
|---|---|
| `experiencia` | Historia laboral narrativa, contexto de cada trabajo |
| `proyecto_detalle` | Qué hace cada proyecto, decisiones tomadas |
| `decision_tecnica` | Por qué X sobre Y — razonamiento documentado |
| `stack_tecnologico` | Tecnologías usadas y en qué contexto específico |
| `metricas` | Resultados medibles por proyecto |
| `orientacion_profesional` | A dónde va, qué quiere aprender, expectativas |

### Estructura de un chunk

```python
{
    "content": "Texto del chunk...",
    "metadata": {
        "tipo": "decision_tecnica",
        "proyecto": "whatsapp_booking_bot",
        "tecnologias": ["docker", "spacy", "flask"],
        "año": "2025",
        "tema": "arquitectura_multi_tenant"
    }
}
```

### Actualización

Manual. Cuando hay un proyecto nuevo o cambio relevante:
1. Editar el `.md` correspondiente en `data/`
2. Correr `scripts/ingest.py`
3. El sistema incorpora los cambios — no hace falta reiniciar la API

### Archivos en data/

```
data/
├── experiencia/
│   ├── that_day_london.md
│   └── proyectos_personales.md
├── proyectos/
│   ├── whatsapp_booking_bot.md
│   ├── lineup.md
│   └── interpretability_series.md
├── decisiones/
│   └── decisiones_tecnicas.md
├── stack/
│   └── tecnologias.md
└── orientacion/
    └── objetivos_profesionales.md
```

---

## 3. GitHub API

### Qué se extrae por repo

| Campo | Detalle |
|---|---|
| Nombre y descripción | Del repo |
| Lenguajes principales | Top 3 por bytes |
| README | Primeros 1000 chars — evita tokens excesivos |
| Última actividad | `updated_at` |

### Módulo

`connectors/github.py` — función principal: `get_github_projects(username)`

### Rate limit

5.000 requests/hora con token autenticado. Sin problema para este uso.

### Punto de ajuste

Modificar cuánto del README se incluye y qué campos se extraen en `connectors/github.py`.

---

## 4. HuggingFace API

### Qué se extrae

| Campo | Detalle |
|---|---|
| Nombre del modelo | ID completo |
| Task | Clasificación, generación, embeddings, etc. |
| Descripción | Primeras líneas del model card |
| Métricas | Si están disponibles en el model card |

### Módulo

`connectors/huggingface.py` — función principal: `get_hf_models(username)`

### Punto de ajuste

Agregar datasets y spaces cuando sea relevante incluirlos en respuestas.

---

## 5. LinkedIn

**Excluido** — scraping no permitido por términos de servicio.
Los datos relevantes de LinkedIn (experiencia, educación) entran
manualmente por ChromaDB bajo las categorías `experiencia` y `orientacion_profesional`.

---

## 6. Agregar una categoría nueva

ChromaDB no tiene esquema rígido. Para agregar una categoría:

1. Crear o editar un archivo `.md` en `data/` con el nuevo contenido
2. Asignar el nuevo valor de `tipo` en el metadata del chunk
3. Correr `scripts/ingest.py`
4. Si la nueva categoría necesita un intent propio en el router, actualizar `app/router.py`
5. Documentar la nueva categoría en la tabla de la sección 2 de este archivo
