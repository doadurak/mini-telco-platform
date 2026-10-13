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


def mask(msisdn: str) -> str:
    """Show only the country/operator prefix and the last two digits of an MSISDN."""
    return msisdn[:6] + "•" * (len(msisdn) - 8) + msisdn[-2:]


phone = step["payload"]["device"]["phoneNumber"]
intent = d["intent"].replace(phone, mask(phone))
t = d.get("timings_ms", {})

panels = [
    ('POST /orchestrate  (dry_run: false, llm-assisted)', "#1f4e79", [
        *[("intent: \"" if i == 0 else "         ") + ln
          for i, ln in enumerate(textwrap.wrap(intent + '"', 50))],
    ]),
    (f'Plan ({d["planner"]["model"]}) + L1-L3 validation', "#7a4b00", [
        f'{step["service_id"]}/{step["operation_id"]}: qosProfile {step["payload"].get("qosProfile")}, '
        f'duration {step["payload"].get("duration")} s',
        f'L1 {ok(val["layer1_schema"]["passed"])}  L2 {ok(val["layer2_semantic"]["passed"])}  '
        f'L3 {ok(val["layer3_registry"]["passed"])} (live CAPIF, registry_checked='
        f'{str(val.get("registry_checked")).lower()})',
    ]),
    ("Execution: CAMARA QoD -> NEF -> Open5GS PCF", "#1b5e20", [
        f'UE IP {ex.get("resolvedUeIpv4")} (subscriber DB); '
        f'{ex.get("requestedQosProfile")} -> {ex.get("qosProfile")}',
        f'HTTP {prov.get("http_status")}, qosStatus {ex.get("qosStatus")} (PCF app session)',
        f'ms: plan {t.get("planning", 0):.0f} | valid. {t.get("validation", 0):.0f} | '
        f'exec {t.get("execution", 0):.0f} | total {t.get("total", 0):.0f}',
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
