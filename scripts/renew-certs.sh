#!/bin/bash
# Certbot auto-renewal script (add to crontab: 0 3 * * 1 /path/to/renew-certs.sh)
set -e
cd "$(dirname "$0")/.."
docker compose run --rm certbot renew --quiet
docker compose exec nginx nginx -s reload
echo "[$(date)] Certificate renewal check complete."
