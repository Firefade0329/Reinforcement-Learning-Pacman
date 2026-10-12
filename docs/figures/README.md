# Figures for the preregistered architecture x n-step study

Descriptive figures made from the official outputs of the frozen run (freeze commit
`92bf82eca0dae731f7396ed5b4e887e4f3b200e4`). They contain no new statistic: every plotted number is read from
`analysis.json` (the script asserts that the paired values, means and differences equal the official ones), except the
validation learning-curve means/ranges and the epsilon-arithmetic reference curve, which are plain per-step means/ranges
and a closed-form expression.

| file | shows |
|---|---|
| `fig1_paired_seeds.png` | the five paired training seeds, n=1 vs n=3, per architecture (last checkpoint, standard scenario) |
| `fig2_effects.png` | d for each architecture and the interaction c, with 97.5 % and 95 % t intervals and the +/-10 threshold |
| `fig3_validation_curves.png` | validation score during training (validation seeds only; not the test set) |
| `fig4_b1_epsilon_arithmetic.png` | the B1 window statistic against 1 - (1 - 0.8 epsilon)^2 |
| `fig5_death_rates.png` | share of test episodes ending in death, per configuration and run |

The figures describe this study only; the wording limits in `docs/PREREG_RESULTS.md` (sections 5 and 6) apply to them.

**Regenerating.** The script reads the extracted results bundle of the release
`prereg-v0.3.2-r1-results-92bf82eca0da` (it needs `analysis/`, `window_diagnostics_summary/` and `runs/*/train_log.jsonl`,
in the layout of `results_prereg/`) and matplotlib:

```
python make_figures.py <results_prereg directory> <output directory>
```
