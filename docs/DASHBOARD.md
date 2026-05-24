# DASHBOARD.md
## RAG Personal · Gastón Blanco

> Panel de control público del sistema RAG.
> Sirve como portfolio técnico y permite probar el sistema con preguntas limitadas.
> Última actualización: Mayo 2026

---

## Índice

1. [Objetivo](#1-objetivo)
2. [Arquitectura](#2-arquitectura)
3. [Endpoints nuevos](#3-endpoints)
4. [Seguridad del playground](#4-seguridad)
5. [Estructura de archivos](#5-archivos)
6. [Secciones del dashboard](#6-secciones)
7. [Stack del frontend](#7-stack)
8. [Decisiones de diseño](#8-decisiones)

---

## 1. Objetivo

Reemplazar la página en blanco de `rag.gaxoblanco.com` con un panel de control
que muestra cómo funciona el sistema RAG internamente.

**Audiencia:** recruiters técnicos y clientes potenciales que quieren entender
el sistema antes de contactar.

**Qué muestra:**
- Estado del sistema en tiempo real (chunks, modelo activo)
- Resultados de evaluación RAGAS del golden dataset
- Flujo completo de una query con decisiones técnicas
- Stack tecnológico
- Playground para probar el RAG con preguntas propias (5 por sesión)

**Qué NO muestra:**
- Los chunks recuperados internamente (privado)
- Logs del servidor
- API key
- Endpoint `/ask` — el playground usa `/playground` separado

---

## 2. Arquitectura

```
rag.gaxoblanco.com
        │
        ▼ Nginx → localhost:8080
        │
      FastAPI
        │
        ├── GET  /              → dashboard.html (Jinja2, público)
        ├── POST /playground    → fragmento HTML (HTMX, público, rate limited)
        ├── GET  /health        → JSON status (público, ya existe)
        └── POST /ask           → JSON respuesta (X-API-Key, ya existe)
```

**Sin infraestructura nueva.** Todo corre en el mismo contenedor `gaston-rag-api`.
Nginx no necesita cambios — ya pasa todo a puerto 8080.

---

## 3. Endpoints nuevos

### GET /
Sirve el dashboard como HTML completo.
- Sin autenticación
- Jinja2 template con datos inyectados en el render
- Datos estáticos: chunk counts, scores RAGAS, stack, arquitectura

### POST /playground
Recibe una pregunta, llama a `responder()`, devuelve fragmento HTML.
- Sin autenticación
- Rate limit: **5 requests por día por IP** (slowapi)
- Filtros de input: mismos que `/ask` — longitud, repetición, chars válidos
- Sin historial conversacional — cada pregunta es independiente
- Sin `include_contexts` — no expone chunks al público
- Responde con HTML parcial (fragmento HTMX) no con JSON

**Request:** `application/x-www-form-urlencoded`
```
question=¿qué hace el WhatsApp Booking Bot?
```

**Response:** fragmento HTML
```html
<div class="result-item">
  <div class="result-answer">El WhatsApp Booking Bot es...</div>
  <div class="result-meta">fuentes: chromadb · github</div>
</div>
```

---

## 4. Seguridad del playground

| Capa | Detalle |
|---|---|
| Rate limit | 5 req/día por IP — más restrictivo que `/ask` (20/min) |
| Filtros de input | Longitud máx 200, repetición chars, repetición palabras, regex ES+EN |
| Guardia de entrada | Injection/jailbreak — misma lógica que `/ask` |
| Guardia de relevancia | Off-topic bloqueado |
| Sin contextos expuestos | `include_contexts=False` — los chunks no llegan al browser |
| Sin historial | Cada pregunta es independiente — no acumula sesión |
| Timeout | 30s máximo — si el LLM no responde, error genérico |

**Riesgo económico:** 5 req/día por IP limita el abuso a ~5 tokens HuggingFace
por IP por día. Con IP rotation el riesgo sigue siendo bajo dado el costo
de Llama 3.1 8B en Novita.

---

## 5. Estructura de archivos

```
app/
├── main.py              ← agregar GET / y POST /playground
└── templates/
    └── dashboard.html   ← HTML + HTMX en un solo archivo

requirements.txt         ← agregar python-multipart
```

**Sin carpeta `static/`** — HTMX se carga desde CDN (cdnjs).
El CSS vive dentro del `dashboard.html` en un `<style>` tag.

---

## 6. Secciones del dashboard

### Tab 1 — Playground (tab por defecto)
- Contador visual de preguntas restantes (5 pills)
- Input de texto + botón "preguntar"
- Chips de preguntas sugeridas (clickeables)
- Área de resultados — las respuestas aparecen arriba, apiladas
- Cada resultado muestra: pregunta, respuesta, fuentes usadas, badge ok/bloqueado

### Tab 2 — Métricas
- Cards con números clave: chunks, faithfulness, answer_relevancy, preguntas evaluadas
- Barras de score por pregunta del golden dataset
- Lista de fuentes con chunk counts

### Tab 3 — Arquitectura
- Flujo paso a paso de una query con íconos
- Cada paso muestra qué hace y los parámetros clave

### Tab 4 — Stack
- Tecnologías agrupadas por categoría
- Chips con versiones exactas

---

## 7. Stack del frontend

| Componente | Tecnología | Por qué |
|---|---|---|
| Templates | Jinja2 | Ya incluido en FastAPI, datos del servidor en el HTML |
| Interactividad | HTMX 1.9 | Sin JS propio — requests al servidor con atributos HTML |
| CSS | Inline en el template | Sin archivos estáticos, un solo archivo |
| Íconos | Tabler Icons (CDN) | Consistente con el diseño del Artifact |
| Fuentes | System fonts | Sin dependencias externas |

**Sin JavaScript propio.** HTMX maneja toda la interactividad
con atributos `hx-post`, `hx-target`, `hx-swap`.

---

## 8. Decisiones de diseño

**¿Por qué HTMX en lugar de JS puro?**
Un solo stack — la lógica de interacción vive en el servidor Python,
no distribuida entre frontend y backend. El template HTML describe
el comportamiento, FastAPI lo ejecuta.

**¿Por qué no React/Vue?**
El dashboard es parte del proyecto RAG, no un proyecto frontend separado.
Agregar un bundler y un framework JS sería infraestructura nueva
para un panel de control simple.

**¿Por qué 5/día y no 5/min?**
Por minuto permite hacer 5 preguntas, esperar 60 segundos, y repetir.
Por día es más restrictivo y tiene más sentido como límite de demo.

**¿Por qué no exponer los chunks?**
Los chunks son la knowledge base privada del sistema — mostrarlos
revelaría todo el contenido de `data/` sin necesidad.
Las fuentes (nombres de archivo) son suficientes para entender
de dónde vino la respuesta.

**¿Por qué tab "playground" primero?**
La primera impresión es interactiva — el visitante prueba antes de leer.
Un recruiter técnico que puede hacer preguntas es más memorable
que un dashboard de métricas.
