"""
NoF 2026 — System Architecture Figure v6  (nof_fig1_arch.png)
==============================================================
IEEE-style clean block diagram.
All coordinates are absolute (no LM-offset arithmetic).
Canvas W=7.4, H=5.6  — content: x in [0.62, 7.32], y in [0, 5.6]
"""
import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch
from matplotlib.lines import Line2D
import numpy as np

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
OUTPUT   = os.path.join(ROOT_DIR, 'docs', 'nof_fig1_arch.png')

plt.rcParams.update({
    'font.family':    'serif',
    'font.serif':     ['Times New Roman', 'Times', 'DejaVu Serif'],
    'font.size':      8,
    'figure.dpi':     220,
    'savefig.dpi':    220,
    'savefig.bbox':   'tight',
    'savefig.pad_inches': 0.05,
})

W, H = 7.4, 5.6
fig, ax = plt.subplots(figsize=(W, H))
ax.set_xlim(0, W); ax.set_ylim(0, H); ax.axis('off')

LM = 0.60    # left margin width for tier labels
XL = LM      # content left edge
XR = 7.32    # content right edge

# ── Colour palette ──────────────────────────────────────────────────────────
U_BG, U_BD   = '#DBEAFE', '#1E40AF'
C_BG, C_BD   = '#F0FDF4', '#14532D'
P_BG, P_BD   = '#FFFBEB', '#92400E'
Q_BG, Q_BD   = '#F0FDFA', '#134E4A'
D_BG, D_BD   = '#F5F3FF', '#3B0764'

LLM_F = '#EDE9FE'; LLM_E = '#5B21B6'
VAL_F = '#FFF1F2'; VAL_E = '#9F1239'
FB_F  = '#FFFBEB'; FB_E  = '#78350F'
DET_F = '#EFF6FF'; DET_E = '#1E40AF'
CAP_F = '#ECFDF5'; CAP_E = '#065F46'

AR  = '#1E293B'
AR2 = '#DC2626'
AR3 = '#065F46'
R   = 0.05

# ── Helpers ─────────────────────────────────────────────────────────────────
def rbox(x, y, w, h, fc, ec, lw=0.9, ls='-', z=3, al=1.0):
    ax.add_patch(FancyBboxPatch((x, y), w, h,
        boxstyle=f'round,pad={R}', fc=fc, ec=ec,
        linewidth=lw, linestyle=ls, zorder=z, alpha=al))

def txt(x, y, s, fs=7.5, fw='bold', col='#1E293B',
        ha='center', va='center', sty='normal', z=5, rot=0):
    ax.text(x, y, s, ha=ha, va=va, fontsize=fs, fontweight=fw,
            color=col, fontfamily='serif', style=sty,
            zorder=z, rotation=rot, multialignment='center')

def tier_strip(y0, y1, fc, ec, label, lfs=6.6):
    """Dashed background + coloured left strip with rotated label."""
    rbox(XL, y0, XR-XL, y1-y0, fc, ec, lw=1.0, ls='--', z=1, al=0.35)
    ax.add_patch(plt.Rectangle((0.02, y0), LM-0.08, y1-y0,
        fc=ec, ec='none', alpha=0.18, zorder=1))
    txt(0.28, (y0+y1)/2, label, fs=lfs, fw='bold', col=ec,
        rot=90, ha='center', va='center', z=2)

def comp(x, y, w, h, fc, ec, top, sub=None,
         tfs=7.4, sfs=6.2, lw=1.0):
    rbox(x, y, w, h, fc, ec, lw=lw, z=3)
    cy = y + h/2 + (0.10 if sub else 0)
    txt(x+w/2, cy, top, fs=tfs, fw='bold', col=ec)
    if sub:
        txt(x+w/2, y+h/2-0.13, sub, fs=sfs, fw='normal',
            col='#374151', sty='italic')

