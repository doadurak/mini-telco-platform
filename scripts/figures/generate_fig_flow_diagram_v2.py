"""
NoF 2026 — Two-Phase LLM Orchestration Flow Diagram  (nof_fig_flow_v2.png)
Terminology aligned with nof_2026.tex.
All Y coordinates explicit (top-to-bottom, no formula bugs).
No text overflow, clean feedback rail on left margin.
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.lines as mlines
from matplotlib.patches import FancyBboxPatch, Polygon
import numpy as np

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUTPUT   = os.path.join(ROOT_DIR, 'docs', 'nof_fig_flow_v2.png')

plt.rcParams.update({
    'font.family':     'sans-serif',
    'font.sans-serif': ['DejaVu Sans', 'Arial', 'Helvetica'],
    'font.size':        8.5,
    'figure.dpi':       300,
    'savefig.dpi':      300,
    'savefig.bbox':    'tight',
    'savefig.pad_inches': 0.14,
})

# ── Canvas ─────────────────────────────────────────────────────────────────────
# W=7.6, H=12.0  (portrait, enough room for side branches without clipping)
W, H = 7.6, 12.0
fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, W)
ax.set_ylim(0, H)
ax.axis('off')
fig.patch.set_facecolor('#FFFFFF')

# ── Colours ────────────────────────────────────────────────────────────────────
C_BG    = '#F7FAFC'   # standard box fill
C_BD    = '#2D3748'   # standard box border (dark slate)
C_TXT   = '#1A202C'   # main text
C_SUB   = '#4A5568'   # secondary text
C_DIM   = '#718096'   # muted / bypass
C_LF    = '#E6FFFA'   # LLM Planner fill (teal tint)
C_LE    = '#1A4A50'   # LLM Planner border
C_PH    = '#EDF2F7'   # Phase sub-box fill
C_OK    = '#276749'   # "Yes" green
C_ERR   = '#9B2C2C'   # "No" / feedback red
C_ARR   = '#4A5568'   # normal arrows
R       = 0.09        # box corner radius

# ── Layout ─────────────────────────────────────────────────────────────────────
# Main column: centred at CX, width BW
CX  = 3.90
BW  = 3.90
BX  = CX - BW / 2    # = 1.95  left edge of main boxes
XR  = CX + BW / 2    # = 5.85  right edge of main boxes

# Feedback Engine (left side):  right edge must be ≤ BX
FBW  = 1.30
FBH  = 0.92
FBX  = BX - FBW - 0.28   # = 0.37  safe left edge (no clipping)

# CAPIF / CAMARA (right side): left edge ≥ XR
CCW  = 1.28
CCX  = XR + 0.18          # = 6.03  safe right column left edge

# Left feedback rail x
RAIL_X = FBX - 0.12       # = 0.25  far-left rail

# ── Explicit Y positions (BOTTOM of each box, y increases upward) ──────────────
# Drawing order: top → bottom means decreasing Y values.
#
#  Box n: drawn from YB[n] (bottom) to YB[n]+BH[n] (top)
#  Arrow between boxes: tail at YB[n], head at YB[n+1]+BH[n+1]
#  Ensure YB[n] > YB[n+1]+BH[n+1]  (lower box has smaller y)

# Hardcoded from top (leaves room for legend at bottom):
YB1, BH1 = 11.15, 0.60   # User Intent
YB2, BH2 = 10.00, 0.75   # FastAPI Gateway
YB3, BH3 =  8.65, 0.75   # Intent Engine  (dashed)
YB4, BH4 =  6.65, 1.45   # LLM Planner
YB5, BH5 =  4.85, 1.10   # Three-Layer Validator

# Gap from Validator bottom (YB5=4.85) to diamond top: 0.50
DY       =  4.00          # diamond CENTRE  (top = 4.30, bot = 3.70)
DHW, DHH = 0.78, 0.30

# Right branch: CAPIF Client centre aligned with diamond centre
CCH  = 0.82
CC_BOT = DY - CCH/2      # = 3.59  CAPIF Client bottom
CC_TOP = DY + CCH/2      # = 4.41  CAPIF Client top

# CAMARA Provider: below CAPIF Client
CQH  = 0.72
CQ_TOP = CC_BOT - 0.32   # = 3.27  CAMARA Provider top
CQ_BOT = CQ_TOP - CQH    # = 2.55  CAMARA Provider bottom

# Feedback Engine: centred on diamond
FBY  = DY - FBH / 2      # = 3.54  bottom of Feedback Engine
                           # top = FBY + FBH = 4.46

# Orchestration Response (below both branches)
YB8, BH8 = 1.55, 0.62    # Response

# ── Helpers ────────────────────────────────────────────────────────────────────
def rbox(x, yb, w, h, fc=C_BG, ec=C_BD, lw=1.2, z=3, ls='-'):
    """Draw rounded box. yb = bottom-left y (matplotlib coords)."""
    ax.add_patch(FancyBboxPatch((x, yb), w, h,
        boxstyle=f'round,pad={R}',
        fc=fc, ec=ec, linewidth=lw, linestyle=ls, zorder=z))

def diamond(cx, cy, hw, hh, fc=C_BG, ec=C_BD, lw=1.2, z=3):
    pts = np.array([[cx, cy+hh],[cx+hw, cy],[cx, cy-hh],[cx-hw, cy]])
    ax.add_patch(Polygon(pts, closed=True, fc=fc, ec=ec, lw=lw, zorder=z))

def label(x, y, s, fs=8.5, fw='bold', col=C_TXT, ha='center', va='center', z=5):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, fontweight=fw,
            color=col, zorder=z, multialignment='center')

def darr(x1, y1, x2, y2, col=C_ARR, lw=1.2, ls='-', rad=0.0):
    """Arrow from (x1,y1) to (x2,y2). y1>y2 ⟹ downward."""
    ax.annotate('', xy=(x2, y2), xytext=(x1, y1),
        arrowprops=dict(arrowstyle='->', color=col, lw=lw,
                        linestyle=ls,
                        connectionstyle=f'arc3,rad={rad}',
                        shrinkA=2, shrinkB=2))

# Shorthand: centred down-arrow between two boxes
def box_arr(yb_upper, yb_lower, bh_lower, col=C_ARR):
    darr(CX, yb_upper, CX, yb_lower + bh_lower, col=col)

# ── 1 · User Intent ────────────────────────────────────────────────────────────
rbox(BX, YB1, BW, BH1, lw=1.4)
label(CX, YB1+BH1*0.66, 'User Intent', fs=10.0)
label(CX, YB1+BH1*0.28, 'Natural language request (EN / TR)',
      fs=8.0, fw='normal', col=C_SUB)

box_arr(YB1, YB2, BH2)

# ── 2 · FastAPI Gateway ────────────────────────────────────────────────────────
rbox(BX, YB2, BW, BH2)
label(CX, YB2+BH2*0.66, 'FastAPI Gateway  (:8000)', fs=9.5)
label(CX, YB2+BH2*0.30, 'POST /orchestrate  —  request routing & dispatch',
      fs=8.0, fw='normal', col=C_SUB)

box_arr(YB2, YB3, BH3)

# ── 3 · Intent Engine (dashed = deterministic baseline) ───────────────────────
rbox(BX, YB3, BW, BH3, ls='--', lw=1.0)
label(CX, YB3+BH3*0.66, 'Intent Engine', fs=9.5, col=C_SUB)
label(CX, YB3+BH3*0.30, 'Deterministic keyword routing  (bypass baseline)',
      fs=8.0, fw='normal', col=C_DIM)

# Bypass rail: right side, thin dashed grey
BPX = XR + 0.22          # bypass rail x
v_mid3 = YB3 + BH3/2     # mid of Intent Engine
v_mid5 = YB5 + BH5/2     # mid of Validator
ax.plot([XR, BPX], [v_mid3, v_mid3], color=C_DIM, lw=0.85, ls='--', zorder=3)
ax.plot([BPX, BPX], [v_mid3, v_mid5], color=C_DIM, lw=0.85, ls='--', zorder=3)
darr(BPX, v_mid5, XR, v_mid5, col=C_DIM, lw=0.85, ls='--')
label(BPX+0.13, (v_mid3+v_mid5)/2,
      'Deterministic\nBypass', fs=7.0, fw='normal', col=C_DIM, ha='left')

box_arr(YB3, YB4, BH4)

# ── 4 · LLM Planner (highlighted teal) ────────────────────────────────────────
rbox(BX, YB4, BW, BH4, fc=C_LF, ec=C_LE, lw=1.5)
label(CX, YB4+BH4-0.25, 'LLM Planner', fs=10.0, col=C_LE)
label(CX, YB4+BH4-0.48, 'Gemini 2.5 Flash  |  GPT-4o-mini  |  Claude Haiku',
      fs=7.8, fw='normal', col=C_LE)

# Phase sub-boxes
PBW = 1.72; PBH = 0.65; PGAP = 0.18
P1X = BX + 0.18
rbox(P1X, YB4+0.18, PBW, PBH, fc=C_PH, ec=C_BD, lw=0.9)
label(P1X+PBW/2, YB4+0.18+PBH*0.63, 'Phase 1', fs=8.8)
label(P1X+PBW/2, YB4+0.18+PBH*0.27, 'Service Selection',
      fs=7.8, fw='normal', col=C_SUB)
# Ph1→Ph2 arrow
darr(P1X+PBW, YB4+0.18+PBH/2, P1X+PBW+PGAP, YB4+0.18+PBH/2, col=C_BD)

P2X = P1X + PBW + PGAP
rbox(P2X, YB4+0.18, PBW, PBH, fc=C_PH, ec=C_BD, lw=0.9)
label(P2X+PBW/2, YB4+0.18+PBH*0.63, 'Phase 2', fs=8.8)
label(P2X+PBW/2, YB4+0.18+PBH*0.27, 'Payload Generation',
      fs=7.8, fw='normal', col=C_SUB)

box_arr(YB4, YB5, BH5)

# ── 5 · Three-Layer Validator ──────────────────────────────────────────────────
rbox(BX, YB5, BW, BH5, lw=1.3)
label(CX, YB5+BH5-0.25, 'Three-Layer Validator', fs=9.5)

SW = (BW - 0.50) / 3
for i, (lbl, sub) in enumerate([
    ('L1', 'Pydantic\nSchema'),
    ('L2', 'Telecom\nPolicy'),
    ('L3', 'CAPIF\nRegistry'),
]):
    sx = BX + 0.14 + i*(SW + 0.08)
    rbox(sx, YB5+0.15, SW, 0.62, fc='#FFFFFF', ec=C_BD, lw=0.75)
    label(sx+SW/2, YB5+0.15+0.62*0.65, lbl, fs=8.5)
    label(sx+SW/2, YB5+0.15+0.62*0.27, sub, fs=7.2, fw='normal', col=C_SUB)

# Validator → diamond
darr(CX, YB5, CX, DY+DHH)

# ── 6 · Decision diamond: Valid? ──────────────────────────────────────────────
diamond(CX, DY, DHW, DHH)
label(CX, DY, 'Valid?', fs=9.0)

# "Yes" → right (to CAPIF Client mid-left)
darr(CX+DHW, DY, CCX, DY, col=C_OK, lw=1.3)
label((CX+DHW + CCX)/2, DY+0.20, 'Yes', fs=8.5, fw='bold', col=C_OK)

# "No" → left (to Feedback Engine mid-right)
darr(CX-DHW, DY, FBX+FBW, DY, col=C_ERR, lw=1.3)
label((CX-DHW + FBX+FBW)/2, DY+0.20, 'No', fs=8.5, fw='bold', col=C_ERR)

# ── 7a · Feedback Engine ──────────────────────────────────────────────────────
rbox(FBX, FBY, FBW, FBH, lw=1.2)
label(FBX+FBW/2, FBY+FBH*0.64, 'Feedback Engine', fs=8.8)
label(FBX+FBW/2, FBY+FBH*0.38, 'Re-prompt with\nerror context',
      fs=7.5, fw='normal', col=C_SUB)
label(FBX+FBW/2, FBY+FBH*0.14, 'max 3 iterations',
      fs=7.5, fw='normal', col=C_DIM)

# Feedback correction loop — L-shaped rail on far left
# From Feedback left-mid → RAIL_X → up to LLM mid → right to LLM Planner
loop_y_src = FBY + FBH/2          # y at Feedback Engine left side
loop_y_dst = YB4 + BH4 * 0.55    # y entering LLM Planner left side
ax.plot([FBX, RAIL_X], [loop_y_src, loop_y_src],
        color=C_ERR, lw=1.1, ls='--', zorder=4, solid_capstyle='round')
ax.plot([RAIL_X, RAIL_X], [loop_y_src, loop_y_dst],
        color=C_ERR, lw=1.1, ls='--', zorder=4, solid_capstyle='round')
darr(RAIL_X, loop_y_dst, BX, loop_y_dst, col=C_ERR, lw=1.1, ls='--')
label((RAIL_X + FBX)/2, (loop_y_src+loop_y_dst)/2,
      'correction\nprompt', fs=7.0, fw='normal', col=C_ERR,
      ha='center', va='center')

# ── 7b · CAPIF Client (centred on diamond y) ──────────────────────────────────
rbox(CCX, CC_BOT, CCW, CCH, lw=1.2)
label(CCX+CCW/2, CC_BOT+CCH*0.64, 'CAPIF Client', fs=8.8)
label(CCX+CCW/2, CC_BOT+CCH*0.30,
      'mTLS auth\n3GPP TS 23.222', fs=7.5, fw='normal', col=C_SUB)

# CAPIF → CAMARA (downward)
darr(CCX+CCW/2, CC_BOT, CCX+CCW/2, CQ_TOP, col=C_OK)

# ── 7c · CAMARA Provider ──────────────────────────────────────────────────────
rbox(CCX, CQ_BOT, CCW, CQH, lw=1.2)
label(CCX+CCW/2, CQ_BOT+CQH*0.64, 'CAMARA Provider', fs=8.8)
label(CCX+CCW/2, CQ_BOT+CQH*0.30,
      'QoD  |  Location\nNEF-QoS', fs=7.5, fw='normal', col=C_SUB)

# CAMARA → Response: L-shaped (down then left)
resp_top = YB8 + BH8
conn_y = (CQ_BOT + resp_top) / 2    # mid-height for the horizontal leg
ax.plot([CCX+CCW/2, CCX+CCW/2], [CQ_BOT, conn_y],
        color=C_OK, lw=1.2, zorder=4)
ax.plot([CCX+CCW/2, CX], [conn_y, conn_y],
        color=C_OK, lw=1.2, zorder=4)
darr(CX, conn_y, CX, resp_top, col=C_OK, lw=1.2)

# ── 8 · Orchestration Response ────────────────────────────────────────────────
rbox(BX, YB8, BW, BH8, lw=1.4)
label(CX, YB8+BH8*0.66, 'Orchestration Response', fs=10.0, col=C_LE)
label(CX, YB8+BH8*0.28, 'CAPIF-verified API execution result',
      fs=8.0, fw='normal', col=C_SUB)

# ── Legend ─────────────────────────────────────────────────────────────────────
leg_handles = [
    mpatches.Patch(fc=C_BG,  ec=C_BD,  label='System Component'),
    mpatches.Patch(fc=C_LF,  ec=C_LE,  label='LLM Orchestration Core'),
    mpatches.Patch(fc=C_PH,  ec=C_BD,  label='LLM Pipeline Phase'),
    mlines.Line2D([], [], color=C_DIM, lw=1.0, ls='--',
                  label='Deterministic bypass'),
    mlines.Line2D([], [], color=C_ERR, lw=1.1, ls='--',
                  label='Correction prompt loop'),
]
ax.legend(handles=leg_handles, loc='lower center', fontsize=7.8,
          framealpha=1.0, facecolor='#FFFFFF', edgecolor='#CBD5E0',
          ncol=2, handlelength=1.5, columnspacing=0.9, borderpad=0.6,
          bbox_to_anchor=(0.5, 0.0))

fig.savefig(OUTPUT, facecolor='#FFFFFF', edgecolor='none')
plt.close(fig)
print(f"OK: {OUTPUT}")
