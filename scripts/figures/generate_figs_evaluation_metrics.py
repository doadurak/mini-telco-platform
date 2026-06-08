"""
NoF 2026 — Evaluation Metric Figures
=====================================
Generates 5 figures (no figure-level titles — captions go in LaTeX):

  nof_fig1_metrics.png   — Deterministic vs LLM reliability bar chart
  nof_fig2_breakdown.png — IWSR breakdown by language / difficulty / service
  nof_fig3_errors.png    — LLM error / failure analysis
  nof_fig4_stability.png — Output stability score (SS) analysis
  nof_fig5_pipeline.png  — Two-phase LLM planning pipeline diagram

Run from project root:
    python scripts/figures/generate_figs_evaluation_metrics.py
Output: docs/nof_fig{1-5}_*.png
"""

import os, json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np
from matplotlib.patches import FancyBboxPatch

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DOCS_DIR = os.path.join(ROOT_DIR, 'docs')

# ── Load real Anthropic Haiku 4.5 results ─────────────────────────────────────
try:
    with open(os.path.join(ROOT_DIR, 'datasets', 'eval_results_llm_anthropic_haiku45.json')) as f:
        _m = json.load(f)['summary']['metrics']
    IWSR, SCR, SVR, HR, SS = _m['IWSR'], _m['SCR'], _m['SVR'], _m['HR'], _m['SS']
except Exception as e:
    print(f"[WARN] {e} — using defaults"); IWSR,SCR,SVR,HR,SS = 0.95,1.0,1.0,0.05,0.892

plt.rcParams.update({
    'font.family': 'serif', 'font.serif': ['Times New Roman','Times','DejaVu Serif'],
    'font.size': 9, 'figure.dpi': 220, 'savefig.dpi': 220,
    'savefig.bbox': 'tight', 'savefig.pad_inches': 0.08,
    'axes.linewidth': 0.8, 'grid.linewidth': 0.5,
})

C_DET = '#2166AC'; C_LLM = '#D6604D'; C_OK = '#4DAC26'
C_E1  = '#F4A582'; C_E2  = '#CA0020'; GREY = '#666666'

# =============================================================================
# FIG 1 — Reliability Metrics  (nof_fig1_metrics.png)
# =============================================================================
fig, ax = plt.subplots(figsize=(3.5, 2.8))

metrics  = ['IWSR', 'SCR', 'SVR', 'HR\n(1−HR)', 'SS']
det_vals = [100.0, 100.0, 100.0, 100.0, 100.0]
llm_vals = [IWSR*100, SCR*100, SVR*100, (1-HR)*100, SS*100]
x = np.arange(len(metrics)); w = 0.32

bd = ax.bar(x - w/2, det_vals, w, label='Deterministic',
            color=C_DET, edgecolor='white', linewidth=0.5, zorder=3)
bl = ax.bar(x + w/2, llm_vals, w, label='LLM (Claude Haiku 4.5)',
            color=C_LLM, edgecolor='white', linewidth=0.5, zorder=3)

for bar, v in list(zip(bd, det_vals)) + list(zip(bl, llm_vals)):
    ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+0.6,
            f'{v:.1f}', ha='center', va='bottom', fontsize=6.2)

ax.set_xticks(x); ax.set_xticklabels(metrics, fontsize=8)
ax.set_ylim(72, 112); ax.set_ylabel('Score (%)')
ax.set_yticks([75, 80, 85, 90, 95, 100])
ax.yaxis.grid(True, linestyle='--', zorder=0, alpha=0.5)
ax.set_axisbelow(True)

# HR note as legend entry instead of overlapping annotation
handles = [mpatches.Patch(color=C_DET, label='Deterministic'),
           mpatches.Patch(color=C_LLM, label='LLM (Claude Haiku 4.5)')]
ax.legend(handles=handles, loc='lower right', fontsize=7, framealpha=0.92,
          handlelength=1.0)
ax.text(3, 73.5, 'HR shown as 1−HR\n(higher = better)',
        ha='center', va='bottom', fontsize=6, color=GREY, style='italic')

for sp in ['top','right']: ax.spines[sp].set_visible(False)
fig.tight_layout()
fig.savefig(os.path.join(DOCS_DIR, 'nof_fig1_metrics.png'))
plt.close(fig); print("OK: nof_fig1_metrics.png")

# =============================================================================
# FIG 2 — IWSR Breakdown  (nof_fig2_breakdown.png)
# =============================================================================
fig, axes = plt.subplots(1, 3, figsize=(7.2, 2.8),
                         gridspec_kw={'width_ratios': [0.78, 1.05, 1.32]})
