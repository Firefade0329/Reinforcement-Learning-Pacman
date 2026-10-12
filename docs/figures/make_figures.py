"""Descriptive figures for the preregistered architecture x n-step study (preview).

Reads ONLY official outputs of the formal run (read-only):
  <RESULTS>/analysis/analysis_20261011_formal/analysis.json
  <RESULTS>/window_diagnostics_summary/window_diagnostics_summary.json
  <RESULTS>/runs/prereg_<arch>_n<N>_s<seed>/train_log.jsonl   (validation rows only: prereg_val seeds 21000-21049)
Computes no new statistic: every plotted number is taken from analysis.json (checked below) except the learning-curve
means/ranges (plain per-step mean/min/max of validation scores) and the epsilon-arithmetic reference curve.
Usage: python make_figures.py <RESULTS_DIR> <OUT_DIR>
"""
import json, sys, math
from pathlib import Path
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

RES = Path(sys.argv[1]); OUT = Path(sys.argv[2]); OUT.mkdir(parents=True, exist_ok=True)
A = json.load(open(RES / 'analysis/analysis_20261011_formal/analysis.json', encoding='utf-8'))
W = json.load(open(RES / 'window_diagnostics_summary/window_diagnostics_summary.json', encoding='utf-8'))
ARCHS = ['cnn2', 'res4', 'res8']
SEEDS = [100, 101, 102, 103, 104]
C1, C3 = '#1f77b4', '#d95f02'  # n=1 blue, n=3 orange (colour-blind safe pair)
FOOT = 'Descriptive figure from the official outputs of the frozen run (freeze commit 92bf82ec); not a new analysis.'
plt.rcParams.update({'font.size': 10, 'axes.spines.top': False, 'axes.spines.right': False, 'figure.dpi': 120})

ep = A['endpoints']['last_standard']
M = ep['model_metrics']; E = ep['effects']

# ---- consistency checks against analysis.json (the plots must not disagree with the official numbers)
for a in ARCHS:
    m1, m3 = np.array(M[f'{a}.n1']['raw_values']), np.array(M[f'{a}.n3']['raw_values'])
    d = E['d'][a]
    assert np.allclose(m1 - m3, d['raw_values'], atol=1e-9), a
    assert abs(m1.mean() - ep['config_summaries'][f'{a}.n1']['mean']) < 1e-9
    assert abs((m1 - m3).mean() - d['mean']) < 1e-9
c = E['c']
assert np.allclose(np.array(E['d']['res8']['raw_values']) - np.array(E['d']['cnn2']['raw_values']), c['raw_values'], atol=1e-9)
print('consistency with analysis.json: OK')


def footer(fig, extra=''):
    import textwrap
    txt = textwrap.fill(FOOT + (' ' + extra if extra else ''), 120)
    fig.text(0.01, 0.005, txt, fontsize=7.5, color='#555555', ha='left', va='bottom')


# ---------------------------------------------------------------- Figure 1: paired seeds
fig, axes = plt.subplots(1, 3, figsize=(10.5, 4.3), sharey=True)
for ax, a in zip(axes, ARCHS):
    m1, m3 = np.array(M[f'{a}.n1']['raw_values']), np.array(M[f'{a}.n3']['raw_values'])
    for s, y1, y3 in zip(SEEDS, m1, m3):
        ax.plot([0, 1], [y1, y3], color='#999999', lw=1, zorder=1)
        ax.scatter([0], [y1], color=C1, s=28, zorder=2)
        ax.scatter([1], [y3], color=C3, s=28, zorder=2)
    ax.plot([0, 1], [m1.mean(), m3.mean()], color='black', lw=2.2, zorder=3)
    ax.scatter([0, 1], [m1.mean(), m3.mean()], color='black', s=55, marker='D', zorder=4)
    d = E['d'][a]
    lo, hi = d['ci975_t']
    ax.set_title(f"{a}: d = {d['mean']:+.1f}  (97.5% t [{lo:.1f}, {hi:.1f}])\n{d['positive_count']}/5 seeds with n=1 higher", fontsize=9.5)
    ax.set_xticks([0, 1]); ax.set_xticklabels(['n = 1', 'n = 3']); ax.set_xlim(-0.35, 1.35)
