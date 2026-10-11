#!/usr/bin/env python3
"""
Re-validate recorded evaluation plans with Layer 3 against the live CAPIF registry.

The 300-entry results were produced with the registry check disabled (L1+L2 only).
This script re-runs the full validator (L1-L3, live CAPIF discovery) on every recorded
plan without new LLM calls and reports whether any IWSR verdict changes.

Usage (inside the backend container, where CAPIF credentials live):
  python scripts/rescore_l3.py datasets/eval_results_*_300.json \
      --output datasets/l3_rescore_300.json
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from backend.service_catalog import CATALOG  # noqa: E402
from backend.validator import validate_step  # noqa: E402


# L3 depends only on the selected service id, so query the live registry once per id
_L3_CACHE: dict[str, tuple[bool, bool]] = {}


def live_l3(svc: str, payload: dict) -> tuple[bool, bool]:
    """Return (l3_passed, registry_checked) for a service id against the live CAPIF registry."""
    if svc not in _L3_CACHE:
        op_id, method = "", "POST"
        if svc in CATALOG and CATALOG[svc].operations:
            op = CATALOG[svc].operations[0]
            op_id, method = op.operation_id, op.method
        v = validate_step(svc, payload, op_id, method, skip_registry=False)
        _L3_CACHE[svc] = (v.layer3_registry.passed, v.registry_checked)
    return _L3_CACHE[svc]


def rescore(path: Path) -> dict:
    data = json.loads(path.read_text(encoding="utf-8"))
    results = data["results"]
    changed, registry_checked, l3_fail = [], 0, 0
    for r in results:
        svc = r.get("actual_service_id")
        if not svc or r.get("actual_payload") is None:
            continue
        l3_passed, checked = live_l3(svc, r["actual_payload"])
        registry_checked += int(checked)
        l3_fail += int(not l3_passed)
        new_iwsr = bool(r["l1_passed"] and r["l2_passed"] and l3_passed and r["service_correct"])
        if new_iwsr != bool(r["iwsr"]):
            changed.append(r["id"])
    n = len(results)
    old = sum(1 for r in results if r["iwsr"])
    return {
        "file": path.name,
        "mode": data["summary"]["mode"],
        "entries": n,
        "registry_checked": registry_checked,
        "l3_rejections": l3_fail,
        "iwsr_recorded": round(old / n, 4),
        "iwsr_with_live_l3": round((old - len(changed)) / n, 4) if changed else round(old / n, 4),
        "changed_entries": changed,
    }


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+", type=Path)
    ap.add_argument("--output", type=Path)
    args = ap.parse_args()
    report = [rescore(f) for f in args.files]
    for r in report:
        print(f"{r['file']:48s} checked={r['registry_checked']}/{r['entries']} "
              f"L3_rejections={r['l3_rejections']} IWSR {r['iwsr_recorded']} -> {r['iwsr_with_live_l3']}")
    if args.output:
        args.output.write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
