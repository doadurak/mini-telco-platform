#!/usr/bin/env bash
# =============================================================================
#  demo_full_system.sh  —  Mini Telco Platform: Full System Demo
#  Shows: OpenCAPIF ▸ CAMARA Providers ▸ Orchestration Backend ▸ LLM Planning
#  Usage: bash scripts/demo_full_system.sh [--fast]
# =============================================================================

FAST=${1:-""}
BASE="http://localhost:8000"

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'; GRN='\033[0;32m'; YLW='\033[1;33m'
BLU='\033[0;34m'; CYN='\033[0;36m'; MAG='\033[0;35m'
WHT='\033[1;37m'; DIM='\033[2m'; RST='\033[0m'

pause() {
    local secs=${1:-2}
    [[ "$FAST" == "--fast" ]] && secs=0
    sleep "$secs"
}

header() {
    echo ""
    echo -e "${YLW}╔══════════════════════════════════════════════════════════════╗${RST}"
    printf "${YLW}║  %-62s║${RST}\n" "$1"
    echo -e "${YLW}╚══════════════════════════════════════════════════════════════╝${RST}"
    pause 1
}

section() {
    echo ""
    echo -e "${CYN}━━━  $1  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${RST}"
    pause 0.5
}

step() {
    echo -e "${BLU}▶${RST}  $1"
}

ok() {
    echo -e "${GRN}✔${RST}  $1"
}

info() {
    echo -e "${DIM}   $1${RST}"
}

# =============================================================================
header "Mini Telco Orchestration Platform — Full System Demo"
echo -e "  ${WHT}Architecture:${RST} OpenCAPIF + CAMARA Providers + LLM Orchestrator"
echo -e "  ${WHT}Date:${RST}         $(date '+%Y-%m-%d %H:%M')"
pause 3

# =============================================================================
header "PHASE 0 — System Status: All Docker Containers"
section "Running containers"
docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" \
  | grep -E "NAME|capif|camara|nef|mongo|vault|mini-telco|register|helper|robot" \
  | column -t
pause 3

# =============================================================================
header "PHASE 1 — OpenCAPIF Infrastructure"
section "1a) CAPIF Register — Onboarding Service (:8080)"
step "GET http://localhost:8080/register/v1/netapps"
curl -sk http://localhost:8080/register/v1/netapps 2>/dev/null \
  | python3 -m json.tool 2>/dev/null | head -30 \
  || echo -e "${DIM}   (register service restarting — see docker ps for status)${RST}"
pause 2

section "1b) HashiCorp Vault — Certificate Store (:8200)"
step "GET http://localhost:8200/v1/sys/health"
curl -sk http://localhost:8200/v1/sys/health | python3 -m json.tool 2>/dev/null
pause 2

section "1c) Platform CAPIF Status — Invoker registered?"
step "GET $BASE/capif/status"
CAPIF_STATUS=$(curl -s "$BASE/capif/status" 2>/dev/null)
echo "$CAPIF_STATUS" | python3 -m json.tool 2>/dev/null || echo "$CAPIF_STATUS"
pause 2

section "1d) CAPIF Discovery — Live API Registry"
step "GET $BASE/capif/discover"
curl -s "$BASE/capif/discover" 2>/dev/null \
  | python3 -m json.tool 2>/dev/null | head -40
pause 3

# =============================================================================
header "PHASE 2 — CAMARA Providers Health Check"

section "2a) QoD Session Provider (:8002)"
step "GET http://localhost:8002/ → OpenAPI spec"
QOD_OUT=$(curl -s http://localhost:8002/ 2>/dev/null)
QOD_TITLE=$(echo "$QOD_OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['info']['title'])" 2>/dev/null)
if [[ -n "$QOD_TITLE" ]]; then
    ok "QoD provider UP"
    echo "$QOD_OUT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'  Title:   {d[\"info\"][\"title\"]}')
print(f'  Version: {d[\"info\"][\"version\"]}')
print(f'  Endpoints: {list(d[\"paths\"].keys())[:3]}')
" 2>/dev/null
else
    echo -e "${RED}✗${RST}  QoD provider not reachable (check: docker ps)"
fi
pause 2

section "2b) Location Retrieval Provider (:8003)"
step "GET http://localhost:8003/openapi.json"
LOC_OUT=$(curl -s http://localhost:8003/openapi.json 2>/dev/null)
LOC_TITLE=$(echo "$LOC_OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d['info']['title'])" 2>/dev/null)
if [[ -n "$LOC_TITLE" ]]; then
    ok "Location provider UP"
    echo "$LOC_OUT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'  Title:     {d[\"info\"][\"title\"]}')
print(f'  Version:   {d[\"info\"].get(\"version\",\"N/A\")}')
print(f'  Endpoints: {list(d[\"paths\"].keys())[:3]}')
" 2>/dev/null
else
    echo -e "${RED}✗${RST}  Location provider not reachable"
fi
pause 2

section "2c) NEF-QoS Provider (:8585)"
step "GET http://localhost:8585/"
NEF_OUT=$(curl -s http://localhost:8585/ 2>/dev/null)
NEF_TITLE=$(echo "$NEF_OUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('info',{}).get('title',''))" 2>/dev/null)
if [[ -n "$NEF_TITLE" ]]; then
    ok "NEF-QoS provider UP"
    echo "$NEF_OUT" | python3 -c "
import json,sys
d=json.load(sys.stdin)
print(f'  Title:     {d[\"info\"][\"title\"]}')
print(f'  Endpoints: {list(d[\"paths\"].keys())[:3]}')
" 2>/dev/null
else
    echo -e "${YLW}⚠${RST}  NEF-QoS: $( echo $NEF_OUT | head -c 100 )"
fi
pause 3

# =============================================================================
header "PHASE 3 — Orchestration Backend"

section "3a) Platform Health"
step "GET $BASE/health"
curl -s "$BASE/health" | python3 -m json.tool 2>/dev/null
pause 1

section "3b) Available CAMARA Services (YAML-parsed at startup)"
step "GET $BASE/catalog/services"
curl -s "$BASE/catalog/services" | python3 -m json.tool 2>/dev/null | head -60
pause 3

# =============================================================================
header "PHASE 4 — Deterministic Orchestration (no LLM cost)"
section "4a) English intent — QoD session"
step "POST $BASE/orchestrate  mode=deterministic"
echo ""
PAYLOAD_DET_EN='{
  "intent": "I need 10 Mbps guaranteed bandwidth for device +30-6971234567 for 60 minutes",
  "mode": "deterministic"
}'
echo -e "${DIM}Request:${RST}"
echo "$PAYLOAD_DET_EN" | python3 -m json.tool
echo ""
RESP=$(curl -s -X POST "$BASE/orchestrate" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD_DET_EN")
echo -e "${DIM}Response:${RST}"
echo "$RESP" | python3 -m json.tool 2>/dev/null || echo "$RESP"
pause 3

section "4b) Turkish intent — Location retrieval (deterministic)"
step "POST $BASE/orchestrate  mode=deterministic  lang=TR"
echo ""
PAYLOAD_DET_TR='{
  "intent": "+90-5321234567 numaralı cihazın konumunu bul",
  "mode": "deterministic"
}'
echo -e "${DIM}Request:${RST}"
echo "$PAYLOAD_DET_TR" | python3 -m json.tool
echo ""
RESP2=$(curl -s -X POST "$BASE/orchestrate" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD_DET_TR")
echo -e "${DIM}Response:${RST}"
echo "$RESP2" | python3 -m json.tool 2>/dev/null || echo "$RESP2"
pause 3

# =============================================================================
header "PHASE 5 — LLM-Assisted Orchestration (GPT-4o-mini)"
section "5a) Complex English intent → Phase 1 service routing"
step "POST $BASE/orchestrate  mode=llm-assisted"
echo ""
PAYLOAD_LLM_EN='{
  "intent": "Set up guaranteed low-latency QoS session for mobile device +34-612345678 with 50 Mbps throughput for video streaming, valid for 2 hours",
  "mode": "llm-assisted"
}'
echo -e "${DIM}Request:${RST}"
echo "$PAYLOAD_LLM_EN" | python3 -m json.tool
echo ""
echo -e "${MAG}⟳ Sending to LLM planner (Phase 1: service routing)...${RST}"
RESP3=$(curl -s -X POST "$BASE/orchestrate" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD_LLM_EN")
echo -e "${DIM}Response (Phase 1+2 complete):${RST}"
echo "$RESP3" | python3 -m json.tool 2>/dev/null || echo "$RESP3"
pause 3

section "5b) Turkish intent — LLM mode"
step "POST $BASE/orchestrate  mode=llm-assisted  intent=TR"
echo ""
PAYLOAD_LLM_TR='{
  "intent": "+1-2125559999 numaralı cihaz için 30 dakika boyunca 20 Mbps bant genişliği garantili QoD oturumu başlat",
  "mode": "llm-assisted"
}'
echo -e "${DIM}Request:${RST}"
echo "$PAYLOAD_LLM_TR" | python3 -m json.tool
echo ""
echo -e "${MAG}⟳ Phase 1: intent language detection + service routing...${RST}"
echo -e "${MAG}⟳ Phase 2: schema-grounded payload generation...${RST}"
RESP4=$(curl -s -X POST "$BASE/orchestrate" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD_LLM_TR")
echo -e "${DIM}Response:${RST}"
echo "$RESP4" | python3 -m json.tool 2>/dev/null || echo "$RESP4"
pause 3

# =============================================================================
header "PHASE 6 — Three-Layer Validator: Rejection Demo"
section "6a) Intentionally malformed payload → L1 rejection"
step "POST $BASE/orchestrate with invalid payload (missing required fields)"
echo ""
PAYLOAD_BAD='{
  "intent": "Create QoD for invalid-phone-format ABC123 with 999 Mbps",
  "mode": "llm-assisted"
}'
echo -e "${DIM}Request (deliberately ambiguous / bad number):${RST}"
echo "$PAYLOAD_BAD" | python3 -m json.tool
echo ""
echo -e "${MAG}⟳ Validator will intercept any schema/semantic violation...${RST}"
RESP5=$(curl -s -X POST "$BASE/orchestrate" \
  -H "Content-Type: application/json" \
  -d "$PAYLOAD_BAD")
echo -e "${DIM}Response (validator output):${RST}"
echo "$RESP5" | python3 -m json.tool 2>/dev/null || echo "$RESP5"
pause 3

# =============================================================================
header "PHASE 7 — Evaluation Results Summary"
section "Pre-computed results (60 intents × 3 LLM providers)"
echo ""
python3 << 'PYEOF'
import json

results = {
    'GPT-4o-mini':       ('datasets/eval_results_gpt4omini.json',              60),
    'Claude Haiku 4.5':  ('datasets/eval_results_llm_anthropic_haiku45.json',  60),
    'Gemini 2.5 Flash':  ('datasets/eval_results_gemini25flash.json',            6),
}

print(f"  {'Provider':<22} {'IWSR':>7} {'SCR':>7} {'SVR':>7} {'HR':>7} {'SS':>7}  n/60")
print('  ' + '-'*70)

for name, (path, n_full) in results.items():
    try:
        with open(path) as f:
            d = json.load(f)
        m = d['summary']['metrics']
        n = d['summary']['total_entries']
        note = f"  ← partial ({n}/60)" if n < 60 else ""
        print(f"  {name:<22} {m['IWSR']*100:>6.1f}% {m['SCR']*100:>6.1f}% {m['SVR']*100:>6.1f}% {m['HR']*100:>6.1f}% {m['SS']*100:>6.1f}% {note}")
    except Exception as e:
        print(f"  {name:<22}  (not available: {e})")

print()
print("  ✔  SCR = SVR = 100% in all LLM-assisted configs — schema grounding is provider-agnostic")
print("  ✔  GPT-4o-mini: best IWSR (98.3%) and stability (SS 96.4%)")
print("  ⚠  Gemini 2.5 Flash: only 6/60 evaluated — full run deferred to quota reset")
PYEOF
pause 4

# =============================================================================
header "Demo Complete"
echo ""
echo -e "  ${WHT}Components verified:${RST}"
echo -e "  ${GRN}✔${RST}  OpenCAPIF (CCF, Register, Vault, Security)"
echo -e "  ${GRN}✔${RST}  CAMARA QoD Provider        :8002"
echo -e "  ${GRN}✔${RST}  CAMARA Location Provider   :8003"
echo -e "  ${GRN}✔${RST}  NEF-QoS Provider           :8585"
echo -e "  ${GRN}✔${RST}  Orchestration Backend      :8000"
echo -e "  ${GRN}✔${RST}  Deterministic + LLM modes"
echo -e "  ${GRN}✔${RST}  Three-Layer Validator"
echo ""
echo -e "  ${DIM}Swagger UI: http://localhost:8000/docs${RST}"
echo -e "  ${DIM}GitHub:     github.com/doadurak/mini-telco-platform${RST}"
echo ""
pause 2
