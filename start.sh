#!/usr/bin/env bash
# =============================================================================
# start.sh — Full mini-telco-platform startup
#
# Startup order:
#   1. OpenCAPIF stack   (nginx, capifcore, register, vault, mongo_register)
#   2. NEF stack         (mongo, nef-monitoring, test_server, core_crowler)
#   3. NEF-QoS           (3GPP AsSessionWithQoS adapter, port 8585)
#   4. camara-QoD        (CAMARA QoD provider, port 8002)
#   5. CamaraLocationRetrieval (CAMARA Location provider, port 8003→8080)
#   6. mini-telco-backend (our AI orchestrator, port 8000)
#   7. CAPIF Setup       (create camara_user, publish NEF APIs, onboard invoker)
#
# Usage:
#   ./start.sh           # start all services
#   ./start.sh --stop    # stop all services
#   ./start.sh --status  # show running containers
# =============================================================================

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

OPENCAPIF_DIR="/home/turkad/OpenCAPIF/capif/services"
NEF_DIR="$SCRIPT_DIR/providers/NEF"
NEF_QOS_DIR="$SCRIPT_DIR/providers/NEF-QoS"
CAMARA_QOD_DIR="$SCRIPT_DIR/providers/camara-QoD"
CAMARA_LOC_DIR="$SCRIPT_DIR/providers/CamaraLocationRetrieval"
BACKEND_DIR="$SCRIPT_DIR"

GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log()   { echo -e "${GREEN}[✓]${NC} $*"; }
info()  { echo -e "${CYAN}[→]${NC} $*"; }
warn()  { echo -e "${YELLOW}[!]${NC} $*"; }
error() { echo -e "${RED}[✗]${NC} $*"; }

wait_for_port() {
    local name=$1 host=$2 port=$3 retries=${4:-20} delay=${5:-3}
    info "Waiting for $name on $host:$port ..."
    for i in $(seq 1 "$retries"); do
        if nc -z "$host" "$port" 2>/dev/null; then
            log "$name is up!"
            return 0
        fi
        sleep "$delay"
    done
    warn "$name did not respond on $host:$port after ${retries} attempts — continuing anyway"
    return 0
}

# ─── STOP mode ───────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--stop" ]]; then
    echo -e "${RED}Stopping all mini-telco-platform services...${NC}"
    docker stop mini-telco-backend-capif 2>/dev/null && log "backend stopped"    || true
    docker stop camara-qod              2>/dev/null && log "camara-qod stopped"  || true
    docker stop camara-location-retrieval 2>/dev/null && log "camara-loc stopped" || true
    docker stop nef-qos                 2>/dev/null && log "nef-qos stopped"     || true
    (cd "$NEF_DIR" && docker compose down 2>/dev/null && log "NEF stack stopped") || true
    echo ""
    warn "OpenCAPIF stack NOT stopped (use OpenCAPIF run.sh to manage it)"
    echo ""
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null
    exit 0
fi

# ─── STATUS mode ─────────────────────────────────────────────────────────────
if [[ "${1:-}" == "--status" ]]; then
    docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
    exit 0
fi

# ─── START mode ──────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  mini-telco-platform — Full Stack Startup"
echo "  CAMARA + OpenCAPIF + FRONT-research-group providers"
echo "═══════════════════════════════════════════════════════"
echo ""

# 1. capif-network
info "Ensuring capif-network exists..."
docker network create capif-network 2>/dev/null && log "capif-network created" || log "capif-network already exists"

# 2. OpenCAPIF
info "Starting OpenCAPIF stack..."
if docker ps --format '{{.Names}}' | grep -q "^register$"; then
    log "OpenCAPIF stack already running — skipping"
else
    if [[ -f "$OPENCAPIF_DIR/run.sh" ]]; then
        (cd "$OPENCAPIF_DIR" && bash run.sh -s false 2>&1 | tail -5) && log "OpenCAPIF stack started" || warn "OpenCAPIF start had issues — check manually"
    else
        warn "OpenCAPIF run.sh not found at $OPENCAPIF_DIR — skipping"
    fi
fi

# 3. NEF stack
info "Starting NEF stack (mongo, nef-monitoring, test_server, core_crowler)..."
if docker ps --format '{{.Names}}' | grep -q "^nef$"; then
    log "NEF stack already running — skipping"
else
    (cd "$NEF_DIR" && docker compose up -d 2>&1 | tail -5) && log "NEF stack started" || warn "NEF stack start had issues"
fi
wait_for_port "NEF monitoring" localhost 9999

# 4. NEF-QoS
info "Starting NEF-QoS (AsSessionWithQoS, port 8585)..."
if docker ps --format '{{.Names}}' | grep -q "^nef-qos$"; then
    log "NEF-QoS already running — skipping"