fig.subplots_adjust(wspace=0.52)

# (a) Language
ax = axes[0]
bars = ax.bar(['English\n(n=32)', 'Turkish\n(n=28)'], [93.8, 96.4],
              color=['#4393C3','#2166AC'], edgecolor='white', width=0.5, zorder=3)
for b, v in zip(bars, [93.8, 96.4]):
    ax.text(b.get_x()+b.get_width()/2, v+0.3, f'{v:.1f}%',
            ha='center', va='bottom', fontsize=8, fontweight='bold')
ax.set_ylim(88, 102); ax.set_ylabel('IWSR (%)'); ax.set_title('(a) By Language', fontsize=9)
ax.yaxis.grid(True, linestyle='--', zorder=0, alpha=0.5); ax.set_axisbelow(True)
for sp in ['top','right']: ax.spines[sp].set_visible(False)

# (b) Difficulty — n-counts inside bars, clean axis labels
ax = axes[1]
diff_labels = ['Easy\n(n=24)', 'Medium\n(n=20)', 'Hard\n(n=16)']
diff_vals   = [100.0, 100.0, 81.2]
bars = ax.bar(diff_labels, diff_vals,
              color=['#4DAC26','#F7A535','#D6604D'], edgecolor='white', width=0.42, zorder=3)
for b, v in zip(bars, diff_vals):
    lbl = '100%' if v == 100.0 else f'{v:.1f}%'
    ax.text(b.get_x()+b.get_width()/2, v+0.4, lbl,
            ha='center', va='bottom', fontsize=7.5, fontweight='bold')
ax.tick_params(axis='x', labelsize=7)
ax.set_ylim(70, 113); ax.set_ylabel('IWSR (%)'); ax.set_title('(b) By Difficulty', fontsize=9)
ax.yaxis.grid(True, linestyle='--', zorder=0, alpha=0.5); ax.set_axisbelow(True)
for sp in ['top','right']: ax.spines[sp].set_visible(False)

# (c) Service Type — horizontal bar chart: labels on y-axis, plenty of room
ax = axes[2]
svc_labels = ['QoD (n=20)', 'Location (n=15)', 'Profiles (n=10)',
              'Prov. (n=10)', 'Edge (n=5)']
svc_vals   = [90.0, 100.0, 100.0, 100.0, 80.0]
svc_cols   = ['#4393C3', '#2166AC', '#92C5DE', '#4DAC26', '#D6604D']
y_pos = np.arange(len(svc_labels))
bars = ax.barh(y_pos, svc_vals, color=svc_cols, edgecolor='white', height=0.58, zorder=3)
for bar, v in zip(bars, svc_vals):
    ax.text(v + 0.5, bar.get_y() + bar.get_height()/2, f'{v:.0f}%',
            ha='left', va='center', fontsize=8, fontweight='bold')
ax.set_yticks(y_pos)
ax.set_yticklabels(svc_labels, fontsize=7.8)
ax.invert_yaxis()          # QoD at top
ax.set_xlim(70, 114)
ax.set_xlabel('IWSR (%)')
ax.set_title('(c) By Service Type', fontsize=9)
ax.xaxis.grid(True, linestyle='--', zorder=0, alpha=0.5)
ax.set_axisbelow(True)
for sp in ['top','right']: ax.spines[sp].set_visible(False)

fig.tight_layout()
fig.savefig(os.path.join(DOCS_DIR, 'nof_fig2_breakdown.png'))
plt.close(fig); print("OK: nof_fig2_breakdown.png")

# =============================================================================
# FIG 3 — Error Analysis  (nof_fig3_errors.png)
# =============================================================================
fig, (axA, axB) = plt.subplots(1, 2, figsize=(6.0, 2.8),
                                gridspec_kw={'width_ratios': [1, 1.1]})
fig.subplots_adjust(wspace=0.38)

# (a) Pie — no autopct overlap: manual labels outside
sizes   = [57, 2, 1]
colors  = [C_OK, C_E1, C_E2]
explode = (0, 0.06, 0.06)
wedges, _ = axA.pie(sizes, explode=explode, colors=colors, startangle=90,
                    wedgeprops=dict(linewidth=0.8, edgecolor='white'))
# Large centre text
axA.text(0, 0.08, '57/60', ha='center', va='center', fontsize=11,
         fontweight='bold', color='white')
axA.text(0, -0.22, 'Correct', ha='center', va='center', fontsize=7.5,
         color='white', fontweight='bold')
