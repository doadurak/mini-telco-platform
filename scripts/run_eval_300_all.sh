#!/bin/bash
# Run 300-entry evaluation for all 3 LLM providers in parallel
# Uses --resume to skip already-evaluated entries (the original 60)

cd /home/turkad/mini-telco-platform

echo "[$(date)] Starting GPT-4o-mini evaluation (240 new entries)..."
LLM_PROVIDER=gpt venv/bin/python scripts/run_evaluation.py \
  --mode llm-assisted \
  --json \
  --output datasets/eval_results_gpt4omini_300.json \
  --resume datasets/eval_results_gpt4omini.json \
  --delay 3 \
  --progress \
  > /tmp/eval_gpt_300.log 2>&1 &
GPT_PID=$!

echo "[$(date)] Starting Claude Haiku 4.5 evaluation (240 new entries)..."
LLM_PROVIDER=anthropic venv/bin/python scripts/run_evaluation.py \
  --mode llm-assisted \
  --json \
  --output datasets/eval_results_llm_anthropic_haiku45_300.json \
  --resume datasets/eval_results_llm_anthropic_haiku45.json \
  --delay 3 \
  --progress \
  > /tmp/eval_haiku_300.log 2>&1 &
HAIKU_PID=$!

echo "[$(date)] Starting Gemini 2.5 Flash evaluation (240 new entries)..."
LLM_PROVIDER=gemini venv/bin/python scripts/run_evaluation.py \
  --mode llm-assisted \
  --json \
  --output datasets/eval_results_gemini25flash_300.json \
  --resume datasets/eval_results_gemini25flash.json \
  --delay 4 \
  --progress \
  > /tmp/eval_gemini_300.log 2>&1 &
GEMINI_PID=$!

echo "PIDs: GPT=$GPT_PID  Haiku=$HAIKU_PID  Gemini=$GEMINI_PID"
echo "Logs: /tmp/eval_{gpt,haiku,gemini}_300.log"

wait $GPT_PID && echo "[$(date)] GPT DONE" || echo "[$(date)] GPT FAILED"
wait $HAIKU_PID && echo "[$(date)] Haiku DONE" || echo "[$(date)] Haiku FAILED"
wait $GEMINI_PID && echo "[$(date)] Gemini DONE" || echo "[$(date)] Gemini FAILED"

echo "[$(date)] All evaluations complete."