else
    (cd "$NEF_QOS_DIR" && docker compose up -d --build 2>&1 | tail -5) && log "NEF-QoS started" || warn "NEF-QoS start had issues"
fi
wait_for_port "NEF-QoS" localhost 8585

# 5. camara-QoD
info "Starting camara-QoD provider (port 8002)..."
if docker ps --format '{{.Names}}' | grep -q "^camara-qod$"; then
    log "camara-QoD already running — skipping"
else
    (cd "$CAMARA_QOD_DIR" && docker compose up -d 2>&1 | tail -5) && log "camara-QoD started" || warn "camara-QoD start had issues"
fi
wait_for_port "camara-QoD" localhost 8002

# 6. CamaraLocationRetrieval
info "Starting CamaraLocationRetrieval provider (port 8003)..."
if docker ps --format '{{.Names}}' | grep -q "^camara-location-retrieval$"; then
    log "CamaraLocationRetrieval already running — skipping"
else
    (cd "$CAMARA_LOC_DIR" && docker compose up -d 2>&1 | tail -5) && log "CamaraLocationRetrieval started" || warn "CamaraLocationRetrieval start had issues"
fi
wait_for_port "CamaraLocationRetrieval" localhost 8003

# 7. Our backend
info "Building and starting mini-telco-backend (port 8000)..."
(cd "$BACKEND_DIR" && docker compose -f docker-compose.capif.yml up -d --build 2>&1 | tail -5) && log "mini-telco-backend started" || error "Backend failed to start!"
wait_for_port "mini-telco-backend" localhost 8000

# ─── Step 8: CAPIF automated setup ───────────────────────────────────────────
info "Running CAPIF post-startup setup..."

# 8a. Create camara_user in register (idempotent — "user already exists" is OK)
info "Ensuring camara_user exists in register..."
ADMIN_TOKEN=$(curl -sk -X POST 'https://localhost:8084/login' \
  -u 'admin:password123' 2>/dev/null | grep -o '"access_token":"[^"]*"' | cut -d'"' -f4)

if [[ -n "$ADMIN_TOKEN" ]]; then
    CREATE_USER_RESP=$(curl -sk -X POST 'https://localhost:8084/createUser' \
      -H "Authorization: Bearer $ADMIN_TOKEN" \
      -H 'Content-Type: application/json' \
      -d '{
        "username": "camara_user",
        "password": "camara_user",
        "email": "camara_user@example.com",
        "enterprise": "FRONT-research-group",
        "country": "GR",
        "purpose": "CAMARA Location Retrieval invoker",
        "description": "CamaraLocationRetrieval CAPIF invoker"
      }' 2>/dev/null)
    if echo "$CREATE_USER_RESP" | grep -qi "success\|registered\|already exists"; then
        log "camara_user ready in register"
    else
        warn "camara_user creation response: $CREATE_USER_RESP"
    fi
else
    warn "Could not get register admin token — skipping camara_user creation"
fi

# 8b. Ensure NEF container is connected to capif-network
info "Connecting NEF to capif-network (idempotent)..."
docker network connect capif-network nef 2>/dev/null && log "NEF connected to capif-network" || log "NEF already on capif-network"

# 8c. Ensure all CAMARA services are published to CAPIF
#     Uses NEF's APF credentials (already onboarded). Idempotent — checks before publishing.
info "Ensuring all CAMARA services are published to CAPIF..."
docker exec nef python3 - <<'PYEOF' 2>/dev/null
import sys, json, os
sys.path.insert(0, '/app')

