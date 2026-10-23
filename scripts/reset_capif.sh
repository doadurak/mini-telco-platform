#!/usr/bin/env bash
# Rebuild CAPIF state after a Docker/WSL restart, then start the full platform.
#
# OpenCAPIF's Vault runs in dev mode (in-memory): after a restart its PKI secrets
# are gone, the register/nginx certificates no longer match, and every provider /
# invoker identity cached by a client is stale. This script recreates OpenCAPIF,
# clears the cached identities and lets start.sh onboard everything again.
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
OPENCAPIF_DIR="${OPENCAPIF_DIR:-$HOME/OpenCAPIF/capif/services}"
NEF_DIR="$PROJECT_DIR/providers/NEF"
NEF_PROVIDER_FOLDER="$NEF_DIR/MonitoringEventAPI/app/provider_onboarding/provider_folder"

echo "[1/5] Recreating OpenCAPIF (clean + run)..."
(cd "$OPENCAPIF_DIR" && bash clean_capif_docker_services.sh -a >/dev/null 2>&1 || true)
{ docker ps -a --format '{{.Names}}' | grep -E '^(services-|helper$|register$)' || true; } | xargs -r docker rm -f >/dev/null
(cd "$OPENCAPIF_DIR" && bash run.sh -b false >/tmp/capif_up.log 2>&1) || echo "  run.sh reported issues (see /tmp/capif_up.log)"

echo "[2/5] Restarting register once Vault PKI is ready..."
sleep 15
docker restart register >/dev/null
for _ in $(seq 1 30); do
  code=$(curl -sk -o /dev/null -w '%{http_code}' -X POST https://localhost:8084/login -u admin:password123 || true)
  [[ "$code" == "200" ]] && break
  sleep 2
done
echo "  register login: HTTP $code"

echo "[3/5] Clearing NEF provider identity (kept as backup) and recreating NEF..."
if [[ -n "$(ls -A "$NEF_PROVIDER_FOLDER" 2>/dev/null)" ]]; then
  mv "$NEF_PROVIDER_FOLDER" "$NEF_PROVIDER_FOLDER.bak-$(date +%Y%m%d%H%M%S)"
  mkdir -p "$NEF_PROVIDER_FOLDER"
fi
(cd "$NEF_DIR" && docker compose -f docker-compose.yaml -f docker-compose.auth.yaml up -d --force-recreate nef >/dev/null 2>&1)

echo "[4/5] Clearing Location provider invoker cache..."
docker exec camara-location-retrieval rm -rf /app/invoker_folder/camara_user 2>/dev/null || true

echo "[5/5] Starting platform (start.sh)..."
bash "$PROJECT_DIR/start.sh"

# start.sh may run the NEF publish step before the recreated NEF is ready (its output is
# silenced). Re-run that idempotent step visibly, then refresh the Location invoker.
echo "[post] Re-running NEF onboarding/publish..."
sed -n "/^docker exec nef python3 - <<'PYEOF'/,/^PYEOF/p" "$PROJECT_DIR/start.sh" | sed '1d;$d' \
  | docker exec -i nef python3 - 2>&1 | grep -E "onboarded|published|publish complete" || true
docker exec camara-location-retrieval rm -rf /app/invoker_folder/camara_user 2>/dev/null || true
