#!/bin/bash
# Let's Encrypt certificate initialization script
# Usage: ./scripts/init-letsencrypt.sh your-domain.com admin@your-domain.com

set -e

DOMAIN=${1:?Usage: $0 <domain> <email>}
EMAIL=${2:?Usage: $0 <domain> <email>}
DATA_PATH="./certbot"

echo "### Creating directories..."
mkdir -p "$DATA_PATH/conf" "$DATA_PATH/www"

echo "### Requesting Let's Encrypt certificate for $DOMAIN..."
docker compose run --rm certbot certonly \
    --webroot \
    --webroot-path=/var/www/certbot \
    --email "$EMAIL" \
    --agree-tos \
    --no-eff-email \
    -d "$DOMAIN"

echo "### Certificate obtained! Update nginx/default.conf:"
echo "  1. Uncomment the HTTPS server block"
echo "  2. Replace 'your-domain.com' with '$DOMAIN'"
echo "  3. Uncomment 'return 301' in the HTTP block"
echo "  4. Run: docker compose restart nginx"
