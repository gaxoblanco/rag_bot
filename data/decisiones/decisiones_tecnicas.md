# Decisiones Técnicas
## Categoría: decision_tecnica

> Decisiones técnicas relevantes extraídas de los proyectos documentados.
> Este archivo crece con cada proyecto nuevo.

---

## No usar LLM en el WhatsApp Booking Bot

**Contexto:** sistema conversacional para gestión de turnos médicos en producción.

**Alternativas consideradas:**
- LLM externo (GPT, Claude, etc.) via API
- Modelo de clasificación de intenciones propio con spaCy

**Decisión:** spaCy entrenado desde cero.

**Razón:** un LLM implica costo variable por cada token generado, multiplicado
por cada mensaje de cada paciente de cada centro de salud onboardeado.
En un sistema multi-tenant con uso constante, ese costo no escala bien.
Un modelo propio tiene costo fijo de servidor, es predecible en su comportamiento,
y no depende de servicios externos para funcionar.

**Resultado:** 99.2% de accuracy, sin costo variable, corriendo en el servidor propio.

---

## OCR especializado vs modelo de imagen general en Lineup

**Contexto:** extraer nombres de artistas de un póster de festival para generar una playlist.

**Alternativas consideradas:**
- Modelo de visión general — alta precisión, pero +8GB de VRAM
- Modelo OCR especializado en texto tipográfico — más liviano, más específico

**Decisión:** OCR especializado.

**Razón:** el modelo de imagen general no entraba en la notebook de desarrollo
y en producción implicaba un costo de cómputo que no se justificaba para esta tarea.
Un póster de festival es texto tipográfico — exactamente el caso de uso
para el que un OCR especializado está optimizado.

**Resultado:** mayor precisión en layouts tipográficos con una fracción del cómputo.
Se agregó un sistema de corrección para nombres con más de tres palabras
que redujo errores en un 80%.

---

## Arquitectura multi-tenant del servicio ML en el WhatsApp Bot

**Contexto:** múltiples instancias del bot (un centro de salud por instancia)
necesitan clasificar intenciones.

**Alternativas consideradas:**
- Incluir el modelo spaCy dentro de cada contenedor de bot
- Separar el servicio ML en un contenedor independiente

**Decisión:** contenedor ML independiente, compartido por todas las instancias.

**Razón:** incluir el modelo en cada contenedor de bot encarece cada instancia
y complica las actualizaciones del modelo — habría que reconstruir todos los contenedores.
Un servicio ML separado se actualiza una vez y sirve a todos.
Cada contenedor de bot se mantiene liviano.

---

## Docker como estándar de desarrollo — origen de la decisión

**Contexto:** en That Day in London, los conflictos de dependencias con XAMPP
y otras librerías consumían tiempo constantemente en el entorno local.

**Decisión:** aprender Docker y adoptarlo como estándar en todos los proyectos siguientes.

**Razón:** no fue una decisión teórica — fue la respuesta directa a un problema
concreto sufrido de primera mano. Un entorno conteneirizado elimina
la categoría completa de bugs de "funciona en mi máquina".

**Impacto:** todos los proyectos posteriores usan Docker desde el inicio.

---

## Sistema de tonos configurable por variable de entorno en el WhatsApp Bot

**Contexto:** diferentes clientes (salud, psicología, belleza, legal) necesitan
que el bot hable con una voz distinta, pero el codebase es el mismo.

**Decisión:** capa de mensajes configurable via `TENANT_TONE` en el entorno.

**Razón:** mantener un codebase único que sirva a múltiples verticales
sin duplicar lógica. El tono es configuración, no código.

**Resultado:** nuevos clientes se onboardean cambiando variables de entorno,
sin tocar el sistema central.

---

## ChromaDB en contenedor separado vs embedded en el rag_bot

**Contexto:** sistema RAG personal que necesita persistir una knowledge base vectorial
entre reinicios de la API.

**Alternativas consideradas:**
- ChromaDB embedded — corre dentro del mismo proceso de la API
- ChromaDB en contenedor Docker separado con volumen persistente

**Decisión:** ChromaDB en contenedor separado.

**Razón:** con ChromaDB embedded, los datos vectoriales viven en el mismo ciclo
de vida que la API — si la API se reinicia o se reconstruye la imagen, se pierde
la knowledge base. Un contenedor separado con volumen persistente hace que los datos
sobrevivan independientemente de lo que pase con el contenedor de la API.
Además permite re-ingestar sin reiniciar el servidor.

**Resultado:** la knowledge base persiste entre deploys. El comando
`docker compose down` baja los contenedores pero no toca los volúmenes.

---

## HuggingFace Inference API vs Ollama local para LLM en producción en el rag_bot

**Contexto:** el VPS de producción (Donweb, 4GB RAM) no tiene GPU.
Necesitaba un LLM para generar respuestas en el sistema RAG.

**Alternativas consideradas:**
- Ollama con llama3.1:8b corriendo en el VPS (CPU)
- HuggingFace Inference API via Novita como proveedor externo

**Decisión:** HuggingFace Inference API con Llama-3.1-8B-Instruct via Novita.

**Razón:** correr llama3.1:8b en CPU en un VPS de 4GB RAM implica
tiempos de respuesta de varios minutos por query — inaceptable para producción.
La API de HuggingFace corre el modelo en sus servidores con GPU,
devuelve respuesta en ~2 segundos, y no tiene costo fijo.
Ollama se mantiene en el stack solo para embeddings (nomic-embed-text),
donde la latencia no es crítica.

**Resultado:** ~2 segundos de respuesta en producción sin GPU local.
Costo variable por uso, sin infraestructura adicional.

---

## InferenceClient directo vs ChatHuggingFace en el rag_bot

**Contexto:** integrar el LLM de HuggingFace en la chain de LangChain.

**Alternativas consideradas:**
- `ChatHuggingFace` de langchain-huggingface
- `InferenceClient` directo de huggingface-hub con clase LLM custom

**Decisión:** `InferenceClient` directo con clase LLM custom.

**Razón:** `ChatHuggingFace` intenta descargar el tokenizador del modelo
al inicializarse. Llama-3.1-8B-Instruct es un modelo gated — requiere
aceptar términos en HuggingFace. La descarga del tokenizador falla con 403
aunque el token tenga acceso a la Inference API.
`InferenceClient` directo llama solo al endpoint de inferencia
sin intentar descargar nada localmente.

**Resultado:** inicialización sin errores, llamadas a la API funcionando correctamente.