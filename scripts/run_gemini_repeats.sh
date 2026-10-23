#!/bin/bash
# Gemini 2.5 Flash, runs 2 and 3 on the 300 intents (run 1: datasets/eval_results_gemini25flash_300.json).
# Needs a paid-tier key; on the free tier the daily quota ends the run with 429 errors.
cd "$(dirname "$0")/.."
mkdir -p datasets/repeats
for r in 2 3; do
  LLM_PROVIDER=gemini GEMINI_MIN_INTERVAL_S=1.0 venv/bin/python scripts/run_evaluation.py --mode llm-assisted \
    --no-registry --json --output datasets/repeats/eval_results_gemini25flash_300_run$r.json --delay 0.5 \
    > /tmp/repeat_gemini25flash_run$r.log 2>&1 && echo "[$(date)] gemini run$r done" || echo "[$(date)] gemini run$r FAILED"
done
