"""Deliverables: START_HERE.md, figures, before/after, technical appendix."""
from __future__ import annotations

import json
import os
import platform
import subprocess

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from . import config

BATCH_COLORS = {"Batch_1": "#C0392B", "Batch_2": "#E67E22",
                "Batch_3": "#2980B9"}


def verdict_class(row: pd.Series, robustness: pd.DataFrame,
                  pair_tab: pd.DataFrame | None = None) -> str:
    """Three honest verdict classes, assigned from primary + robustness."""
    if not row["significant_bh"]:
        return "no_clear_difference_detected"
    feat = row["feature"]
    # acquisition-confound gate: a raw pore count cannot be "supported"
    # if its noise-adjusted sibling in the same pair is not significant
    if feat == "pores_per_mpx" and pair_tab is not None:
        sib = pair_tab[(pair_tab.feature == "pores_per_mpx_noise_adj")
                       & (pair_tab.pair == row["pair"])]
        if len(sib) and not bool(sib.significant_bh.iloc[0]):
            return "possible_difference_image_check_needed"
    scen = robustness[(robustness.feature == feat)
                      & (robustness.pair == row["pair"])]
    # label-dependent if any justified variant loses the same-direction
    # significance or changes sign
    changed = scen[
        (scen.scenario.isin(["pooled_classifier", "omit_disputed",
                             "downsampled_2x"]))
        & ((~scen.significant_bh) | (np.sign(scen.median_diff)
                                     != np.sign(row["median_diff"])))]
    if len(changed):
        return "possible_difference_image_check_needed"
    return "supported_difference"


def fig_findings(feats: pd.DataFrame, out: str) -> None:
    feats9 = config.PRIMARY_FEATURES
    fig, axes = plt.subplots(3, 3, figsize=(15, 12))
    for ax, feat in zip(axes.ravel(), feats9):
        for i, (batch, col) in enumerate(BATCH_COLORS.items()):
            v = feats.loc[feats.batch == batch, feat].dropna()
            jx = np.random.default_rng(0).normal(0, 0.05, len(v))
            ax.scatter(np.full(len(v), i) + jx, v, color=col, s=45,
                       edgecolor="white", linewidth=0.6, zorder=3,
                       label=batch)
            ax.hlines(v.median(), i - 0.28, i + 0.28, color=col,
                      linewidth=3, zorder=4)
        ax.set_xticks(range(3))
        ax.set_xticklabels(["B1", "B2", "B3 (ref)"])
        ax.set_title(feat.replace("_", " "), fontsize=11)
        ax.grid(axis="y", alpha=0.2)
        ax.set_axisbelow(True)
    handles = [plt.Line2D([], [], marker="o", ls="", color=c, label=b)
               for b, c in BATCH_COLORS.items()]
    fig.legend(handles=handles, loc="lower center", ncol=3, fontsize=12)
    fig.suptitle("One dot = one microscope location (primary features)",
                 fontsize=16, fontweight="bold")
    fig.tight_layout(rect=(0, 0.04, 1, 0.97))
    fig.savefig(out, dpi=160)
    plt.close(fig)





