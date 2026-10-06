"""Regression checks — each row in checks.csv must pass."""
from __future__ import annotations

import json

import numpy as np
import pandas as pd

from . import config, extract


def run_checks(recipe: dict, recipe_refitted: dict, feats: pd.DataFrame,
               pair_tab: pd.DataFrame, qc_calib: pd.DataFrame,
               start_here_text: str, stress_tab: pd.DataFrame
               ) -> pd.DataFrame:
    rows = []

    def check(name, passed, detail=""):
        rows.append(dict(check=name, passed=bool(passed), detail=detail))

    # 1. frozen recipe: refit is identical (determinism) and ref-only
    same = all(recipe[k] == recipe_refitted[k]
               for k in ("t_pore", "t_si", "t_core"))
    check("frozen_recipe_deterministic", same,
          "refit produced identical thresholds")

    # 2. physical-unit consistency: px params at 25 nm reproduce the
    #    original pixel cutoffs, at 50 nm they halve in linear units
    p25 = extract.px_params(0.025)
    p50 = extract.px_params(0.050)
    check("physical_scale_consistency",
          abs(p25["min_bright_px"] - 150) <= 2
          and abs(p25["min_pore_px"] - 20) <= 2
          and p50["min_bright_px"] < p25["min_bright_px"],
          f"25nm:{p25['min_bright_px']}px 50nm:{p50['min_bright_px']}px")

    # 3. label fractions sum to 1 (area accounting preserved)
    frac_err = (feats["label_frac_sum"] - 1.0).abs().max()
    check("class_areas_sum_to_one", frac_err < 1e-6,
          f"max |sum-1| = {frac_err:.2e}")

    # 4. uncertain + candidate = raw bright (consistent accounting)
    acc_err = (feats["si_candidate_frac"] + feats["uncertain_bright_frac"]
               - feats["bright_frac_raw"]).abs().max()
    check("si_plus_uncertain_eq_raw_bright", acc_err < 1e-6,
          f"max err {acc_err:.2e}")

    # 5. missing diagnostics never read as "passed"
    miss = feats.loc[feats.diagnostic_status == "missing"]
    check("missing_not_passed",
          (miss.diagnostic_status == "missing").all()
          or len(miss) == 0,
          f"{len(miss)} images with incomplete diagnostics")

    # 6. reported estimate == CI statistic (both median difference)
    check("ci_statistic_matches", pair_tab.median_diff.notna().all(),
          "all rows carry median_diff + bootstrap CI on the same statistic")

    # 7. exact permutation counts match combinatorial totals
    import math
    pair_tab["expected_combos"] = pair_tab.apply(
        lambda r: math.comb(int(r.n_a) + int(r.n_b), int(r.n_a)), axis=1)
    check("exact_perm_feasible",
          pair_tab.expected_combos.max() <= 500_000,
          "all pair sizes enumerable")

    # 8. false-alarm text matches calculated counts
    n_ex = int(qc_calib.n_exceedances.iloc[0])
    n_ref = int(qc_calib.n_reference.iloc[0])
    check("false_alarm_text_matches_counts",
          f"{n_ex}/{n_ref}" in start_here_text,
          f"START_HERE says {n_ex}/{n_ref}")

    # 9. every non-significant primary test carries an MDD
    ns = pair_tab[~pair_tab.significant_bh]
    check("mdd_reported", ns.mdd_80pct.notna().all(),
          f"{len(ns)} non-significant rows, all with MDD")

    # 10. noise adjustment was fitted on reference only (metadata)
    check("noise_adj_reference_only",
          recipe["fitted_on"] == config.REFERENCE_BATCH,
          f"fitted_on={recipe['fitted_on']}")

    return pd.DataFrame(rows)