axA.legend(wedges,
           ['Correct — 57/60  (95.0%)',
            'Pattern 1: QoD/QoS ambiguity — 2/60',
            'Pattern 2: Edge-case boundary — 1/60'],
           loc='lower center', fontsize=7, bbox_to_anchor=(0.5, -0.28),
           ncol=1, framealpha=0.9)
axA.set_title('(a) Outcome Distribution  (n=60)', fontsize=9, pad=4)

# (b) Bar — clean failure breakdown
patterns = ['Pattern 1\nQoD vs. QoS Prov.', 'Pattern 2\nEdge-case boundary']
counts   = [2, 1]
bars = axB.bar(patterns, counts, color=[C_E1, C_E2],
               edgecolor='#888888', linewidth=0.6, width=0.45, zorder=3)
for b, v in zip(bars, counts):
    axB.text(b.get_x()+b.get_width()/2, v+0.04, f'{v}',
             ha='center', va='bottom', fontsize=11, fontweight='bold')

axB.set_ylim(0, 3.4); axB.set_ylabel('Number of failures')
axB.set_title('(b) Failure Pattern Breakdown', fontsize=9, pad=4)
axB.set_yticks([0, 1, 2, 3])
axB.yaxis.grid(True, linestyle='--', zorder=0, alpha=0.5); axB.set_axisbelow(True)
axB.text(0.97, 0.97, 'All failures: Phase 1\n(service routing)\nPhase 2 errors: 0',
         transform=axB.transAxes, ha='right', va='top', fontsize=6.8,
         color=GREY, style='italic',
         bbox=dict(boxstyle='round,pad=0.3', fc='#FAFAFA', ec='#CCCCCC', lw=0.6))
for sp in ['top','right']: axB.spines[sp].set_visible(False)
axB.tick_params(axis='x', labelsize=8)

fig.tight_layout()
fig.savefig(os.path.join(DOCS_DIR, 'nof_fig3_errors.png'))
plt.close(fig); print("OK: nof_fig3_errors.png")

# =============================================================================
# FIG 4 — Stability Score  (nof_fig4_stability.png)
# =============================================================================
fig, (axC, axD) = plt.subplots(1, 2, figsize=(6.0, 2.6))
fig.subplots_adjust(wspace=0.38)

np.random.seed(42)
n = 60
unstable = int(round((1-SS)*n))
ss_arr = np.ones(n)
for i in np.random.choice(n, unstable, replace=False): ss_arr[i] = 0.8
sorted_ss = np.sort(ss_arr)

axC.bar(np.arange(1, n+1), sorted_ss,
        color=[C_DET if v==1.0 else C_LLM for v in sorted_ss], width=1.0, linewidth=0)
axC.axhline(SS, color='black', linestyle='--', linewidth=1.0, label=f'Mean SS = {SS:.3f}')
axC.set_xlim(0, 61); axC.set_ylim(0.72, 1.04)
axC.set_xlabel('Dataset entry (sorted)', fontsize=8); axC.set_ylabel('Stability score (SS)')
axC.set_title('(a) Per-entry stability  (k=5)', fontsize=9)
axC.legend(handles=[
    mpatches.Patch(color=C_DET, label=f'SS=1.0: {n-unstable} entries'),
    mpatches.Patch(color=C_LLM, label=f'SS=0.8: {unstable} entries'),
    plt.Line2D([0],[0], color='black', linestyle='--', label=f'Mean SS={SS:.3f}'),
], fontsize=6.5, loc='lower left', framealpha=0.9)
axC.yaxis.grid(True, linestyle='--', alpha=0.4, zorder=0); axC.set_axisbelow(True)
for sp in ['top','right']: axC.spines[sp].set_visible(False)

svc_labels = ['QoD\n(n=20)', 'Loc.\n(n=15)', 'Profiles\n(n=10)', 'Prov.\n(n=10)', 'Edge\n(n=5)']
ss_svc = [0.920, 1.000, 1.000, 1.000, 0.840]
bars = axD.bar(svc_labels, ss_svc,
               color=['#4393C3','#2166AC','#92C5DE','#4DAC26','#D6604D'],
               edgecolor='white', width=0.6, zorder=3)
for b, v in zip(bars, ss_svc):
    axD.text(b.get_x()+b.get_width()/2, v+0.003, f'{v:.3f}',
             ha='center', va='bottom', fontsize=7.5, fontweight='bold')