axes[0].set_ylabel('mean pellets eaten per test episode\n(300 sealed test episodes per run)')
fig.suptitle('Paired training seeds: n=1 vs n=3, last checkpoint, standard scenario (grey lines = same seed; black = 5-seed mean)', fontsize=10.5)
fig.tight_layout(rect=(0, 0.04, 1, 0.94)); footer(fig)
fig.savefig(OUT / 'fig1_paired_seeds.png', dpi=150); plt.close(fig)

# ---------------------------------------------------------------- Figure 2: effects with intervals
fig, ax = plt.subplots(figsize=(10, 4.9))
labels = ['d.cnn2', 'd.res4', 'd.res8', 'c = d.res8 - d.cnn2']
effs = [E['d']['cnn2'], E['d']['res4'], E['d']['res8'], E['c']]
for i, e in enumerate(effs):
    lo, hi = e['ci975_t']; lo95, hi95 = e['ci95_t']
    ax.plot([lo, hi], [i, i], color='black', lw=1.6)
    ax.plot([lo95, hi95], [i, i], color='black', lw=5, alpha=0.35, solid_capstyle='butt')
    ax.scatter([e['mean']], [i], color='black', s=45, zorder=3)
    ax.scatter(e['raw_values'], [i - 0.18] * 5, color='#555555', s=14, alpha=0.8, zorder=2)
ax.axvline(0, color='#888888', lw=1)
for x in (-10, 10):
    ax.axvline(x, color='#c0392b', lw=1, ls='--')
ax.text(10.8, 3.55, '+10', color='#c0392b', fontsize=8); ax.text(-10.8, 3.55, '-10', color='#c0392b', fontsize=8, ha='right')
ax.set_yticks(range(4)); ax.set_yticklabels(labels); ax.invert_yaxis()
ax.set_xlabel('score difference (points)' + chr(10) + 'thin line: 97.5% t interval; thick bar: 95% t interval; small dots: single seeds; dashed: +/-10 threshold')
ax.set_title('Effects with their intervals' + chr(10) + 'H1: lower bound of d.res4 above 10 -> supported;  H2: interval of c reaches both sides -> uncertain', fontsize=9.5)
fig.tight_layout(rect=(0, 0.07, 1, 1)); footer(fig)
fig.savefig(OUT / 'fig2_effects.png', dpi=150); plt.close(fig)

# ---------------------------------------------------------------- Figure 3: validation learning curves
fig, axes = plt.subplots(1, 3, figsize=(10.5, 4.0), sharey=True)
for ax, a in zip(axes, ARCHS):
    for n, col in ((1, C1), (3, C3)):
        curves = []
        for s in SEEDS:
            xs, ys = [], []
            for line in open(RES / f'runs/prereg_{a}_n{n}_s{s}/train_log.jsonl', encoding='utf-8'):
                r = json.loads(line)
                if r.get('type') == 'eval':
                    xs.append(r['env_steps']); ys.append(r['val_score'])
            curves.append((xs, ys))
        xs = curves[0][0]
        assert all(c[0] == xs for c in curves) and len(xs) == 15
        Y = np.array([c[1] for c in curves])
        ax.fill_between(xs, Y.min(0), Y.max(0), color=col, alpha=0.18, lw=0)
        ax.plot(xs, Y.mean(0), color=col, lw=2, label=f'n = {n}')
    ax.set_title(a, fontsize=10); ax.set_xlabel('environment transitions')
    ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{int(v/1000)}k'))
