#!/bin/bash
# GPT-4o-mini on the 300 intents, three independent runs. Replaces the earlier
# eval_results_gpt4omini_300.json, whose 240 non-pilot entries were planned by Gemini
# because the run used LLM_PROVIDER=gpt, which the planner did not recognise.
cd "$(dirname "$0")/.."
mkdir -p datasets/repeats
for r in 1 2 3; do
  LLM_PROVIDER=openai venv/bin/python scripts/run_evaluation.py --mode llm-assisted --no-registry \
    --json --output datasets/repeats/eval_results_gpt4omini_300_run$r.json --delay 1 \
    > /tmp/repeat_gpt4omini_run$r.log 2>&1 && echo "[$(date)] gpt run$r done" || echo "[$(date)] gpt run$r FAILED"
done
# Baseline: native function calling, alone and with the L1-L3 validator feedback loop
LLM_PROVIDER=openai venv/bin/python scripts/run_evaluation.py --mode llm-function-calling --no-registry --no-feedback   --json --output datasets/eval_results_gpt4omini_function_calling_300.json --delay 1   > /tmp/function_calling.log 2>&1 && echo "[$(date)] function calling done" || echo "[$(date)] function calling FAILED"
LLM_PROVIDER=openai venv/bin/python scripts/run_evaluation.py --mode llm-function-calling --no-registry   --json --output datasets/eval_results_gpt4omini_function_calling_feedback_300.json --delay 1   > /tmp/function_calling_fb.log 2>&1 && echo "[$(date)] function calling + feedback done" || echo "[$(date)] function calling + feedback FAILED"
