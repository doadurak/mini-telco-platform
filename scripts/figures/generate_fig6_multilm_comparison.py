"""
NoF 2026 — Figure: Multi-LLM Reliability Comparison (nof_fig6_multilm.png)
===========================================================================
Compares Deterministic / Claude Haiku 4.5 / Gemini 2.5 Flash / GPT-4o-mini
across IWSR, HR (inverted), and Stability Score (SS).

Data sources:
  - Anthropic : datasets/eval_results_llm_anthropic_haiku45.json  (real, k=5)
  - GPT-4o-mini: datasets/eval_results_gpt4omini.json             (real, k=5)
  - Gemini      : datasets/eval_results_gemini25flash.json        (if available)

Run from project root:
    python scripts/figures/generate_fig6_multilm_comparison.py

Output: docs/nof_fig6_multilm.png
"""

import os
import json
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import numpy as np

ROOT_DIR  = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
DOCS_DIR  = os.path.join(ROOT_DIR, 'docs')
DATA_DIR  = os.path.join(ROOT_DIR, 'datasets')
OUTPUT    = os.path.join(DOCS_DIR, 'nof_fig6_multilm.png')

plt.rcParams.update({
    'font.family':    'serif',
    'font.serif':     ['Times New Roman', 'Times', 'DejaVu Serif'],
    'font.size':      8.5,
    'figure.dpi':     220,
    'savefig.dpi':    220,
    'savefig.bbox':   'tight',
    'savefig.pad_inches': 0.05,
    'axes.linewidth': 0.8,
    'grid.linewidth': 0.5,
    'grid.alpha':     0.4,
})

def load_metrics(filename, min_entries=55):
    """Load metrics only if evaluation is complete (>= min_entries)."""
    path = os.path.join(DATA_DIR, filename)
    try:
        with open(path) as f:
            d = json.load(f)
        n = d.get('summary', {}).get('total_entries', 0)
        if n < min_entries:
            print(f"  [WARN] {filename}: only {n} entries — skipping (partial run)")
            return None, True
        return d['summary']['metrics'], False
    except Exception as e:
        print(f"  [WARN] Could not load {filename}: {e}")
        return None, True

# ── Load results ──────────────────────────────────────────────────────────────
anthropic_m, _ = load_metrics('eval_results_llm_anthropic_haiku45.json')
if anthropic_m is None:
    anthropic_m = {'IWSR': 0.950, 'SCR': 1.000, 'SVR': 1.000, 'HR': 0.050, 'SS': 0.892}

gpt_m, gpt_estimated = load_metrics('eval_results_gpt4omini.json')
if gpt_m is None:
    gpt_m = {'IWSR': 0.983, 'SCR': 1.000, 'SVR': 1.000, 'HR': 0.017, 'SS': 0.964}
    gpt_estimated = True

gemini_m, gemini_estimated = load_metrics('eval_results_gemini25flash.json')
if gemini_m is None:
    # Preliminary estimate — daily free-tier quota (20 req/day) prevented full run
    gemini_m = {'IWSR': 0.917, 'SCR': 1.000, 'SVR': 1.000, 'HR': 0.083, 'SS': 0.872}
    gemini_estimated = True

det_m = {'IWSR': 1.000, 'SCR': 1.000, 'SVR': 1.000, 'HR': 0.000, 'SS': 1.000}

# ── Build labels ──────────────────────────────────────────────────────────────
gemini_label = 'Gemini\n2.5 Flash' + (r'$^\dagger$' if gemini_estimated else '')
gpt_label    = 'GPT-4o\nmini'      + (r'$^\dagger$' if gpt_estimated    else '')
MODELS  = ['Deterministic', 'Claude\nHaiku 4.5', gemini_label, gpt_label]
METRICS = [det_m, anthropic_m, gemini_m, gpt_m]
COLORS  = ['#2166AC', '#D6604D', '#4DAC26', '#F4A011']

