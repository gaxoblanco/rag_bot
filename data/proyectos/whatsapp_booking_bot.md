# Viner — WhatsApp Booking Bot en producción
Categoría: proyecto_detalle — Período: Noviembre 2025 — Presente (en producción con clientes reales)

Viner es el sistema de gestión de turnos vía WhatsApp que desarrollé y opero.
Lanzado en noviembre de 2025. En producción con clientes reales desde noviembre 2025.
Fecha de lanzamiento: noviembre 2025.
Gestiona reservas, recordatorios, lista de espera y sincronización con Google Calendar
para profesionales de salud, psicología, legal, fitness y belleza.
Stack: Python, Flask, spaCy entrenado (99.2% accuracy), Redis, SQLite, Twilio,
Google Calendar API, Docker multi-tenant. Sin LLMs — modelo propio de clasificación.

En este portfolio Viner cumple dos roles: es uno de mis proyectos técnicos más
complejos, y es también la herramienta que uso para que los visitantes agenden
un meet conmigo directamente por WhatsApp.

Preguntas frecuentes sobre Viner: qué es Viner, cómo funciona el bot,
por qué no usaste un LLM, cómo está construido, qué tecnologías usa el WhatsApp bot,
qué es el booking bot, cómo agendo una reunión, cómo me contacto,
el bot de WhatsApp, viner.gaxoblanco.com, cuándo lanzaste Viner, fecha de lanzamiento,
desde cuándo está en producción, cuándo empezaste Viner.

---

## El origen

Todo empezó cuando una amiga pidió ayuda para crear una comunidad por WhatsApp
donde compartir información con sus colegas y conseguir más pacientes.

Fue interesante, pero quedé con ganas de ir más lejos. Si iba a construir algo
sobre WhatsApp, quería aprender a usar un modelo de ML de intención real —
no solo conectar mensajes con respuestas fijas. Y si entrenaba ese modelo,
podía construir algo que tuviera valor real: un sistema de gestión de agenda
para profesionales de la salud, operado completamente por WhatsApp.

Así nació el bot. El proyecto de la amiga fue la chispa; el sistema de turnos
fue la excusa para aprender a fondo.

---

## Qué hace el sistema

Un bot conversacional completo para gestión de turnos — agnóstico de industria.
Funciona para cualquier profesional o negocio que maneje agenda: salud, legal,
fitness, belleza, consultoría, o cualquier vertical que necesite reservas.

Los usuarios pueden buscar disponibilidad en tiempo real, reservar, cancelar
y reprogramar turnos — todo desde WhatsApp, sin descargar ninguna app adicional.

Los profesionales gestionan su agenda a través de Google Calendar: el bot
sincroniza automáticamente, envía recordatorios, maneja lista de espera
cuando hay cancelaciones, y permite importar disponibilidad desde CSV o Excel.

Está en producción con clientes reales desde noviembre de 2025.

---

## La decisión más importante: no usar un LLM

Conectar un LLM implicaba un costo fijo por cada token generado, más el costo
de la API de WhatsApp, más Twilio, más el servidor. Para un servicio que atiende
múltiples centros de salud simultáneamente, eso no escala bien en costos.

La alternativa fue entrenar un modelo de clasificación de intenciones propio con spaCy.
Un modelo chico, entrenado desde cero con datos propios, corriendo en el servidor.

El resultado: 99.2% de accuracy en detección de intenciones, sin costo variable
por token, y sin dependencia de servicios externos de IA.

---

## Arquitectura multi-tenant

El servicio ML corre en un contenedor Docker dedicado e independiente del bot.
Múltiples instancias del bot pueden consultar al mismo modelo simultáneamente —
cada contenedor de bot se mantiene liviano, y el modelo sirve a todos.

Esto permite onboardear nuevos clientes (centros de salud, psicólogos, clínicas)
sin escalar la infraestructura de ML. Solo se agrega una nueva instancia de bot.

---

## El modelo de ML

- Framework: spaCy 3.7.2 con TextCatEnsemble
- Dataset: ~1.050 ejemplos sintéticos generados con pipeline de data augmentation propio
- Accuracy: 99.2%
- Lógica híbrida: ML como primario, reglas como fallback para casos edge
- El modelo corre en el servidor — sin latencia de API externa

Entrenar el modelo desde cero, generar los datos sintéticos, y diseñar
el pipeline de augmentation fue la parte técnicamente más exigente del proyecto.

---

## Sistema de tonos multi-tenant

El mismo codebase puede hablar con voz distinta según el cliente.
Un centro de salud formal usa un tono aspiracional; una clínica de barrio
puede usar un tono más coloquial y cercano.

El tono se configura por variable de entorno (`TENANT_TONE`).
Nuevos verticales — salud, legal, fitness, belleza — se onboardean
sin tocar la lógica central del bot.

---

## Integraciones

**Google Calendar (Service Account):**
- Disponibilidad en tiempo real
- Creación y cancelación de turnos
- Notificaciones push via watch channels
- Sincronización diaria via CRON

**Twilio WhatsApp API:**
- Mensajería bidireccional
- Templates aprobados para recordatorios y ofertas de lista de espera

**Redis:**
- Estado de sesión por usuario (TTL 30 min)
- Fallback en memoria si Redis no está disponible
- Rate limiter con ventana deslizante para control de spam

---

## Funcionalidades destacadas

- **Lista de espera:** cuando un turno se cancela, el sistema ofrece el slot
  automáticamente a los pacientes en lista de espera en cascada
- **Recordatorios automáticos:** el bot recuerda el turno al paciente
  y procesa su confirmación o cancelación
- **Importación de agenda:** los profesionales pueden cargar su disponibilidad
  desde CSV o Excel directamente por WhatsApp
- **Contexto conversacional entre sesiones:** el sistema recuerda el estado
  de cada conversación aunque el usuario no haya respondido durante horas

---

## Stack completo

- Python 3.10 + Flask
- spaCy 3.7.2 (modelo propio entrenado)
- Twilio WhatsApp API
- Google Calendar API (Service Account)
- Redis 7 (sesiones con TTL)
- SQLite (base de datos)
- Docker + Docker Compose
- APScheduler (7 jobs CRON diarios)

---

## Lo que dejó este proyecto

El bot demostró que es posible construir un sistema de IA conversacional
en producción sin depender de LLMs — con un modelo propio entrenado,
más barato de operar, más predecible en su comportamiento, y sin costo variable
por cada interacción.

El sistema es generalista desde el arranque: el mismo codebase sirve cualquier
vertical que maneje agenda. Salud fue el primer cliente, pero la arquitectura
no asume nada del dominio — el tono, los mensajes y la lógica de negocio
se configuran por variable de entorno sin tocar el código central.

También es el proyecto donde más claramente se ve la diferencia entre
construir un demo y construir un sistema: gestión de errores, fallbacks,
rate limiting, anti-spam, sincronización de estado, múltiples roles de usuario,
y onboarding de nuevos clientes sin tocar el código central.