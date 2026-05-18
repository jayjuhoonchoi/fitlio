#!/usr/bin/env bash
# Install certbot deploy hook: after "certbot renew", reload Fitlio nginx in Docker.
# Run once on EC2 (with sudo).
# Usage: sudo FITLIO_DIR=/home/ubuntu/fitlio ./scripts/install_letsencrypt_deploy_hook.sh
set -euo pipefail

FITLIO_DIR="${FITLIO_DIR:-$HOME/fitlio}"
FITLIO_DIR_Q="$(printf '%q' "${FITLIO_DIR}")"
HOOK_DIR=/etc/letsencrypt/renewal-hooks/deploy
HOOK="${HOOK_DIR}/99-fitlio-nginx.sh"

if [[ "$(id -u)" -ne 0 ]]; then
  echo "Run with sudo"
  exit 1
fi

mkdir -p "$HOOK_DIR"
cat >"$HOOK" <<EOF
#!/bin/sh
set -e
cd ${FITLIO_DIR_Q} || exit 1
if [ -f .fitlio-k8s-alt-ports ]; then
  exec docker compose -f docker-compose.yml -f docker-compose.k8s-alt-ports.yml restart nginx
fi
exec docker compose -f docker-compose.yml restart nginx
EOF
chmod +x "$HOOK"
echo "Installed $HOOK (reloads nginx after renew)."
