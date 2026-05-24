# Stack Tecnológico — Contexto de uso real
## Categoría: stack_tecnologico

> Solo tecnologías con contexto real de proyecto documentado.
> Este archivo crece a medida que se agregan nuevos proyectos.

Mis tecnologías principales son Python, JavaScript, TypeScript, Docker, Jupyter Notebook, React,
Angular, FastAPI, Flask, spaCy, LangChain, ChromaDB, Redis, SQLite, MySQL.
En ML/AI: LangChain, ChromaDB, Ollama, HuggingFace Inference API, spaCy, RAGAS.
Front-end: React, Angular, HTML, CSS, SASS, Storybook.
Herramientas: Docker, Git, Figma, VS Code.

Tecnologías que no manejo: Java, Kotlin, Swift, C#, .NET, Ruby, Go, Rust,
Vue, Svelte, GraphQL (cliente), Kubernetes, AWS, GCP, Azure.
PHP lo usé en proyectos anteriores pero no es parte de mi stack actual.

Preguntas frecuentes sobre mi stack: ¿qué tecnologías usás? ¿qué lenguajes manejás?
¿cuál es tu stack? ¿con qué trabajás? ¿sabés Python? ¿usás Docker? ¿qué frameworks conocés?

---

## Python

El lenguaje principal para todo lo relacionado con ML y backend.

Usado en el WhatsApp Booking Bot como lenguaje central del sistema —
Flask, spaCy, Google Calendar integration, Redis, SQLite, APScheduler.
También en Lineup para el pipeline completo de OCR + Spotify API.
Y en la serie de interpretabilidad para XGBoost, SHAP, LIME y análisis de CNNs.
Y en el rag_bot — FastAPI, LangChain, ChromaDB, HuggingFace Inference API.

No es un lenguaje que aprendí en un curso y apliqué una vez —
es la herramienta con la que construyo sistemas que corren en producción.

---

## Docker

Aprendido por necesidad real, no por curiosidad.

En That Day in London los conflictos de dependencias con XAMPP y otras librerías
consumían tiempo constantemente. Esa experiencia fue el origen directo del interés
en Docker — aprender a conteneirizar para nunca más depender de que el entorno
local funcione de una manera específica.

Hoy Docker es parte natural de cualquier proyecto:
el WhatsApp Bot corre en Docker con arquitectura multi-contenedor,
con el servicio ML separado del bot para mantener cada imagen liviana.
Lineup también se deployó con Docker. El rag_bot corre en Docker Compose
con tres contenedores: API, ChromaDB y Ollama.

---

## FastAPI

Framework backend del rag_bot — sistema RAG personal en producción.
Maneja los endpoints de la API (`/ask`, `/playground`, `/health`),
el dashboard público con Jinja2 + HTMX, y el rate limiting via slowapi.

Elegido sobre Flask para el rag_bot por su tipado con Pydantic,
validación automática de requests/responses, y documentación auto-generada.

---

## LangChain + ChromaDB + Ollama

Stack completo del rag_bot — sistema RAG personal en producción.

LangChain 0.3 como orquestador del pipeline RAG.
ChromaDB 0.6.3 como base vectorial — corriendo en contenedor separado
con volumen persistente para que los datos sobrevivan reinicios.
Ollama con nomic-embed-text para embeddings locales sin costo.
HuggingFace Inference API con Llama 3.1 8B como LLM en producción.

---

## spaCy

El modelo de clasificación de intenciones del WhatsApp Booking Bot
fue entrenado desde cero con spaCy 3.7.2 (TextCatEnsemble).

El proceso completo: generación de ~1.050 ejemplos sintéticos con pipeline
de data augmentation propio, entrenamiento, evaluación, y deploy como
servicio independiente en Docker. Resultado: 99.2% de accuracy.

La decisión de usar spaCy en lugar de un LLM fue técnica y económica:
un modelo propio no tiene costo variable por token, es predecible,
y se puede correr en el servidor sin dependencia de servicios externos.

---

## Flask

Framework backend del WhatsApp Booking Bot.
Maneja el webhook de Twilio, el webhook de Google Calendar,
y expone los endpoints internos del sistema.

Elegido por su simplicidad para proyectos donde el framework
no necesita ser el protagonista — la lógica de negocio es lo que importa.

---

## Redis

Usado en el WhatsApp Booking Bot para gestión de estado de sesión
por usuario con TTL de 30 minutos.

