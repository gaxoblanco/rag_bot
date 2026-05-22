# SEGURIDAD.md
## RAG Personal · Gastón Blanco

> Reglas de seguridad del proyecto. Actualizar si cambia la exposición del endpoint
> o se agregan nuevas credenciales.
> Última actualización: Mayo 2026 — deploy en producción completado.

---

## Índice

1. [API keys y variables de entorno](#1-api-keys)
2. [Capas de seguridad activas](#2-capas-de-seguridad)
3. [Datos sensibles](#3-datos-sensibles)
4. [Tokens externos](#4-tokens-externos)
5. [Checklist de mantenimiento](#5-checklist)

---

## 1. API keys y variables de entorno

**Regla:** ninguna credencial en el código. Todo en `.env`. El archivo `.env` nunca se commitea.

```bash
# .env — nunca commitear
USER_RAG_API_KEY=        # API key del endpoint — requerida en X-API-Key header
GITHUB_TOKEN=              # solo lectura de repos públicos
HF_TOKEN=                  # HuggingFace Inference API (Novita/Llama 3.1)
CHROMA_HOST=chroma
CHROMA_PORT=8000
OLLAMA_HOST=ollama
OLLAMA_PORT=11434
MODEL_PROVIDER=huggingface
MODEL_NAME=meta-llama/Llama-3.1-8B-Instruct
```

---

## 2. Capas de seguridad activas

El endpoint está expuesto públicamente en `https://xxxx.xxxx.com`.
Las siguientes capas protegen el sistema en orden de ejecución:

### Capa de red
| Mecanismo | Detalle |
|---|---|
| HTTPS (TLS) | Nginx + Let's Encrypt — tráfico encriptado entre cliente y servidor |
| Puerto 8080 cerrado | iptables DROP desde exterior — solo 127.0.0.1 puede acceder directo |
| Nginx reverse proxy | El contenedor de la API nunca está expuesto al exterior directamente |

### Capa de aplicación
| Mecanismo | Detalle |
|---|---|
| `X-API-Key` header | `secrets.compare_digest` — evita timing attacks |
| Rate limit | 20 req/min por IP via slowapi |
| Filtro de input | Longitud máx 200 chars, repetición de chars/palabras, regex chars válidos ES+EN |
| Guardia de entrada | Injection/jailbreak en ES + EN — ~40 keywords |
| Guardia de relevancia | Off-topic sin keywords de perfil — bloquea preguntas genéricas de internet |
| Guardia de salida | Valida que la respuesta contenga keywords del perfil |

### Flujo de una request rechazada
```
Request
   ├── Sin X-API-Key → 401
   ├── Rate limit superado → 429
   ├── Input inválido (longitud/repetición/chars) → blocked: true
   ├── Injection/jailbreak detectado → blocked: true
   ├── Off-topic sin relación con perfil → blocked: true
   └── Respuesta fuera de foco → blocked: true
```

Todas las respuestas rechazadas devuelven el mismo mensaje genérico
para no revelar qué capa disparó el bloqueo.

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
- `HF_TOKEN` tiene acceso a Inference API — rotar si hay uso anómalo

---

## 5. Checklist de mantenimiento

Para verificar el estado del sistema en producción:

```bash
# Estado de contenedores
docker compose -f docker/docker-compose.yml ps

# Puerto 8080 cerrado al exterior
iptables -L INPUT -n | grep 8080
# Debe mostrar: ACCEPT 127.0.0.1 + DROP 0.0.0.0/0

# HTTPS activo
curl https://rag.gaxoblanco.com/health

# Certificado SSL — fecha de vencimiento
certbot certificates

# Renovación automática (certbot la hace solo, pero verificar)
systemctl status snap.certbot.renew.timer
```

**Ante un incidente:**
1. Rotar `USER_RAG_API_KEY` en `.env` y reiniciar el contenedor
2. Si se expuso `HF_TOKEN`, rotarlo en HuggingFace → Settings → Tokens
3. Si se expuso `GITHUB_TOKEN`, rotarlo en GitHub → Settings → Developer settings