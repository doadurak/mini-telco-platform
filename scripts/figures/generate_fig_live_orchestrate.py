#!/usr/bin/env python3
"""Render Fig. 2 (live POST /orchestrate, dry_run=false) from a recorded response.

Usage:
  python scripts/figures/generate_fig_live_orchestrate.py \
      docs/live_runs/2026-10-10/S1_openai.json docs/fig2_live_orchestrate.png
"""
import json
import sys
import textwrap

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch

src, out = sys.argv[1], sys.argv[2]
d = json.load(open(src))
step, val, ex = d["steps"][0], d["validation"], d["execution_result"]
prov = ex.get("provider", {})


def ok(b):
    return "PASS" if b else "FAIL"


panels = [
    ("Request  POST /orchestrate", "#1f4e79", [
        *[("\"intent\": \"" if i == 0 else "           ") + ln
          for i, ln in enumerate(textwrap.wrap(d["intent"] + '"', 44))],
        '"dry_run": false, "orchestration_mode": "llm-assisted"',
    ]),
    (f'Plan ({d["planner"]["model"]}) + L1-L3 validation', "#7a4b00", [
        f'service: {step["service_id"]} / {step["operation_id"]}  ({step["method"]})',
        *[("payload: " if i == 0 else "         ") + f'"{k}": {json.dumps(v)}'
          for i, (k, v) in enumerate(step["payload"].items())],
        f'L1 schema: {ok(val["layer1_schema"]["passed"])}   L2 semantic: {ok(val["layer2_semantic"]["passed"])}',
        f'L3 CAPIF registry: {ok(val["layer3_registry"]["passed"])}  (registry_checked={str(val.get("registry_checked")).lower()})',
    ]),
    ("Execution: CAMARA QoD -> NEF -> Open5GS PCF", "#1b5e20", [
        f'device {step["payload"]["device"]["phoneNumber"]} -> UE IP {ex.get("resolvedUeIpv4")} (5GC subscriber DB)',
        f'profile {ex.get("requestedQosProfile")} -> enforced as {ex.get("qosProfile")}',
        f'HTTP {prov.get("http_status")}  {prov.get("url", "").replace("http://host.docker.internal", "")}',
        f'sessionId: {ex.get("sessionId")[:18]}...   duration: {ex.get("duration")} s',
        f'qosStatus: {ex.get("qosStatus")}  (PCF app session bound to PDU session)',
    ]),
    ("Latency breakdown (ms)", "#4a4a4a", [
        "   ".join(f"{k}: {v:.0f}" for k, v in d.get("timings_ms", {}).items() if k != "feedback"),
    ]),
]

fig_w = 4.6
line_h, head_h, gap = 0.20, 0.26, 0.10
heights = [head_h + line_h * len(p[2]) + 0.08 for p in panels]
fig_h = sum(heights) + gap * (len(panels) - 1) + 0.05
fig, ax = plt.subplots(figsize=(fig_w, fig_h), dpi=300)
ax.set_xlim(0, fig_w)
ax.set_ylim(0, fig_h)
ax.axis("off")

y = fig_h
for (title, color, lines), h in zip(panels, heights):
    y -= h
    ax.add_patch(FancyBboxPatch((0.03, y), fig_w - 0.06, h, boxstyle="round,pad=0,rounding_size=0.06",
                                fc="#f7f7f7", ec=color, lw=1.2))
    ax.add_patch(FancyBboxPatch((0.03, y + h - head_h), fig_w - 0.06, head_h,
                                boxstyle="round,pad=0,rounding_size=0.06", fc=color, ec=color, lw=1.2))
    ax.text(0.12, y + h - head_h / 2, title, color="white", fontsize=7.6, weight="bold", va="center",
            family="DejaVu Sans")
    for i, ln in enumerate(lines):
        ax.text(0.12, y + h - head_h - 0.06 - line_h * (i + 0.5), ln, fontsize=6.4, va="center",
                family="DejaVu Sans Mono")
    y -= gap

plt.savefig(out, bbox_inches="tight", pad_inches=0.02)
print("wrote", out)
