#!/bin/bash
cd /home/turkad/mini-telco-platform

# Load .env properly
while IFS='=' read -r key value; do
    [[ "$key" =~ ^#.*$ ]] && continue
    [[ -z "$key" ]] && continue
    export "$key=$value"
done < .env

export LLM_PROVIDER=openai
export OPENAI_MODEL=gpt-4o-mini

echo "OpenAI key prefix: ${OPENAI_API_KEY:0:20}..."
echo "Model: $OPENAI_MODEL"
echo "Starting OpenAI evaluation..."

venv/bin/python3 scripts/run_evaluation.py \
    --mode llm-assisted \
    --output datasets/eval_results_gpt4omini.json \
    --progress \
    --delay 2 \
    --max 60

echo "=== DONE ==="

venv/bin/python3 - << 'PYEOF'
import json
with open('datasets/eval_results_gpt4omini.json') as f:
    d = json.load(f)
s = d.get('summary', d)
m = s.get('metrics', s)
print("=" * 40)
print("GPT-4o-mini RESULTS")
print("=" * 40)
for key in ['IWSR','SCR','SVR','HR','SS','RRF']:
    val = m.get(key, m.get(key.lower(), '?'))
    if isinstance(val, float):
        print(f"  {key}: {val:.4f}  ({val*100:.1f}%)")
    else:
        print(f"  {key}: {val}")
PYEOF
