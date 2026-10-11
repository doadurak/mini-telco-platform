#!/usr/bin/env bash
# Run the demo scenarios live (dry_run=false) on every LLM backend and record the responses.
#
#   bash scripts/run_live_scenarios.sh [output_dir]
#
# Before each QoD request the device's open sessions are deleted, since CAMARA QoD
# allows one active session per device (a second request returns 409 CONFLICT).
set -euo pipefail

OUT="${1:-docs/live_runs/$(date +%F)}"
API="${API:-http://localhost:8000}"
QOD="${QOD:-http://localhost:8002/quality-on-demand/v1}"
mkdir -p "$OUT"

declare -A INTENT=(
  [S1]="Activate video-streaming quality for +905321234567 for the next 30 minutes."
  [S2]="Retrieve the current location of device +905551112233."
  # S3 = dataset entry edge_003 (ground truth: qod); the LLM backends disagree on it
  [S3]="Provide network quality improvement for device +905551112233 for a long time"
)
declare -A PHONE=([S1]="+905321234567" [S2]="" [S3]="+905551112233")

close_qod_sessions() {  # phone ue_ipv4
  local body ids
  body=$(printf '{"device": {"phoneNumber": "%s", "ipv4Address": {"publicAddress": "%s", "privateAddress": "%s"}}}' "$1" "$2" "$2")
  ids=$(curl -s -X POST "$QOD/retrieve_sessions" -H 'Content-Type: application/json' -d "$body" \
        | python3 -c "import json,sys
try: d=json.load(sys.stdin)
except Exception: d=[]
items=d if isinstance(d,list) else d.get('sessions', d.get('items', []))
print(' '.join(str(s.get('sessionId')) for s in items if isinstance(s,dict) and s.get('sessionId')))")
  for id in $ids; do curl -s -o /dev/null -X DELETE "$QOD/sessions/$id"; done
}

for provider in openai anthropic gemini; do
  curl -s -o /dev/null -X POST "$API/config/provider" -H 'Content-Type: application/json' -d "{\"provider\":\"$provider\"}"
  for s in S1 S2 S3; do
    case "${PHONE[$s]}" in
      +905321234567) close_qod_sessions "${PHONE[$s]}" 10.45.0.10 ;;
      +905551112233) close_qod_sessions "${PHONE[$s]}" 10.45.0.12 ;;
    esac
    curl -s -X POST "$API/orchestrate" -H 'Content-Type: application/json' \
      -d "{\"intent\": \"${INTENT[$s]}\", \"dry_run\": false, \"orchestration_mode\": \"llm-assisted\"}" \
      -o "$OUT/${s}_${provider}.json"
    python3 - "$OUT/${s}_${provider}.json" <<'PY'
import json, sys
f = sys.argv[1]; d = json.load(open(f))
if "validation" not in d:
    print(f, "ERROR", json.dumps(d)[:300]); sys.exit()
v, s, e = d["validation"], d["steps"][0], d["execution_result"]
status = e.get("qosStatus") or e.get("assignmentStatus") or e.get("status")
print(f"{f.split('/')[-1]:22s} {d['planner'].get('model'):26s} {s['service_id']:19s} "
      f"L1/L2/L3={int(v['layer1_schema']['passed'])}{int(v['layer2_semantic']['passed'])}{int(v['layer3_registry']['passed'])} "
      f"registry_checked={int(v['registry_checked'])} http={e.get('provider', {}).get('http_status')} status={status} "
      f"profile={e.get('requestedQosProfile')}->{e.get('qosProfile')} ue={e.get('resolvedUeIpv4')} "
      f"feedback={int(d['feedback']['attempted'])} total_ms={d['timings_ms'].get('total')}")
PY
    sleep 2
  done
done
curl -s -o /dev/null -X POST "$API/config/provider" -H 'Content-Type: application/json' -d '{"provider":"openai"}'