def arr(x1,y1,x2,y2, col=AR, lw=1.1, ls='-', rad=0.0,
        lbl='', lx=None, ly=None):
    ax.annotate('', xy=(x2,y2), xytext=(x1,y1),
        arrowprops=dict(arrowstyle='->', color=col, lw=lw,
                        linestyle=ls,
                        connectionstyle=f'arc3,rad={rad}'))
    if lbl:
        mx = lx or (x1+x2)/2
        my = ly or (y1+y2)/2
        txt(mx, my, lbl, fs=5.6, fw='normal', col=col, sty='italic')

def cyl(x, y, w, h, fc, ec, label, lfs=7.0):
    ey = h * 0.22; bh = h - ey
    ax.add_patch(plt.Rectangle((x, y), w, bh,
        fc=fc, ec='none', zorder=3))
    ax.plot([x, x], [y, y+bh], color=ec, lw=0.9, zorder=4)
    ax.plot([x+w, x+w], [y, y+bh], color=ec, lw=0.9, zorder=4)
    ax.add_patch(mpatches.Ellipse((x+w/2, y+bh),
        w, 2*ey, fc=fc, ec=ec, lw=0.9, zorder=5))
    th = np.linspace(0, np.pi, 60)
    ax.plot(x+w/2+(w/2)*np.cos(th), y+ey*np.sin(th),
            color=ec, lw=0.9, zorder=4)
    ax.plot([x, x+w], [y, y], color=ec, lw=0.9, zorder=4)
    txt(x+w/2, y+bh/2, label, fs=lfs, fw='bold', col=ec)

# =============================================================================
#  TIER 1 — User Interface    y: 4.88 – 5.50
# =============================================================================
tier_strip(4.86, 5.50, U_BG, U_BD, 'Tier 1\nUser\nInterface')

comp(0.66, 4.92, 1.44, 0.48, U_BG, U_BD,
     'Operator Dashboard', 'Browser / OpenAPI UI', tfs=7.1, sfs=5.9)

arr(2.10, 5.16, 2.40, 5.16, col=U_BD)

comp(2.40, 4.92, 2.04, 0.48, '#F8FAFC', '#64748B',
     'POST /orchestrate', 'intent request (JSON)', tfs=7.1, sfs=5.9)

arr(4.44, 5.16, 4.72, 5.16, col=U_BD)

comp(4.72, 4.92, 2.60, 0.48, C_BG, C_BD,
     'FastAPI Backend  :8000', '/orchestrate  /catalog  /capif',
     tfs=7.2, sfs=5.9, lw=1.4)

# =============================================================================
#  TIER 2 — Control Plane    y: 1.62 – 4.78
# =============================================================================
tier_strip(1.60, 4.78, C_BG, C_BD, 'Tier 2\nControl\nPlane')

# ── Intent Engine (x: 0.66–2.24) ────────────────────────────────────────────
comp(0.66, 3.68, 1.58, 0.92, DET_F, DET_E,
     'Intent Engine', 'Deterministic\nkeyword routing',
     tfs=7.3, sfs=6.2, lw=1.0)

# FastAPI → Intent Engine
ax.annotate('', xy=(1.10, 4.60), xytext=(5.20, 4.92),
    arrowprops=dict(arrowstyle='->', color=C_BD, lw=1.0,
                    connectionstyle='arc3,rad=0.15'))

# ── LLM Planner outer (x: 2.36–5.68) ───────────────────────────────────────
comp(2.36, 3.28, 3.32, 1.32, LLM_F, LLM_E, '', lw=1.4)
txt(4.02, 4.44, 'LLM Planner', fs=7.5, fw='bold', col=LLM_E)
txt(4.02, 4.30, 'Gemini  |  OpenAI  |  Anthropic',
    fs=6.0, fw='normal', col=LLM_E, sty='italic')

comp(2.46, 3.36, 1.38, 1.02, '#FAF5FF', LLM_E,
     'Phase 1', 'Service\nSelection', tfs=7.0, sfs=6.3, lw=0.8)

