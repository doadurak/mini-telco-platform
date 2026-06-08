"""
NoF 2026 — Two-Phase LLM Orchestration Flow Diagram  (nof_fig_flow.png)
========================================================================
Publication-quality flowchart showing the full request lifecycle:
  User Intent → FastAPI → Intent Engine → LLM Planner (Ph1+Ph2)
  → Three-Layer Validator → [Feedback loop OR Execute] → Response

Style: coloured rounded boxes + diamond decisions (like ML paper flowcharts).
Output: docs/nof_fig_flow.png
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Polygon
from matplotlib.lines import Line2D
import numpy as np

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUTPUT   = os.path.join(ROOT_DIR, 'docs', 'nof_fig_flow.png')

plt.rcParams.update({
    'font.family':    'sans-serif',
    'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica'],
    'font.size':      9,
    'figure.dpi':     220,
    'savefig.dpi':    220,
    'savefig.bbox':   'tight',
    'savefig.pad_inches': 0.12,
})

# Canvas
W, H = 5.2, 10.2
fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')
fig.patch.set_facecolor('#FAFAFA')

# ── Colour tokens ────────────────────────────────────────────────────────────
IO_F,   IO_E   = '#C8E6C9', '#2E7D32'   # green  — input / output
GW_F,   GW_E   = '#BBDEFB', '#1565C0'   # blue   — gateway / router
LLM_F,  LLM_E  = '#E1BEE7', '#6A1B9A'   # purple — LLM components
VAL_F,  VAL_E  = '#FFCDD2', '#B71C1C'   # red    — validator
FB_F,   FB_E   = '#FFE0B2', '#E65100'   # orange — feedback
CAP_F,  CAP_E  = '#B2DFDB', '#00695C'   # teal   — CAPIF / execute
DEC_F,  DEC_E  = '#FFF9C4', '#F57F17'   # yellow — decision diamonds
PH_F,   PH_E   = '#D1C4E9', '#4527A0'   # indigo — phase sub-boxes

ARROW = '#37474F'
R = 0.10  # corner radius

# ── Helpers ──────────────────────────────────────────────────────────────────
def rbox(x, y, w, h, fc, ec, lw=1.2, z=3, alpha=1.0, ls='-'):
    ax.add_patch(FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f'round,pad={R}',
        fc=fc, ec=ec, linewidth=lw, linestyle=ls,
        zorder=z, alpha=alpha))

def pill(x, y, w, h, fc, ec, lw=1.4, z=3):
    """Stadium / pill shape — for input/output."""
    rx = h / 2
    ax.add_patch(mpatches.FancyBboxPatch(
        (x, y), w, h,
        boxstyle=f'round,pad={rx}',
        fc=fc, ec=ec, linewidth=lw, zorder=z))

def diamond(cx, cy, hw, hh, fc, ec, lw=1.2, z=3):
    """Decision diamond centred at (cx,cy)."""
    pts = np.array([[cx, cy+hh], [cx+hw, cy],
                    [cx, cy-hh], [cx-hw, cy]])
    ax.add_patch(Polygon(pts, closed=True,
        fc=fc, ec=ec, linewidth=lw, zorder=z))

def txt(x, y, s, fs=8.5, fw='bold', col='#1A1A1A',
        ha='center', va='center', z=5, wrap=False):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, fontweight=fw,
            color=col, zorder=z, multialignment='center',
            wrap=wrap)

def arr(x1, y1, x2, y2, col=ARROW, lw=1.3, ls='-',
        rad=0.0, lbl='', lfs=7.5, lpad=(0.12, 0)):
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle='->', color=col, lw=lw,
                        linestyle=ls,
                        connectionstyle=f'arc3,rad={rad}'))
    if lbl:
        mx, my = (x1+x2)/2 + lpad[0], (y1+y2)/2 + lpad[1]
        ax.text(mx, my, lbl, ha='left', va='center',
                fontsize=lfs, color=col, zorder=6,
                fontstyle='italic')

CX  = W / 2          # centre x
BW  = 3.60           # standard box width
BX  = CX - BW/2      # box left edge

# =============================================================================
# 1 — User Intent  (pill, top)
# =============================================================================
Y1 = 9.50; BH1 = 0.52
pill(BX, Y1, BW, BH1, IO_F, IO_E, lw=1.5)
txt(CX, Y1 + BH1/2 + 0.08, 'User Intent', fs=9.5, fw='bold', col=IO_E)
txt(CX, Y1 + BH1/2 - 0.14, 'Natural language request (EN / TR)',
    fs=7.8, fw='normal', col='#2E7D32')

arr(CX, Y1, CX, Y1 - 0.28, col=ARROW)

# =============================================================================
# 2 — FastAPI Gateway
# =============================================================================
Y2 = 8.34; BH2 = 0.72
rbox(BX, Y2, BW, BH2, GW_F, GW_E)
txt(CX, Y2+BH2*0.66, 'FastAPI Backend  :8000', fs=9.0, fw='bold', col=GW_E)
txt(CX, Y2+BH2*0.28, 'POST /orchestrate  —  route & dispatch',
    fs=7.5, fw='normal', col='#1565C0')

arr(CX, Y2, CX, Y2 - 0.28, col=ARROW)

# =============================================================================
# 3 — Intent Engine
# =============================================================================
Y3 = 7.22; BH3 = 0.72
rbox(BX, Y3, BW, BH3, GW_F, GW_E, lw=1.0, ls='--')
txt(CX, Y3+BH3*0.64, 'Intent Engine', fs=9.0, fw='bold', col=GW_E)
txt(CX, Y3+BH3*0.24, 'Deterministic keyword routing  (baseline)',
    fs=7.5, fw='normal', col='#1565C0')

# bypass dashed arrow (direct route skips LLM)
ax.annotate('', xy=(BX+BW+0.10, 5.32), xytext=(BX+BW+0.10, Y3+BH3/2),
    arrowprops=dict(arrowstyle='->', color='#90A4AE', lw=1.0,
                    linestyle='dashed',
                    connectionstyle='arc3,rad=0.0'))
ax.plot([BX+BW, BX+BW+0.10], [Y3+BH3/2, Y3+BH3/2],
        color='#90A4AE', lw=1.0, ls='--', zorder=4)
txt(BX+BW+0.22, (Y3+BH3/2 + 5.42)/2, 'direct\nroute',
    fs=6.8, fw='normal', col='#78909C', ha='left', va='center')

arr(CX, Y3, CX, Y3 - 0.30, col=ARROW)

# =============================================================================
# 4 — LLM Planner  (outer box + Phase 1/2 inner)
# =============================================================================
Y4 = 5.52; BH4 = 1.42
rbox(BX, Y4, BW, BH4, LLM_F, LLM_E, lw=1.4)
txt(CX, Y4+BH4-0.22, 'LLM Planner', fs=9.2, fw='bold', col=LLM_E)
txt(CX, Y4+BH4-0.42, 'Gemini  |  OpenAI  |  Anthropic',
    fs=7.0, fw='normal', col='#6A1B9A', va='center')

# Phase 1 inner box
PBW = 1.56; PBH = 0.64; GAP = 0.12
P1X = BX + 0.12
rbox(P1X, Y4 + 0.14, PBW, PBH, PH_F, PH_E, lw=0.9)
txt(P1X + PBW/2, Y4 + 0.14 + PBH*0.62, 'Phase 1', fs=8.0, fw='bold', col=PH_E)
txt(P1X + PBW/2, Y4 + 0.14 + PBH*0.22, 'Service\nSelection', fs=7.0, fw='normal', col='#311B92')

# inner arrow Phase1 → Phase2
arr(P1X+PBW, Y4+0.14+PBH/2, P1X+PBW+GAP, Y4+0.14+PBH/2, col=PH_E, lw=1.0)

# Phase 2 inner box
P2X = P1X + PBW + GAP
rbox(P2X, Y4 + 0.14, PBW, PBH, PH_F, PH_E, lw=0.9)
txt(P2X + PBW/2, Y4 + 0.14 + PBH*0.62, 'Phase 2', fs=8.0, fw='bold', col=PH_E)
txt(P2X + PBW/2, Y4 + 0.14 + PBH*0.22, 'Payload\nGeneration', fs=7.0, fw='normal', col='#311B92')

arr(CX, Y4, CX, Y4 - 0.30, col=ARROW)

# =============================================================================
# 5 — Three-Layer Validator
# =============================================================================
Y5 = 3.82; BH5 = 1.00
rbox(BX, Y5, BW, BH5, VAL_F, VAL_E, lw=1.4)
txt(CX, Y5+BH5-0.22, 'Three-Layer Validator', fs=9.0, fw='bold', col=VAL_E)

# L1, L2, L3 sub-boxes
SW = (BW - 0.48) / 3
for i, (lbl, sub) in enumerate([
    ('L1', 'Pydantic\nSchema'),
    ('L2', 'Telecom\nPolicy'),
    ('L3', 'CAPIF\nRegistry'),
]):
    sx = BX + 0.12 + i*(SW+0.06)
    rbox(sx, Y5+0.10, SW, 0.60, '#FFEBEE', VAL_E, lw=0.7)
    txt(sx+SW/2, Y5+0.10+0.60*0.70, lbl, fs=8.0, fw='bold', col=VAL_E)
    txt(sx+SW/2, Y5+0.10+0.60*0.26, sub, fs=6.8, fw='normal', col='#B71C1C')

# arrows L1/L2/L3 separator labels
for i in range(1, 3):
    xv = BX + 0.12 + i*(SW+0.06) - 0.03
    ax.plot([xv, xv], [Y5+0.12, Y5+0.68],
            color=VAL_E, lw=0.5, ls=':', zorder=4)

arr(CX, Y5, CX, Y5 - 0.30, col=ARROW)

# =============================================================================
# 6 — Decision diamond: Valid?
# =============================================================================
DY = 3.16; DHW = 0.78; DHH = 0.30
diamond(CX, DY, DHW, DHH, DEC_F, DEC_E, lw=1.2)
txt(CX, DY, 'Valid?', fs=8.8, fw='bold', col='#E65100')

# "Yes" path (right → down)
ax.annotate('', xy=(CX+DHW+1.02, DY), xytext=(CX+DHW, DY),
    arrowprops=dict(arrowstyle='->', color=CAP_E, lw=1.2))
txt(CX+DHW+0.40, DY+0.18, 'Yes', fs=8.0, fw='bold', col=CAP_E)

# "No" path (left → down)
ax.annotate('', xy=(CX-DHW-0.90, DY), xytext=(CX-DHW, DY),
    arrowprops=dict(arrowstyle='->', color=FB_E, lw=1.2))
txt(CX-DHW-0.45, DY+0.18, 'No', fs=8.0, fw='bold', col=FB_E)

# =============================================================================
# 7a — Feedback Engine (left branch)
# =============================================================================
FBW = 1.50; FBH = 0.90; FBX = BX - 0.10
FBY = 1.80
rbox(FBX, FBY, FBW, FBH, FB_F, FB_E, lw=1.2)
txt(FBX+FBW/2, FBY+FBH*0.65, 'Feedback\nEngine', fs=8.5, fw='bold', col=FB_E)
txt(FBX+FBW/2, FBY+FBH*0.22, 'max 3 iterations', fs=7.0, fw='normal', col='#E65100')

# arrow: diamond No → Feedback (down-left)
ax.annotate('', xy=(FBX+FBW/2, FBY+FBH), xytext=(CX-DHW-0.90, DY),
    arrowprops=dict(arrowstyle='->', color=FB_E, lw=1.2,
                    connectionstyle='arc3,rad=0.0'))

# correction loop: Feedback → LLM Planner (curved left)
ax.annotate('', xy=(BX-0.06, Y4+BH4/2), xytext=(FBX-0.06, FBY+FBH/2),
    arrowprops=dict(arrowstyle='->', color=FB_E, lw=1.2,
                    connectionstyle='arc3,rad=0.4'))
txt(BX-0.34, (Y4+BH4/2 + FBY+FBH/2)/2, 'correction\nprompt',
    fs=6.8, fw='normal', col=FB_E, ha='center', va='center')

# =============================================================================
# 7b — CAPIF Client + CAMARA Execute (right branch)
# =============================================================================
CCX = CX + DHW + 0.12; CCW = 1.50

# CAPIF Client
CCY = 2.38; CCH = 0.78
rbox(CCX, CCY, CCW, CCH, CAP_F, CAP_E, lw=1.2)
txt(CCX+CCW/2, CCY+CCH*0.64, 'CAPIF Client', fs=8.5, fw='bold', col=CAP_E)
txt(CCX+CCW/2, CCY+CCH*0.22, 'mTLS + Discovery', fs=7.0, fw='normal', col=CAP_E)

arr(CCX+CCW/2, CCY, CCX+CCW/2, CCY-0.30, col=CAP_E)

# CAMARA Provider
CQY = 1.62; CQH = 0.68
rbox(CCX, CQY, CCW, CQH, CAP_F, CAP_E, lw=1.2)
txt(CCX+CCW/2, CQY+CQH*0.62, 'CAMARA Provider', fs=8.2, fw='bold', col=CAP_E)
txt(CCX+CCW/2, CQY+CQH*0.24, 'QoD / Location / NEF-QoS', fs=6.8, fw='normal', col=CAP_E)

arr(CCX+CCW/2, CQY, CX, CQY-0.40, col=CAP_E, rad=0.2)

# =============================================================================
# 8 — Response (output pill)
# =============================================================================
Y8 = 0.55; BH8 = 0.52
pill(BX, Y8, BW, BH8, IO_F, IO_E, lw=1.5)
txt(CX, Y8+BH8/2+0.08, 'Orchestration Response', fs=9.0, fw='bold', col=IO_E)
txt(CX, Y8+BH8/2-0.14, 'CAPIF-verified API execution result',
    fs=7.5, fw='normal', col='#2E7D32')

# =============================================================================
# Legend
# =============================================================================
legend_items = [
    mpatches.Patch(fc=IO_F,  ec=IO_E,  label='Input / Output'),
    mpatches.Patch(fc=GW_F,  ec=GW_E,  label='API Gateway'),
    mpatches.Patch(fc=LLM_F, ec=LLM_E, label='LLM Planner'),
    mpatches.Patch(fc=VAL_F, ec=VAL_E, label='Validator (L1–L3)'),
    mpatches.Patch(fc=FB_F,  ec=FB_E,  label='Feedback Loop'),
    mpatches.Patch(fc=CAP_F, ec=CAP_E, label='CAPIF / CAMARA'),
]
ax.legend(handles=legend_items, loc='lower center', fontsize=7.0,
          framealpha=0.9, ncol=3, handlelength=1.0, columnspacing=0.6,
          bbox_to_anchor=(0.5, -0.005))

fig.savefig(OUTPUT, facecolor='#FAFAFA')
plt.close(fig)
print(f"OK: {OUTPUT}")
