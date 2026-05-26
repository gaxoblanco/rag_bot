# Sobre este sistema — Portfolio de Gastón Blanco
## Categoría: general

Esta página es el portfolio técnico interactivo de Gastón Blanco,
desarrollador Fullstack especializado en ML/AI.

Tiene dos partes que coexisten y se complementan:

**1. El RAG** — este sistema de conversación. Podés hacerme cualquier pregunta
sobre mi perfil, proyectos, stack, experiencia o decisiones técnicas.
Respondo en tiempo real consultando mi knowledge base real.

**2. Viner** — el WhatsApp Booking Bot. Cuando termines de explorar mi perfil
y quieras agendar un meet, lo hacés directamente desde WhatsApp.
Viner gestiona la agenda automáticamente — elegís horario, confirmás,
y listo. Sin emails de ida y vuelta.

El flujo es: preguntás todo lo que necesitás saber → cuando estés listo,
agendamos una charla directamente por WhatsApp.

Preguntas frecuentes sobre esta página: qué es esto, de qué trata esta página,
qué puedo preguntar, cómo funciona, qué es un RAG, quién sos, qué hacés,
para qué sirve esto, qué información tenés, cómo agendo una reunión,
cómo me contacto, cómo funciona el sistema, qué proyectos tenés acá.

---

## El RAG — cómo funciona

Cuando hacés una pregunta, el sistema:

1. Detecta si es relevante para el perfil
2. Busca en ChromaDB los chunks más relevantes de la knowledge base
3. Consulta GitHub en tiempo real si preguntás sobre repositorios
4. Construye un prompt con ese contexto
5. Llama a Llama 3.1 8B via HuggingFace Inference API
6. Valida que la respuesta sea sobre el perfil antes de enviártela

Todo el código es open source. El sistema mismo es uno de mis proyectos —
pipeline RAG completo con evaluación RAGAS, 158 tests unitarios y deploy en producción.

---

## Viner — el WhatsApp Bot para agendar

Viner es el sistema de gestión de turnos que uso para que los visitantes
puedan agendar un meet conmigo directamente desde WhatsApp.

Cuando querés hablar, mandás un mensaje y Viner gestiona todo:
disponibilidad en tiempo real, confirmación, recordatorios.
Sin intermediarios, sin emails, sin formularios.

Es también uno de mis proyectos en producción — construido con Python,
spaCy entrenado con 99.2% de accuracy, Flask, Redis, Google Calendar API,
Twilio y arquitectura multi-tenant con Docker.

---

## Por qué existe este portfolio

Construí este sistema para demostrar en la práctica lo que sé hacer,
no solo listarlo en un CV. Si estás evaluando si trabajamos juntos,
esta conversación ya es parte de la evaluación — estás viendo el RAG en acción.