arr(3.84, 3.87, 4.06, 3.87, col=LLM_E)

comp(4.06, 3.36, 1.50, 1.02, '#FAF5FF', LLM_E,
     'Phase 2', 'Payload\nGeneration', tfs=7.0, sfs=6.3, lw=0.8)

# FastAPI → LLM Planner
ax.annotate('', xy=(4.02, 4.60), xytext=(5.70, 4.92),
    arrowprops=dict(arrowstyle='->', color=C_BD, lw=1.0,
                    connectionstyle='arc3,rad=-0.04'))

# ── CAPIF Client (x: 5.82–7.32) ─────────────────────────────────────────────
comp(5.82, 3.68, 1.50, 0.92, CAP_F, CAP_E,
     'CAPIF Client', 'mTLS onboarding\nService discovery',
     tfs=7.2, sfs=6.1, lw=1.0)

# FastAPI → CAPIF Client
ax.annotate('', xy=(6.57, 4.60), xytext=(6.57, 4.92),
    arrowprops=dict(arrowstyle='->', color=CAP_E, lw=0.9))

# ── Three-Layer Validator (x: 0.66–7.32) ────────────────────────────────────
comp(0.66, 2.62, 6.66, 0.78, VAL_F, VAL_E, '', lw=1.4)
txt(4.00, 3.21, 'Three-Layer Validator', fs=7.6, fw='bold', col=VAL_E)

# L1, L2, L3 sub-boxes
seg_xs = [0.74, 2.92, 5.10]
seg_w  = 2.00
for xp, (top, sub) in zip(seg_xs, [
    ('L1 — Schema',    'Pydantic v2'),
    ('L2 — Policy',    'Telecom semantics'),
    ('L3 — Registry',  'CAPIF live query'),
]):
    comp(xp, 2.69, seg_w, 0.62, '#FFF5F5', VAL_E,
         top, sub, tfs=7.0, sfs=6.0, lw=0.7)
for xv in [2.86, 5.04]:
    ax.plot([xv, xv], [2.71, 3.29], color=VAL_E, lw=0.6, ls=':', zorder=4)

# LLM Planner → Validator
arr(4.02, 3.36, 4.02, 3.40, col=AR, lw=1.1,
    lbl='payload', lx=4.34, ly=3.30)

# Intent Engine (direct) → Validator
ax.annotate('', xy=(0.96, 3.40), xytext=(0.96, 3.68),
    arrowprops=dict(arrowstyle='->', color=DET_E, lw=0.9, linestyle='dashed'))
txt(0.68, 3.54, 'direct', fs=5.3, fw='normal', col=DET_E, sty='italic')

# L3 → CAPIF Client
arr(7.10, 2.99, 6.57, 3.68, col=AR3, lw=0.9, ls='dashed',
    lbl='L3 query', lx=7.24, ly=3.30)

# ── Feedback Engine (x: 0.66–3.26) ─────────────────────────────────────────
comp(0.66, 1.72, 2.60, 0.76, FB_F, FB_E,
     'Feedback Engine', 'Structured correction\nmax 3 iterations',
     tfs=7.2, sfs=6.1, lw=1.0)

# Validator → Feedback (reject)
arr(1.96, 2.62, 1.96, 2.48, col=AR2, lw=1.15,
    lbl='reject', lx=2.30, ly=2.54)

# Feedback → LLM Planner (correction loop)
ax.annotate('', xy=(2.46, 3.80), xytext=(1.96, 2.48),
    arrowprops=dict(arrowstyle='->', color=AR2, lw=1.15,
                    connectionstyle='arc3,rad=-0.30'))
txt(1.28, 3.16, 'correction', fs=5.5, fw='normal', col=AR2, sty='italic')

# Validator → CAMARA (execute — pass)
arr(4.40, 2.62, 5.50, 1.60, col=AR, lw=1.1,
    lbl='execute', lx=5.34, ly=2.06)