try:
    from opencapif_sdk import capif_provider_connector
    import requests, warnings
    warnings.filterwarnings('ignore')

    conn = capif_provider_connector(config_file='/app/provider_onboarding/provider_config_sample.json')
    ids = conn.provider_capif_ids

    # If not yet onboarded, onboard first
    if not ids.get('APF-1'):
        print("Onboarding NEF provider to CAPIF...", flush=True)
        conn.onboard_provider()
        ids = conn.provider_capif_ids
        # Also publish 3GPP Monitoring Event API
        from opencapif_sdk import api_schema_translator
        openapi_file = '/app/provider_onboarding/openapi.yaml'
        if os.path.exists(openapi_file):
            t = api_schema_translator(openapi_file)
            t.build('http://host.docker.internal:9999/3gpp-monitoring-event/v1', '0', '0')
            conn.api_description_path = '/3gpp-monitoring-event.json'
            conn.publish_req['publisher_apf_id'] = ids['APF-1']
            conn.publish_req['publisher_aefs_ids'] = [ids['AEF-1']]
            conn.publish_services()
        print(f"NEF onboarded: {ids}", flush=True)

    apf_id = ids.get('APF-1')
    aef_id = ids.get('AEF-1')
    if not apf_id or not aef_id:
        print("No APF/AEF IDs found — skipping CAMARA service publish", flush=True)
        sys.exit(0)

    folder = conn.provider_folder.rstrip('/') + '/'
    base_url = f'{conn.capif_https_url}published-apis/v1/{apf_id}/service-apis'
    cert = (folder + 'apf-1.crt', folder + 'APF-1_private_key.key')
    ca = folder + 'ca.crt'

    # Get existing published API names
    r = requests.get(base_url, cert=cert, verify=ca, timeout=10)
    existing = {api.get('apiName') for api in (r.json() if r.status_code == 200 else [])}
    print(f"Already published: {existing}", flush=True)

    # CAMARA services to publish (with securityMethods for proper token flow)
    services = [
        {'apiName': 'quality-on-demand', 'uri': '/quality-on-demand/v1/sessions', 'domain': 'camara-qod', 'ver': 'v1.1.0'},
        {'apiName': 'qos-profiles', 'uri': '/qos-profiles/v1/qos-profiles', 'domain': 'mini-telco', 'ver': 'v1.1.0'},
        {'apiName': 'qos-provisioning', 'uri': '/qos-provisioning/v1/device-qos', 'domain': 'nef-qos', 'ver': 'v1.1.0'},
        {'apiName': 'location-retrieval', 'uri': '/location-retrieval/v0.5/retrieve', 'domain': 'camara-location', 'ver': 'v0.5'},
    ]

    for svc in services:
        if svc['apiName'] in existing:
            print(f"  {svc['apiName']}: already published — skip", flush=True)
            continue
        body = {
            'apiName': svc['apiName'],
            'description': f"CAMARA {svc['apiName']} API",
            'aefProfiles': [{
                'aefId': aef_id,
                'versions': [{'apiVersion': svc['ver'], 'resources': [{'resourceName': 'resource', 'uri': svc['uri'], 'commType': 'REQUEST_RESPONSE', 'operations': ['POST', 'GET']}]}],
                'protocol': 'HTTP_1_1',
                'domainName': svc['domain'],
                'securityMethods': ['PKI']
            }],
            'supportedFeatures': '0'
        }
        r = requests.post(base_url, headers={'Content-Type': 'application/json'},
            data=json.dumps(body), cert=cert, verify=ca, timeout=15)
        print(f"  {svc['apiName']}: HTTP {r.status_code}", flush=True)

    print("CAPIF service publish complete", flush=True)
except Exception as e:
    print(f"CAPIF publish error (non-fatal): {e}", flush=True)
    import traceback; traceback.print_exc()
PYEOF
log "CAPIF service publish step complete"

# 8d. Restart CamaraLocationRetrieval to pick up fresh CAPIF security context
info "Restarting CamaraLocationRetrieval to refresh CAPIF token state..."
docker restart camara-location-retrieval 2>/dev/null && log "CamaraLocationRetrieval restarted" || warn "Could not restart CamaraLocationRetrieval"
sleep 12  # Give it time to onboard and be ready

# 8e. Trigger backend CAPIF invoker onboarding (clear stale cache first)
info "Triggering backend CAPIF invoker onboarding..."
# Clear stale invoker details to force fresh onboarding
docker exec mini-telco-backend-capif sh -c \
    "rm -f /app/backend/capif/invoker_details.json /app/backend/capif/register_auth.json" 2>/dev/null || true

# Wait a moment for the backend to settle, then trigger onboarding
sleep 3
ONBOARD_RESP=$(curl -sk -X POST 'http://localhost:8000/capif/invokers/onboard' \
  -H 'Content-Type: application/json' \
  -d '{
    "api_invoker_information": "Mini-Telco-Platform-Orchestrator",
    "public_key": "",
    "notification_destination": "http://localhost:8000/notifications"
  }' 2>/dev/null)
INVOKER_ID=$(echo "$ONBOARD_RESP" | grep -o '"apiInvokerId":"[^"]*"' | cut -d'"' -f4)
if [[ -n "$INVOKER_ID" ]]; then
    log "Backend CAPIF invoker onboarded: $INVOKER_ID"
else
    warn "Backend onboarding response: ${ONBOARD_RESP:0:200}"
fi

# ─── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "═══════════════════════════════════════════════════════"
echo "  All services started and configured!"
echo "═══════════════════════════════════════════════════════"
echo ""
echo "  Frontend:    http://localhost:8000"
echo "  Swagger UI:  http://localhost:8000/docs"
echo "  Health:      http://localhost:8000/health"
echo "  CAPIF Status:http://localhost:8000/capif/status"
echo ""
echo "  camara-QoD:  http://localhost:8002/docs"
echo "  Location:    http://localhost:8003/docs"
echo "  NEF-QoS:     http://localhost:8585/docs"
echo "  NEF:         http://localhost:9999"
echo ""
echo "  OpenCAPIF:"
echo "    Register:  https://localhost:8084"
echo "    CAPIF:     https://localhost (nginx)"
echo ""
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"