def write_start_here(path: str, pair_tab: pd.DataFrame,
                     robustness: pd.DataFrame, qc_verdicts: pd.DataFrame,
                     calib: pd.DataFrame, feats: pd.DataFrame) -> None:
    """<=600 words, four required questions, three verdict classes."""
    v = pair_tab.copy()
    v["verdict"] = v.apply(
        lambda r: verdict_class(r, robustness, pair_tab), axis=1)

    def lines_for(verdict):
        sub = v[v.verdict == verdict]
        return [f"  - {r.pair}: {r.feature} "
                f"(median diff {r.median_diff:+.4g}, "
                f"exact p={r.p_exact:.4f})"
                for r in sub.itertuples()]

    n_disp = int(feats.is_disputed.sum())
    n_ex = int(calib.n_exceedances.iloc[0])
    n_ref = int(calib.n_reference.iloc[0])
    qc_orig = qc_verdicts[qc_verdicts.scenario == "original_recipe"]
    qc_fix = qc_verdicts[
        qc_verdicts.scenario == "reference_weights_and_heldout_T2"]
    qc_txt = " ; ".join(
        f"{r.batch}: {r.verdict}" for r in qc_fix.itertuples())

    mdd_rows = v[v.verdict == "no_clear_difference_detected"]
    mdd_txt = ("  - " + "\n  - ".join(
        f"{r.pair} {r.feature}: undetectable below ~{r.mdd_80pct:.3g}"
        for r in mdd_rows.itertuples())) if len(mdd_rows) else "  - none"

    text = f"""# Validated batch comparison — start here

**What this is:** a re-measurement of the 31 BSE cross-sections under one
recipe frozen on the reference batch (Batch_3, shipment-approved
*selected reference* — not proven defect-free). It answers whether
batch differences survive measurement uncertainty; it does not measure
quality, safety, or cell performance.

## 1. What differences did we measure?

Across 9 declared measurements (Si candidate fraction, uncertain-bright
fraction, Si sizes D50/D90, Si clustering, pore fraction, pore count —
raw and noise-adjusted — and pore anisotropy), comparing all batch pairs
with exact permutation tests (every possible split enumerated — no
random seeds) and Benjamini–Hochberg correction.

## 2. Which survive the image and statistical checks?

**Differences supported under the checked assumptions:**
{chr(10).join(lines_for('supported_difference')) or '  - none'}

## 3. Which depend on uncertain pictures or labels?

**Possible difference — image check needed:**
{chr(10).join(lines_for('possible_difference_image_check_needed')) or '  - none'}

(A raw pore-count excess marked "possible" means it did not survive
noise adjustment: the photos in that batch are noisier, and pore count
rises with noise. The adjusted version is the one to trust.)

{n_disp} Batch_1 photos are unusually low-contrast; the two existing
pipelines disagree by up to ~11 percentage points on how much of their
bright material is silicon. The review sheet in `panels/` lists crops for
human labelling — without independent chemistry (e.g. EDS), the Si
fraction in those regions stays *uncertain bright material*, counted
separately above.

**No clear difference detected** (does NOT prove equivalence — with 7
photos per batch, differences below the listed threshold are simply
invisible to these tests):
{mdd_txt}

## 4. What single extra measurement would most help?

- *Si identity:* an EDS map on any disputed region → resolves the
  bright-material label outright.
- *Pore-count noise:* one low-dose/low-noise repeat image per batch →
  tests whether the noise-adjusted ordering holds.
- *Independent quality verdict:* any measurement independent of these
  images (e.g. electrochemical half-cell capacity) → calibrates what the
  image markers actually predict.

## QC recheck (corrected reproduction of the original pipeline)

With reference-fitted weights and held-out baseline calibration:
{qc_txt}. The original "zero false alarms" claim is wrong: {n_ex}/{n_ref}
reference images exceed the flag threshold under leave-one-out scoring.

*All comparisons are indicators about these images under the stated
recipe — not predictions of cell behaviour.*
"""
    with open(path, "w") as fh:
        fh.write(text)