# =============================================================================
#  TIER 3a — OpenCAPIF    y: 0.72 – 1.52   x: 0.66 – 4.44
# =============================================================================
# Combined background for both 3a and 3b
tier_strip(0.70, 1.52, '#FAFAF9', '#6B7280', 'Tier 3\nProviders')

# 3a background
rbox(0.66, 0.72, 3.74, 0.80, P_BG, P_BD, lw=0.9, ls='--', z=2, al=0.5)
txt(2.53, 1.44, 'OpenCAPIF Core Function',
    fs=6.0, fw='bold', col=P_BD)

capif_items = [
    ('Register\n:8084/:8080', 0.70, 1.00),
    ('CCF',                   1.80, 0.76),
    ('Vault  :8200',          2.66, 0.92),
    ('nginx  :443',           3.68, 0.66),
]
for lbl, xp, ww in capif_items:
    comp(xp, 0.76, ww, 0.58, P_BG, P_BD, lbl, tfs=6.3, lw=0.7)

# CAPIF Client <-> OpenCAPIF
ax.annotate('', xy=(2.50, 1.52), xytext=(6.57, 3.68),
    arrowprops=dict(arrowstyle='<->', color=P_BD, lw=1.0,
                    connectionstyle='arc3,rad=0.22'))
txt(4.20, 2.72, 'mTLS / discover', fs=5.5, fw='normal',
    col=P_BD, sty='italic')

# =============================================================================
#  TIER 3b — CAMARA Providers    y: 0.72 – 1.52   x: 4.50 – 7.32
# =============================================================================
rbox(4.50, 0.72, 2.82, 0.80, Q_BG, Q_BD, lw=0.9, ls='--', z=2, al=0.5)
txt(5.91, 1.44, 'CAMARA Providers', fs=6.0, fw='bold', col=Q_BD)

camara_items = [
    ('QoD\n:8002',     4.54, 0.84),
    ('Location\n:8003',5.46, 0.92),
    ('NEF-QoS\n:8585', 6.46, 0.84),
]
for lbl, xp, ww in camara_items:
    comp(xp, 0.76, ww, 0.58, Q_BG, Q_BD, lbl, tfs=6.4, lw=0.7)

# =============================================================================
#  TIER 4 — Persistence    y: 0.04 – 0.62   x: 4.50 – 7.32
# =============================================================================
tier_strip(0.03, 0.62, D_BG, D_BD, 'Tier 4\nDB')
cyl(4.80, 0.07, 1.90, 0.46, D_BG, D_BD, 'MongoDB', lfs=7.1)

arr(6.88, 0.76, 6.62, 0.62, col=D_BD, lw=0.9,
    lbl='IMSI/location', lx=7.18, ly=0.67)

# =============================================================================
#  Legend
# =============================================================================
legend_items = [
    mpatches.Patch(fc=U_BG,  ec=U_BD,  ls='--', label='User Interface'),
    mpatches.Patch(fc=C_BG,  ec=C_BD,  ls='--', label='Control Plane'),
    mpatches.Patch(fc=LLM_F, ec=LLM_E,           label='LLM Planner'),
    mpatches.Patch(fc=VAL_F, ec=VAL_E,            label='Validator (L1–L3)'),
    mpatches.Patch(fc=P_BG,  ec=P_BD,  ls='--', label='OpenCAPIF'),
    mpatches.Patch(fc=Q_BG,  ec=Q_BD,  ls='--', label='CAMARA/Persistence'),
    Line2D([0],[0], color=AR,  lw=1.2,                  label='Data flow'),
    Line2D([0],[0], color=AR2, lw=1.2, linestyle='--',  label='Feedback loop'),
]
ax.legend(handles=legend_items, loc='lower left', fontsize=6.2,
          framealpha=0.97, ncol=4, handlelength=1.1, columnspacing=0.7,
          bbox_to_anchor=(LM/W, -0.02))

fig.savefig(OUTPUT)
plt.close(fig)
print(f"OK: {OUTPUT}")
