#!/bin/bash
set -e
cd /home/turkad/mini-telco-platform

echo "=== Loading .env ==="
while IFS='=' read -r key value; do
    [[ "$key" =~ ^#.*$ ]] && continue
    [[ -z "$key" ]] && continue
    export "$key=$value"
done < .env

echo "=== Setting LLM_PROVIDER=gemini ==="
export LLM_PROVIDER=gemini
export GEMINI_MODEL=gemini-2.5-flash

echo "Gemini key prefix: ${GEMINI_API_KEY:0:20}..."
echo "Model: $GEMINI_MODEL"
echo ""
echo "=== Starting evaluation (60 entries, stability k=5) ==="
echo "=== ETA: ~15-25 min (Gemini free tier: 15 req/min) ==="
echo ""

venv/bin/python3 scripts/run_evaluation.py \
    --mode llm-assisted \
    --output datasets/eval_results_gemini25flash.json \
    --progress \
    --delay 5 \
    --max 60

echo ""
echo "=== DONE ==="

venv/bin/python3 - << 'PYEOF'
import json
with open('datasets/eval_results_gemini25flash.json') as f:
    d = json.load(f)

# Try different key formats
s = d.get('summary', d)
m = s.get('metrics', s)

print("=" * 40)
print("GEMINI 2.5 FLASH RESULTS")
print("=" * 40)
for key in ['IWSR','SCR','SVR','HR','SS','RRF']:
    val = m.get(key, m.get(key.lower(), '?'))
    if isinstance(val, float):
        print(f"  {key}: {val:.4f}  ({val*100:.1f}%)")
    else:
        print(f"  {key}: {val}")
PYEOF