axes[0].set_ylabel('validation score (50 episodes)')
axes[0].legend(frameon=False, loc='upper left')
fig.suptitle('Validation score during training (line = mean of 5 seeds, band = min-max); validation seeds only, not the test set', fontsize=10.5)
fig.tight_layout(rect=(0, 0.04, 1, 0.94)); footer(fig, 'Validation is on prereg_val seeds, GPU, every 20,000 transitions.')
fig.savefig(OUT / 'fig3_validation_curves.png', dpi=150); plt.close(fig)

# ---------------------------------------------------------------- Figure 4: B1 mismatch vs epsilon arithmetic
def eps_at(t):
    return max(0.05, 1.0 - 0.95 * t / 120000.0)


def eps_bin_mean(b):
    ts = np.arange(b * 20000, (b + 1) * 20000, 8)
    return float(np.mean([eps_at(t) for t in ts]))


def mismatch_bin_theory(b, k=2):
    ts = np.arange(b * 20000, (b + 1) * 20000, 8)
    return float(np.mean([1 - (1 - 0.8 * eps_at(t)) ** k for t in ts]))


fig, ax = plt.subplots(figsize=(7.4, 4.4))
x = np.array([b * 20000 + 10000 for b in range(15)])
for cfg, col, ls in (('res4.n3', C3, '-'), ('cnn2.n3', '#7f7f7f', '-'), ('res8.n3', '#2ca02c', '-')):
    ys = []
    for b in range(15):
        per = W['configs'][cfg]['by_start_bin_all_h'][str(b)]['p_later_mismatch_hge2']['per_run']
        ys.append(np.mean([p['rate'] for p in per]))
    ax.plot(x, ys, color=col, lw=2 if cfg == 'res4.n3' else 1.2, ls=ls, marker='o', ms=4, label=f'observed, {cfg} (mean of 5 runs)')
ax.plot(x, [mismatch_bin_theory(b) for b in range(15)], color='black', lw=1.5, ls='--',
        label='epsilon-greedy arithmetic: 1 - (1 - 0.8 eps)^2, two later actions')
ax.plot(x, [eps_bin_mean(b) for b in range(15)], color='#888888', lw=1, ls=':', label='epsilon (bin mean)')
ax.set_xlabel('collection step of the window start'); ax.set_ylabel('fraction of windows (h >= 2)' + chr(10) + 'with a later non-greedy action')
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f'{int(v/1000)}k'))
ax.set_title('B1 window statistic is what epsilon-greedy exploration alone implies', fontsize=10)
ax.legend(frameon=False, fontsize=8, loc='upper right')
fig.tight_layout(rect=(0, 0.08, 1, 1)); footer(fig, 'Reference curve ignores ties; epsilon anneals 1.0 -> 0.05 over the first 120,000 transitions.')
fig.savefig(OUT / 'fig4_b1_epsilon_arithmetic.png', dpi=150); plt.close(fig)

# ---------------------------------------------------------------- Figure 5: death rates
fig, ax = plt.subplots(figsize=(7.4, 4.0))
R = ep['rates_steps']
w = 0.36
for i, a in enumerate(ARCHS):
    for j, (n, col) in enumerate(((1, C1), (3, C3))):
        v = np.array(R[f'{a}.n{n}']['died_rate']['per_model']) * 100
        xpos = i + (j - 0.5) * w
        ax.bar(xpos, v.mean(), width=w * 0.9, color=col, alpha=0.75, label=f'n = {n}' if i == 0 else None)
        ax.scatter([xpos] * 5, v, color='black', s=10, zorder=3)
ax.set_xticks(range(3)); ax.set_xticklabels(ARCHS); ax.set_ylim(0, 105)
ax.set_ylabel('episodes ending in death (%)')
ax.set_title('Death rate on the 300 test episodes (bar = mean of 5 runs; dots = single runs)', fontsize=10)
ax.legend(frameon=False, loc='lower right')
fig.tight_layout(rect=(0, 0.08, 1, 1)); footer(fig, 'Episodes can also end by truncation (1000 steps) or by clearing the map; those rates are in analysis.json.')
fig.savefig(OUT / 'fig5_death_rates.png', dpi=150); plt.close(fig)
print('figures written to', OUT)
