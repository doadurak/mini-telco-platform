#!/usr/bin/env python3
"""
Per-layer fault injection: does each validator layer catch its faults, and can the
LLM feedback loop repair them (at what latency cost)?

Correct GPT-4o-mini plans from the 300-entry run are mutated with faults that target
one layer each, validated (L3 against the live CAPIF registry), and passed to the
real feedback loop (correct_payload_with_feedback, at most 3 iterations).

  L1  missing_field   : required applicationServer removed
  L1  wrong_type      : duration "thirty minutes" instead of an integer
  L2  bad_e164        : phone number without the leading "+"
  L2  duration_policy : duration 10800 s (schema allows it, policy max is 7200 s)
  L2  unknown_profile : qosProfile "QOS_ULTRA"
  L2  bad_ipv4        : applicationServer.ipv4Address "300.1.1.1"
  L3  unpublished     : service missing from the CAPIF discovery result (registry
                        response filtered, simulating an unpublished API)

Run inside the backend container (LLM keys, CAPIF credentials):
  python scripts/layer_fault_injection.py --per-fault 10 --output datasets/layer_faults.json
"""
from __future__ import annotations

import argparse
import copy
import json
import random
import statistics
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import backend.capif.client as capif_client  # noqa: E402
from backend.feedback_engine import run_correction_loop  # noqa: E402
from backend.llm_planner import correct_payload_with_feedback, set_llm_provider  # noqa: E402
from backend.models import ExecutionStep  # noqa: E402
from backend.rag_context import get_payload_schema_prompt  # noqa: E402
from backend.service_catalog import CATALOG  # noqa: E402
from backend.validator import validate_step  # noqa: E402

RESULTS = Path("datasets/eval_results_gpt4omini_300.json")


def _qod(fn):
    def apply(p):
        p = copy.deepcopy(p)
        fn(p)
        return p
    return apply


FAULTS = {
    "missing_field": ("L1", _qod(lambda p: p.pop("applicationServer", None))),
    "wrong_type": ("L1", _qod(lambda p: p.__setitem__("duration", "thirty minutes"))),
    "bad_e164": ("L2", _qod(lambda p: p["device"].__setitem__("phoneNumber", p["device"]["phoneNumber"].lstrip("+")))),
    "duration_policy": ("L2", _qod(lambda p: p.__setitem__("duration", 10800))),
    "unknown_profile": ("L2", _qod(lambda p: p.__setitem__("qosProfile", "QOS_ULTRA"))),
    "bad_ipv4": ("L2", _qod(lambda p: p.setdefault("applicationServer", {}).__setitem__("ipv4Address", "300.1.1.1"))),
    "unpublished": ("L3", lambda p: copy.deepcopy(p)),
}

_ALIASES = {"qod": "quality-on-demand"}


def _hide_from_registry(service_id: str):
    """Patch CAPIF discovery so the given service is absent (restored by the caller)."""
    original = capif_client.discover_services
    hidden = {service_id, _ALIASES.get(service_id, service_id)}

    def patched(*a, **kw):
        d = original(*a, **kw)
        apis = (d.get("services") or {}).get("serviceAPIDescriptions", [])
        d = copy.deepcopy(d)
        d["services"]["serviceAPIDescriptions"] = [x for x in apis if x.get("apiName") not in hidden]
        return d

    capif_client.discover_services = patched
    return original


def _step(service_id: str, payload: dict) -> ExecutionStep:
    op = CATALOG[service_id].operations[0]
    return ExecutionStep(service_id=service_id, operation_id=op.operation_id, method=op.method,
                         path=op.path, payload=payload, rationale="fault injection")


def _revalidate(step, skip):
    return validate_step(step.service_id, step.payload, step.operation_id, step.method, skip_registry=skip)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--per-fault", type=int, default=10)
    ap.add_argument("--provider", default="openai")
    ap.add_argument("--seed", type=int, default=7)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    set_llm_provider(args.provider)
    rng = random.Random(args.seed)

    records = json.loads(RESULTS.read_text(encoding="utf-8"))["results"]
    good = [r for r in records if r["iwsr"] and not r.get("error") and r.get("actual_payload")]
    qod = [r for r in good if r["actual_service_id"] == "qod"]

    rows = []
    for fault, (layer, mutate) in FAULTS.items():
        pool = qod if layer in ("L1", "L2") else good
        for rec in rng.sample(pool, args.per_fault):
            svc = rec["actual_service_id"]
            step = _step(svc, mutate(rec["actual_payload"]))
            original = _hide_from_registry(svc) if layer == "L3" else None
            try:
                t0 = time.perf_counter()
                v = _revalidate(step, False)
                t_val = (time.perf_counter() - t0) * 1000
                caught = {"L1": not v.layer1_schema.passed, "L2": not v.layer2_semantic.passed,
                          "L3": not v.layer3_registry.passed}
                t0 = time.perf_counter()
                _, v2, fb = run_correction_loop(
                    intent=rec["intent"], step=step, initial_validation=v,
                    schema_context=get_payload_schema_prompt(svc, step.operation_id),
                    correct_fn=correct_payload_with_feedback, revalidate_fn=_revalidate,
                    skip_registry=False,
                ) if not v.valid else (step, v, None)
                t_fb = (time.perf_counter() - t0) * 1000
            finally:
                if original is not None:
                    capif_client.discover_services = original
            rows.append({
                "id": rec["id"], "fault": fault, "layer": layer, "service": svc,
                "detected": not v.valid, "detected_at_target": caught[layer],
                "registry_checked": v.registry_checked,
                "repaired": bool(fb and fb.recovered), "iterations": fb.iterations if fb else 0,
                "validation_ms": round(t_val, 1), "feedback_ms": round(t_fb, 1),
            })
            print(f"{fault:16s} {rec['id']:12s} detected={rows[-1]['detected_at_target']} "
                  f"repaired={rows[-1]['repaired']} iters={rows[-1]['iterations']} fb_ms={rows[-1]['feedback_ms']:.0f}")

    summary = []
    for fault, (layer, _) in FAULTS.items():
        r = [x for x in rows if x["fault"] == fault]
        summary.append({
            "fault": fault, "layer": layer, "n": len(r),
            "detected_at_target": sum(x["detected_at_target"] for x in r),
            "repaired": sum(x["repaired"] for x in r),
            "median_iterations": statistics.median(x["iterations"] for x in r),
            "median_feedback_ms": round(statistics.median(x["feedback_ms"] for x in r)),
            "median_validation_ms": round(statistics.median(x["validation_ms"] for x in r), 1),
        })
    print()
    for s in summary:
        print(f"{s['layer']} {s['fault']:16s} detected {s['detected_at_target']}/{s['n']}  repaired {s['repaired']}/{s['n']}  "
              f"iters {s['median_iterations']}  feedback {s['median_feedback_ms']} ms  validation {s['median_validation_ms']} ms")
    if args.output:
        args.output.write_text(json.dumps({"summary": summary, "cases": rows}, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