El sistema tiene fallback en memoria si Redis no está disponible,
lo que garantiza que el bot sigue funcionando ante una caída del servicio.
También se usa como base para el rate limiter con ventana deslizante.

---

## Twilio (WhatsApp API)

Integración completa en el WhatsApp Booking Bot —
mensajería bidireccional, templates aprobados para recordatorios
y ofertas de lista de espera, y configuración del webhook para
recibir mensajes entrantes.

---

## Google Calendar API

Integración profunda en el WhatsApp Booking Bot usando Service Account
(no OAuth de usuario): disponibilidad en tiempo real, creación y cancelación
de turnos, notificaciones push via watch channels, y sincronización
diaria via CRON. El profesional no necesita tocar el bot —
gestiona todo desde su Google Calendar de siempre.

---

## React

Usado en That Day in London para una plataforma logística —
web app compartiendo capa de datos con la versión mobile via Redux.
El front de ambas plataformas fue desarrollado por Gastón.

---

## React Native

Mobile app de la plataforma logística de That Day in London,
desarrollada en paralelo con la web en React, compartiendo
el mismo estado via Redux. Incluía OCR para escanear órdenes
de entrega en tiempo real.

---

## Redux

Capa de estado compartida entre la web en React y la app
en React Native en el proyecto logístico de That Day in London.
Permitió que ambas plataformas mostraran la misma información
en tiempo real sin duplicar lógica de datos.

---

## Angular

Usado en Lineup para el front-end con Angular Standalone Components —
la decisión de usar Standalone Components fue intencional para
mantener el bundle liviano y evitar la complejidad de NgModules
en un proyecto de una sola feature principal.

---

## TypeScript

Usado en proyectos frontend modernos. Base natural cuando se trabaja
con Angular (que lo usa por defecto) y en proyectos React donde
el tipado agrega valor real en equipos o codebases que crecen.

---

## Storybook

Uno de los trabajos más interesantes de That Day in London.
Se armó el sistema de componentes completo en Storybook integrado con Drupal
para Bimbo México, basado en atomic design y traducido desde el Figma del cliente.

El objetivo era que el equipo pudiera crear nuevos contenidos manteniendo
consistencia visual sin empezar de cero cada vez.
Un sistema pensado para escalar — no una solución puntual.

---

## OCR

Dos usos distintos con decisiones técnicas diferentes:

En That Day in London: OCR para escanear órdenes de entrega en la app logística.

En Lineup: en lugar de usar un modelo de imagen general (que pesaba más de 8GB de VRAM),
se eligió un modelo OCR especializado en texto tipográfico — mayor precisión
en pósters de festivales con una fracción del cómputo. Se agregó un sistema
de corrección para nombres de bandas con más de tres palabras,
reduciendo errores en un 80%.

---

## Spotify API

Usada en Lineup para buscar artistas por nombre y recuperar su top de canciones.
El pipeline completo corre sin input manual: OCR extrae los nombres del póster,
Spotify API recupera las canciones, y la playlist se genera automáticamente.

---

## Figma

Usado en Flextech para diseñar la landing page antes de pasar a código.
El diseño en Figma fue propio — no se partió de un template existente.

El background en Diseño Industrial hace que Figma sea una herramienta
natural, no solo un entregable previo al desarrollo.

---

## HTML / CSS / JavaScript

Base de todo el trabajo front-end desde el inicio.
Usados en Flextech (landing completa), en That Day in London
(múltiples proyectos de clientes), y como fundamento
de cualquier proyecto web posterior.

---

## SASS

Usado en That Day in London para el sistema de diseño
con Storybook y Drupal, siguiendo atomic design principles.
SASS permitió mantener consistencia de estilos a escala
en un sistema de componentes reutilizables.

---

## SQLite

Base de datos del WhatsApp Booking Bot —
almacena profesionales, turnos, lista de espera,
eventos de conversación y estado del sistema.

Elegido por simplicidad operativa en un sistema donde
el volumen de datos no justifica la complejidad de un motor más pesado.

---

## MySQL

Base de datos relacional usada en el proyecto final de Codo a Codo (2023) —
plataforma de venta de entradas con sistema de autenticación.
Es la experiencia principal en bases de datos relacionales.

---

## PHP

Usado en Flextech para la lógica del servidor y configuración
del servicio de correos de la landing page.
También base del título de Codo a Codo (2023).
No es parte del stack actual — mencionado por completitud histórica.