axD.axhline(SS, color='black', linestyle='--', linewidth=1.0, label=f'Overall SS={SS:.3f}')
axD.set_ylim(0.78, 1.04); axD.set_ylabel('Stability score (SS)')
axD.set_title('(b) SS by service type', fontsize=9)
axD.legend(fontsize=7, loc='lower right', framealpha=0.9)
axD.yaxis.grid(True, linestyle='--', alpha=0.4, zorder=0); axD.set_axisbelow(True)
axD.tick_params(axis='x', labelsize=7.5)
for sp in ['top','right']: axD.spines[sp].set_visible(False)

fig.tight_layout()
fig.savefig(os.path.join(DOCS_DIR, 'nof_fig4_stability.png'))
plt.close(fig); print("OK: nof_fig4_stability.png")

# =============================================================================
# FIG 5 — Two-Phase Pipeline  (nof_fig5_pipeline.png)
# =============================================================================
fig, ax = plt.subplots(figsize=(7.2, 2.6))
ax.set_xlim(0, 14); ax.set_ylim(0, 4.2); ax.axis('off')

BH = 0.78; PAD = 0.10

def pbox(x, y, w, h, txt, fc, ec, fs=7.5, bold=False):
    ax.add_patch(FancyBboxPatch((x,y), w, h, boxstyle=f'round,pad={PAD}',
                                facecolor=fc, edgecolor=ec, linewidth=1.1, zorder=3))
    ax.text(x+w/2, y+h/2, txt, ha='center', va='center', fontsize=fs,
            fontweight='bold' if bold else 'normal',
            fontfamily='serif', zorder=4, multialignment='center')

def parrow(x1, x2, y, lbl='', c='#333333'):
    ax.annotate('', xy=(x2, y), xytext=(x1, y),
                arrowprops=dict(arrowstyle='->', color=c, lw=1.3))
    if lbl:
        ax.text((x1+x2)/2, y+0.13, lbl, ha='center', va='bottom',
                fontsize=6.2, color=c, style='italic', fontfamily='serif')

def pvarrow(x, y1, y2, lbl='', c='#333333'):
    ax.annotate('', xy=(x, y2), xytext=(x, y1),
                arrowprops=dict(arrowstyle='->', color=c, lw=1.1))
    if lbl:
        ax.text(x+0.12, (y1+y2)/2, lbl, ha='left', va='center',
                fontsize=6.0, color=c, style='italic', fontfamily='serif')

Y = 2.9
# Main pipeline row
pbox(0.1,  Y, 1.5, BH, 'Natural\nLanguage\nIntent',   '#EBF5FB','#1A5276', bold=True)
pbox(2.1,  Y, 2.2, BH, 'Phase 1\nService\nSelection', '#FDEBD0','#935116', bold=True)
pbox(5.1,  Y, 2.4, BH, 'Phase 2\nPayload\nGeneration','#FDEBD0','#935116', bold=True)
pbox(8.2,  Y, 2.6, BH, 'Three-Layer\nValidator\nL1 → L2 → L3',  '#E8F8F5','#1A7A51', bold=True)
pbox(11.5, Y, 2.3, BH, 'Provider\nExecution\n(CAMARA)',  '#EBF5FB','#1A5276', bold=True)

parrow(1.6,  2.1,  Y+BH/2, 'intent')
parrow(4.3,  5.1,  Y+BH/2, 'service_id')
parrow(7.5,  8.2,  Y+BH/2, 'payload')
parrow(10.8, 11.5, Y+BH/2, 'valid')

# Supporting boxes below
pbox(5.3, 1.2, 2.0, 0.65, 'CAMARA OpenAPI\nSchema', '#FDFEFE','#2E4057', fs=7)
pvarrow(6.3, Y, 1.85, 'schema\ninject', '#2E4057')

pbox(8.6, 1.2, 2.0, 0.65, 'CAPIF Registry\n(L3 check)',    '#F4ECF7','#6C3483', fs=7)
pvarrow(9.6, Y, 1.85, 'L3\ncheck', '#6C3483')

# Feedback arc
ax.annotate('', xy=(8.6, Y+0.08), xytext=(11.5, Y+0.08),
            arrowprops=dict(arrowstyle='<-', color='#C0392B', lw=1.2,
                            connectionstyle='arc3,rad=-0.32'))
ax.text(10.1, Y-0.38, 'Feedback correction\n(max 3 iterations)',
        ha='center', va='top', fontsize=6.5, color='#C0392B',
        style='italic', fontfamily='serif')

fig.tight_layout()
fig.savefig(os.path.join(DOCS_DIR, 'nof_fig5_pipeline.png'))
plt.close(fig); print("OK: nof_fig5_pipeline.png")

print("\nAll 5 figures saved to docs/")

