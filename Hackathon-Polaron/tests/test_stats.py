"""Regression tests for the vcompare/stats.py fixes.

Shipped bugs confirmed 2026-10:
  1. benjamini_hochberg([0.03, 0.04], 0.05) -> [False, True]; the
     elementwise rank gate blocked the step-up rule (correct: [T,T]).
  2. A NaN feature poisoned the permutation null -> obs=NaN -> p=0,
     i.e. falsely maximal significance.

Run:  .venv/bin/python tests/test_stats.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from vcompare import stats


def main():
    # 1) BH step-up
    p = stats.benjamini_hochberg(pd.Series([0.03, 0.04]), 0.05)
    assert p.tolist() == [True, True], p.tolist()
    # nothing passes -> nothing rejected
    p = stats.benjamini_hochberg(pd.Series([0.4, 0.9]), 0.05)
    assert p.tolist() == [False, False]
    # classic example: k-th threshold reached by a later rank rejects all below
    p = stats.benjamini_hochberg(pd.Series([0.001, 0.02, 0.04]), 0.05)
    assert p.tolist() == [True, True, True]   # 0.04 <= 0.05*3/3
    # NaN excluded from family, result for the rest unaffected
    p = stats.benjamini_hochberg(pd.Series([0.001, np.nan, 0.04]), 0.05)
    assert p.tolist()[:1] + p.tolist()[2:] == [True, True]
    assert not p.iloc[1]

    # 2) NaN observed stat -> NaN p, never 0
    va = np.array([[1.0], [np.nan], [2.0], [3.0]])
    vb = np.array([[5.0], [6.0], [7.0]])
    null, obs = stats.median_diff_null(np.vstack([va, vb]), 4)
    pv = stats.exact_pvalues(null, obs)
    assert np.isnan(pv[0]), pv

    # 3) pairwise_table: a NaN feature returns NaN p, not 0
    rng = np.random.default_rng(0)
    feats = pd.DataFrame(dict(
        image_id=[f"i{i}" for i in range(21)],
        batch=["Batch_1"] * 7 + ["Batch_2"] * 7 + ["Batch_3"] * 7,
        clean=np.r_[rng.normal(0, 1, 14), rng.normal(5, 1, 7)],
        with_nan=np.r_[rng.normal(0, 1, 6), np.nan,
                       rng.normal(0, 1, 14)]))
    out = stats.pairwise_table(feats, {}, ("clean", "with_nan"), 200, 0)
    nan_rows = out[out.feature == "with_nan"]
    assert (nan_rows.p_exact.notna()).all()          # filtered, not NaN
    b13 = nan_rows[nan_rows.pair == "Batch_1-Batch_3"].iloc[0]
    assert b13.n_a == 6                              # one dropped
    # an all-NaN feature would be insufficient -> NaN p
    feats["all_nan"] = np.nan
    out2 = stats.pairwise_table(feats, {}, ("all_nan",), 50, 0)
    assert out2.p_exact.isna().all() and out2.insufficient.all()

    print("test_stats: all assertions passed")


if __name__ == "__main__":
    main()
