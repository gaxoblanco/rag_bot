# Estado de contenedores
docker compose -f docker/docker-compose.yml ps

# Puerto 8080 cerrado al exterior
iptables -L INPUT -n | grep 8080
# Debe mostrar: ACCEPT 127.0.0.1 + DROP 0.0.0.0/0

# HTTPS activo
curl https://rag.gaxoblanco.com/health

# Dashboard accesible públicamente
curl https://rag.gaxoblanco.com/

# Playground responde (sin API key)
curl -X POST https://rag.gaxoblanco.com/playground \
  -d "question=hola"

# Certificado SSL — fecha de vencimiento
certbot certificates

# Renovación automática (certbot la hace solo, pero verificar)
systemctl status snap.certbot.renew.timer