def write_before_after(path: str, qc_verdicts: pd.DataFrame,
                       pair_tab: pd.DataFrame,
                       robustness: pd.DataFrame) -> None:
    rows = [
        ("'Zero false alarms' on baseline self-scores",
         "1/17 reference images exceed the flag threshold (LOO)",
         "The generator asserted zero without counting"),
        ("Batch_1 = REJECT (excess Si)",
         qc_verdicts.set_index("scenario").loc[
             "reference_weights_and_heldout_T2"].query(
             "batch=='Batch_1'").verdict.iloc[0],
         "REJECT depended on redundancy weights fitted on all batches; "
         "reference-only weights give INVESTIGATE on identical features"),
        ("Silicon fractions treated as measured",
         "Split into si_candidate + uncertain_bright; ambiguous material "
         "counted separately",
         "An intensity filter cannot establish chemical identity"),
        ("Permutation p-values with seed 0",
         "Exact permutation — all splits enumerated",
         "B2's verdict was seed-sensitive; enumeration removes the seed"),
        ("'No significant difference' read as 'same'",
         "Every non-significant test reports its minimum detectable "
         "difference",
         "With n=7 only large effects are detectable"),
    ]
    df = pd.DataFrame(rows, columns=["earlier_claim", "now", "why"])
    with open(path, "w") as fh:
        fh.write("# Before / after — what changed and why\n\n")
        fh.write("| earlier_claim | now | why |\n|---|---|---|\n")
        for _, r in df.iterrows():
            fh.write("| " + " | ".join(str(r[c]).replace("|", "\\|")
                                       for c in df.columns) + " |\n")
        fh.write("\n")


def write_appendix(path: str, recipe: dict, pair_tab: pd.DataFrame,
                   run_settings: dict) -> None:
    try:
        import skimage, scipy
        versions = dict(numpy=np.__version__, pandas=pd.__version__,
                        scipy=scipy.__version__, skimage=skimage.__version__,
                        python=platform.python_version())
    except Exception:
        versions = {}
    with open(path, "w") as fh:
        fh.write(f"""# Technical appendix — validated comparison

## Reproduce

```bash
{run_settings.get('command', '.venv/bin/python run_compare.py --data Hackathon-Polaron --out validated_comparison')}
```

## Software versions

{json.dumps(versions, indent=2)}

## Run settings

{json.dumps(run_settings, indent=2)}

## Frozen recipe (reference batch only)

{json.dumps(recipe, indent=2)}

## Statistics

- Test statistic: difference of **medians** (the same statistic for the
  estimate and its interval).
- p-values: **exact permutation** — all assignments enumerated
  (C(24,7)=346,104 for 7-vs-17; C(14,7)=3,432 for 7-vs-7). No seed
  dependence.
- Multiplicity: Benjamini–Hochberg at FDR {config.FDR_ALPHA} within each
  batch pair across the {len(config.PRIMARY_FEATURES)} declared features.
- CIs: percentile bootstrap over images ({config.N_BOOT} resamples,
  seed {config.SEED}). Images are the independent sampling unit —
  pixels/particles are not.
- MDD: `mdd_critical` is the smallest |median diff| rejected at
  alpha={config.PERM_ALPHA}; `mdd_80pct` is the smallest location shift
  giving >={int(config.MDD_POWER*100)}% power under a pure-shift model.

## Exclusions / unknowns

- No specimen/location metadata in the TIFFs — image-level is the only
  known sampling unit; locations within a batch may not be independent.
- `Batch_3` = shipment-approved **selected reference**; not verified
  defect-free. All differences are relative to it.
- `Batch_1/*_segmentation.npy` (7 files): leftover 4-class colour
  clustering from an early `segment_images.py`; known to mislabel
  graphite — **unused**, kept for provenance only.
- InLens fine-line/crack measures are secondary: acquisition
  comparability across images is unresolved.

## DFN outputs — known defects, not used here

`dfn_output/` model numbers are **not trustworthy** pending repair
(separate task): the OKane2022 parameter merge overwrites silicon OCP/
exchange/mechanics with graphite values; the LAM constant is 3600x too
fast (1e-3 vs 2.7778e-7 s-1); the capacity readout differences full
cycle endpoints of a running counter; `--fast` runs were reported as
full-res 5-cycle. Treat all DFN indicators as requiring correction.

## Remaining limitations

- "No clear difference" does not prove equivalence (see MDD column).
- The uncertain-bright category is conditional on the frozen recipe;
  alternative thresholds shift membership (stress test reported in
  robustness.csv).
- No independent labels: expert review sheet is produced, not filled.
""")
