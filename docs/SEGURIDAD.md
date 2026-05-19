# SEGURIDAD.md
## RAG Personal · Gastón Blanco

> Reglas de seguridad del proyecto. Actualizar si cambia la exposición del endpoint
> o se agregan nuevas credenciales.

---

## Índice

1. [API keys y variables de entorno](#1-api-keys)
2. [Exposición del endpoint](#2-exposicion-del-endpoint)
3. [Datos sensibles](#3-datos-sensibles)
4. [Tokens externos](#4-tokens-externos)
5. [Checklist antes de hacer deploy](#5-checklist)

---

## 1. API keys y variables de entorno

**Regla:** ninguna credencial en el código. Todo en `.env`. El archivo `.env` nunca se commitea.

```bash
# .env — nunca commitear
DEEPSEEK_API_KEY=
GITHUB_TOKEN=
HF_TOKEN=
CHROMA_HOST=chroma
CHROMA_PORT=8000
OLLAMA_HOST=ollama
OLLAMA_PORT=11434
MODEL_PROVIDER=deepseek
MODEL_NAME=deepseek-chat
```

El archivo `.env.example` documenta las variables necesarias sin valores —
ese sí va al repositorio.

---

## 2. Exposición del endpoint

**MVP:** endpoint sin autenticación.
Aceptable porque el sistema solo responde con información que Gastón
eligió poner en la knowledge base — no hay datos privados expuestos.

**Riesgos monitoreados:**

| Riesgo | Mitigación MVP |
|---|---|
| Abuso (muchas queries = costo DeepSeek) | Rate limiting con slowapi |
| Prompt injection | Prompt template restringe estrictamente al contexto |

**Para v2 si se expone públicamente:**
- API key simple para el endpoint
- Rate limit por IP más estricto

---

## 3. Datos sensibles

**Qué NO va en ChromaDB:**
- Email, teléfono u otro dato de contacto directo
- Datos de clientes del WhatsApp Bot
- Información salarial específica

**Qué SÍ va:**
- Todo lo que ya aparece en el CV público
- Proyectos públicos con sus decisiones técnicas
- Orientación profesional que Gastón quiere comunicar

---

## 4. Tokens externos

- Usar tokens con permisos mínimos — solo lectura de repos/modelos públicos
- Rotar si se exponen accidentalmente
- Nunca loguear tokens en output del servidor ni en logs de Docker

---

## 5. Checklist antes de hacer deploy

- [ ] `.env` no está en el repositorio (verificar `.gitignore`)
- [ ] `.env.example` tiene todas las variables sin valores
- [ ] ChromaDB y Ollama no tienen puertos expuestos al exterior en `docker-compose.yml`
- [ ] Rate limiting activo en FastAPI
- [ ] Tokens de GitHub y HuggingFace con permisos de solo lectura
- [ ] No hay credenciales hardcodeadas en ningún archivo de código
