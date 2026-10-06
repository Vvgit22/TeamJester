"""Corrected reproduction of the QC decision layer on saved features.

Repairs, relative to the shipped QC report:
  * redundancy weights fitted on the REFERENCE batch only
    (the original fitted them on all batches — pooled calibration);
  * held-out (leave-one-image-out) T2 null for the drift pathway;
  * actual image-level exceedance counts with uncertainty, replacing the
    "zero false alarms" assertion.

Reads saved `qc_output/features_*.csv`; does not re-segment and does not
modify polaron_qc.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from polaron_qc.detect import (Baseline, assess_batch, calibrate_thresholds,
                               image_t2)
from polaron_qc.scorecard import build_scorecard, weight_scale


def _wilson_ci(k: int, n: int, z: float = 1.96) -> tuple[float, float]:
    if n == 0:
        return (np.nan, np.nan)
    p = k / n
    den = 1 + z ** 2 / n
    centre = (p + z ** 2 / (2 * n)) / den
    half = z * np.sqrt(p * (1 - p) / n + z ** 2 / (4 * n ** 2)) / den
    return centre - half, centre + half


def run(qc_features_dir: str, batches=("Batch_1", "Batch_2", "Batch_3"),
        seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    tables = {b: pd.read_csv(f"{qc_features_dir}/features_{b}.csv",
                             index_col="image_id") for b in batches}
    baseline = Baseline.fit(tables["Batch_3"])
    pooled = pd.concat(tables.values())

    weights_pooled = weight_scale(build_scorecard(baseline, pooled))
    weights_ref = weight_scale(build_scorecard(baseline, baseline.table))

    # held-out T2 null: score each reference image against the rest
    loo_t2 = np.array([
        image_t2(Baseline.fit(baseline.table.drop(i)).z_scores(
            baseline.table.loc[i])) for i in baseline.table.index])

    calib = calibrate_thresholds(baseline, weights_ref)
    n_ref = len(baseline.table)
    n_exceed = int((calib["loo_max_scores"]
                    > calib["image_flag_thr"]).sum())
    lo, hi = _wilson_ci(n_exceed, n_ref)
    calib_rows = [dict(
        n_reference=n_ref, flag_threshold=calib["image_flag_thr"],
        loo_max=float(calib["loo_max_scores"].max()),
        n_exceedances=n_exceed,
        exceedance_rate=n_exceed / n_ref,
        exceedance_rate_ci_lo=lo, exceedance_rate_ci_hi=hi,
        note="1/17 exceedances expected under LOO calibration; "
             "this is the measured false-alarm rate, not a prediction "
             "for future batches")]
    calib_df = pd.DataFrame(calib_rows)

    cases = [
        ("original_recipe", "Batch_1", tables["Batch_1"],
         weights_pooled, False),
        ("original_recipe", "Batch_2", tables["Batch_2"],
         weights_pooled, False),
        ("reference_only_weights", "Batch_1", tables["Batch_1"],
         weights_ref, False),
        ("reference_weights_and_heldout_T2", "Batch_1", tables["Batch_1"],
         weights_ref, True),
        ("reference_weights_and_heldout_T2", "Batch_2", tables["Batch_2"],
         weights_ref, True),
        ("diagnostic_omit_disputed", "Batch_1",
         tables["Batch_1"].drop(list(_disputed())),
         weights_ref, True),
    ]
    rows = []
    for scenario, name, table, weights, heldout in cases:
        cal = calibrate_thresholds(baseline, weights)
        if heldout:
            cal["baseline_t2"] = loo_t2
        verdict = assess_batch(name, table, baseline, cal, seed=seed,
                               n_boot=20_000, weight_scale=weights)
        rows.append(dict(
            scenario=scenario, batch=name, n_images=len(table),
            verdict=verdict.verdict,
            flag_threshold=cal["image_flag_thr"],
            strict_flags=len(verdict.image_flags),
            p90_exceeders=len(verdict.image_exceeders),
            t2_p=verdict.t2_pvalue,
            significant_features="|".join(verdict.significant_features),
            reasons=" | ".join(verdict.reasons)))
    return pd.DataFrame(rows), calib_df


def _disputed() -> tuple[str, ...]:
    from . import config
    return config.DISPUTED_IMAGES
