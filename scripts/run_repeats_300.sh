#!/bin/bash
# Two extra runs per LLM on the 300 intents (runs 2 and 3; run 1 is datasets/eval_results_*_300.json)
# to bound run-to-run variance at temperature 0.1. The providers run in parallel, the runs of one
# provider in sequence. L3 is skipped: every recorded plan already passed the live registry check.
cd /home/turkad/mini-telco-platform
mkdir -p datasets/repeats
run() {  # provider tag delay
  for r in 2 3; do
    LLM_PROVIDER=$1 venv/bin/python scripts/run_evaluation.py --mode llm-assisted --no-registry \
      --json --output datasets/repeats/eval_results_$2_300_run$r.json --delay $3 \
      > /tmp/repeat_$2_run$r.log 2>&1 && echo "[$(date)] $2 run$r done" || echo "[$(date)] $2 run$r FAILED"
  done
}
# GPT runs: see run_gpt_300_x3.sh (LLM_PROVIDER must be openai)
run anthropic haiku45 2 &
run gemini gemini25flash 3 &
wait
echo "[$(date)] all repeats done"