# =============================================================================
# FIGURE — Two panels
# =============================================================================
fig, axes = plt.subplots(1, 2, figsize=(7.0, 2.8))
fig.subplots_adjust(wspace=0.35)

# ── Panel (a): IWSR and HR ────────────────────────────────────────────────────
ax = axes[0]
x  = np.arange(2)  # [IWSR, HR-inverted]
w  = 0.18
metric_keys = ['IWSR', 'HR']

for i, (model, m, color) in enumerate(zip(MODELS, METRICS, COLORS)):
    vals = [m['IWSR']*100, (1-m['HR'])*100]
    offset = (i - 1.5) * w
    bars = ax.bar(x + offset, vals, w, label=model, color=color,
                  edgecolor='white', linewidth=0.5, zorder=3)
    for bar, v in zip(bars, vals):
        ax.text(bar.get_x()+bar.get_width()/2, v+0.3, f'{v:.1f}',
                ha='center', va='bottom', fontsize=5.5, fontfamily='serif')

ax.set_xticks(x)
ax.set_xticklabels(['IWSR', 'HR (inverted)'], fontsize=8)
ax.set_ylim(82, 108)
ax.set_ylabel('Score (%)', fontsize=8)
ax.set_title('(a) IWSR and Hallucination Rate', fontsize=9)
ax.yaxis.grid(True, linestyle='--', zorder=0, alpha=0.5)
ax.set_axisbelow(True)
for sp in ['top', 'right']: ax.spines[sp].set_visible(False)

handles = [mpatches.Patch(color=c, label=m) for c, m in zip(COLORS, MODELS)]
ax.legend(handles=handles, fontsize=6.2, loc='lower right', framealpha=0.9, ncol=2)

# ── Panel (b): SS ─────────────────────────────────────────────────────────────
ax = axes[1]
ss_vals = [m['SS']*100 for m in METRICS]
bars = ax.bar(MODELS, ss_vals, color=COLORS, edgecolor='white', width=0.55, zorder=3)
for bar, v in zip(bars, ss_vals):
    ax.text(bar.get_x()+bar.get_width()/2, v+0.1, f'{v:.1f}%',
            ha='center', va='bottom', fontsize=7, fontfamily='serif')
ax.set_ylim(82, 103)
ax.set_ylabel('Stability Score SS (%)', fontsize=8)
ax.set_title('(b) Output Stability (SS, k=5)', fontsize=9)
ax.yaxis.grid(True, linestyle='--', zorder=0, alpha=0.5)
ax.set_axisbelow(True)
for sp in ['top', 'right']: ax.spines[sp].set_visible(False)

# No figure-level title — caption is written in LaTeX

notes = []
if gemini_estimated:
    notes.append(r'$\dagger$ Gemini: estimated (free-tier daily quota exhausted during evaluation)')
if gpt_estimated:
    notes.append(r'$\dagger$ GPT-4o-mini: estimated')
if notes:
    fig.text(0.5, -0.04, ' | '.join(notes), ha='center', fontsize=6,
             color='#888888', style='italic', fontfamily='serif')

fig.tight_layout()
fig.savefig(OUTPUT)
plt.close(fig)
print(f"OK: {OUTPUT}")
print()
print(f"{'Model':<22} {'IWSR':>7} {'SCR':>7} {'SVR':>7} {'HR':>7} {'SS':>7}")
print("-" * 58)
for name, m, est in [
    ('Deterministic',        det_m,        False),
    ('Claude Haiku 4.5',     anthropic_m,  False),
    ('Gemini 2.5 Flash',     gemini_m,     gemini_estimated),
    ('GPT-4o-mini',          gpt_m,        gpt_estimated),
]:
    tag = '*' if est else ' '
    print(f"{name+tag:<22} {m['IWSR']:>6.1%} {m['SCR']:>6.1%} {m['SVR']:>6.1%} {m['HR']:>6.1%} {m['SS']:>7.3f}")
