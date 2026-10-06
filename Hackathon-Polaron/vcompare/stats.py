"""Exact permutation tests + bootstrap CIs + minimum detectable difference.

With n1+n2 <= 24 the full split space is enumerable (C(24,7)=346,104;
C(14,7)=3,432), so permutation p-values are exact — no seed, no Monte
Carlo.  The enumerated null also yields the minimum detectable
difference: the smallest |median diff| the test could reject, and the
location shift giving ~80% power.
"""
from __future__ import annotations

import itertools
from functools import lru_cache

import numpy as np
import pandas as pd


@lru_cache(maxsize=None)
def _combos(n: int, k: int) -> np.ndarray:
    """All k-subsets of range(n), shape (C(n,k), k)."""
    return np.asarray(list(itertools.combinations(range(n), k)),
                      dtype=np.int64)


def median_diff_null(vals: np.ndarray, n1: int) -> tuple[np.ndarray, np.ndarray]:
    """Exact permutation null of median(A)-median(B) for each column.

    vals: (n, F) values; rows 0..n1-1 are group A.  Returns
    (null diffs (n_combos, F), observed diffs (F,)).
    """
    vals = np.asarray(vals, dtype=np.float64)
    n, n_feat = vals.shape
    n2 = n - n1
    c = _combos(n, n1)
    nc = len(c)
    sel = np.zeros((nc, n), bool)
    sel[np.arange(nc)[:, None], c] = True
    med_a = np.median(vals[c], axis=1)                    # (nc, F)
    flat = np.broadcast_to(vals, (nc, n, n_feat))
    med_b = np.median(flat[~sel].reshape(nc, n2, n_feat), axis=1)
    obs = np.median(vals[:n1], axis=0) - np.median(vals[n1:], axis=0)
    return med_a - med_b, obs


def exact_pvalues(null: np.ndarray, obs: np.ndarray) -> np.ndarray:
    """Two-sided exact p = fraction of |null| >= |obs| (obs is in null).

    Non-finite observed stats (e.g. a NaN feature — np.median propagates)
    would otherwise give p=0, i.e. falsely maximal significance; they
    return NaN instead."""
    obs = np.asarray(obs, dtype=np.float64)
    p = (np.abs(null) >= np.abs(obs) - 1e-12).mean(axis=0)
    p[~np.isfinite(obs)] = np.nan
    return p


def bootstrap_median_ci(a: np.ndarray, b: np.ndarray, n_boot: int,
                        seed: int, alpha: float = 0.05
                        ) -> tuple[float, float]:
    rng = np.random.default_rng(seed)
    idx_a = rng.integers(0, len(a), (n_boot, len(a)))
    idx_b = rng.integers(0, len(b), (n_boot, len(b)))
    d = np.median(a[idx_a], axis=1) - np.median(b[idx_b], axis=1)
    return tuple(np.quantile(d, [alpha / 2, 1 - alpha / 2]))


def mdd_from_null(null_col: np.ndarray, alpha: float = 0.05,
                  power: float = 0.80) -> tuple[float, float]:
    """(critical_value, shift_for_power) from an enumerated null column.

    critical_value: smallest |d| rejected at two-sided `alpha`.
    shift_for_power: smallest location shift delta such that a test at
    `alpha` rejects with probability >= `power` under a pure-shift model
    (P(|D + delta| > crit) >= power, D the null distribution).
    """
    d = np.sort(np.asarray(null_col))
    ad = np.abs(d)
    crit = np.quantile(ad, 1 - alpha)
    # power(delta) = P(|D + delta| > crit); monotone in delta for delta>0
    # => delta* = crit - quantile(D, 1 - power)  (upper tail dominates)
    delta = crit - np.quantile(d, 1 - power)
    return float(crit), float(delta)


def benjamini_hochberg(pvals: pd.Series, alpha: float) -> pd.Series:
    """Standard BH step-up: let k be the largest rank with
    p_(k) <= alpha*k/m; reject all hypotheses with p <= p_(k).

    The previous elementwise `p <= alpha*rank/m` gate blocked the
    step-up rule: BH([0.03, 0.04], 0.05) must reject BOTH (the rank-2
    threshold is 0.05) but returned [False, True]. NaN p-values are
    excluded from the family (m counts finite values only)."""
    p = pvals.astype(float)
    out = pd.Series(False, index=p.index)
    finite = p.dropna().sort_values()
    m = len(finite)
    if not m:
        return out
    thresh = alpha * np.arange(1, m + 1) / m
    passed = finite.to_numpy() <= thresh
    if not passed.any():
        return out
    crit = float(finite.iloc[np.flatnonzero(passed).max()])
    out.loc[p.index[p <= crit]] = True
    return out


def pairwise_table(features: pd.DataFrame, batches: dict[str, list[str]],
                   cols: tuple[str, ...], n_boot: int, seed: int
                   ) -> pd.DataFrame:
    """3 batch pairs x len(cols): median diff, exact p, bootstrap CI, MDD."""
    rows = []
    pairs = [("Batch_1", "Batch_3"), ("Batch_2", "Batch_3"),
             ("Batch_1", "Batch_2")]
    for name_a, name_b in pairs:
        a = features[features.batch == name_a]
        b = features[features.batch == name_b]
        # per-feature finite filtering: a NaN in ANY feature used to
        # poison the shared permutation null (np.median propagates),
        # turning that feature's p into 0 — maximal false significance.
        for feat in cols:
            va = a[feat].to_numpy(float)
            vb = b[feat].to_numpy(float)
            va = va[np.isfinite(va)]
            vb = vb[np.isfinite(vb)]
            if len(va) < 2 or len(vb) < 2:
                rows.append(dict(
                    pair=f"{name_a}-{name_b}", feature=feat,
                    median_a=np.median(va) if len(va) else np.nan,
                    median_b=np.median(vb) if len(vb) else np.nan,
                    median_diff=np.nan, ci_lo=np.nan, ci_hi=np.nan,
                    p_exact=np.nan, n_a=len(va), n_b=len(vb),
                    mdd_critical=np.nan, mdd_80pct=np.nan,
                    insufficient=True))
                continue
            vals = np.c_[np.r_[va, vb]]
            null, obs = median_diff_null(vals, len(va))
            p = exact_pvalues(null, obs)
            ci = bootstrap_median_ci(va, vb, n_boot, seed)
            crit, delta = mdd_from_null(null[:, 0])
            rows.append(dict(
                pair=f"{name_a}-{name_b}", feature=feat,
                median_a=np.median(va), median_b=np.median(vb),
                median_diff=obs[0], ci_lo=ci[0], ci_hi=ci[1],
                p_exact=p[0], n_a=len(va), n_b=len(vb),
                mdd_critical=crit, mdd_80pct=delta,
                insufficient=False))
    out = pd.DataFrame(rows)
    out["significant_bh"] = False
    for pair in out.pair.unique():
        m = out.pair == pair
        out.loc[m, "significant_bh"] = benjamini_hochberg(
            out.loc[m, "p_exact"], config_fdr()).values
    return out


def config_fdr() -> float:
    from . import config
    return config.FDR_ALPHA


def loo_sweep(features: pd.DataFrame, pair: tuple[str, str],
              cols: tuple[str, ...]) -> pd.DataFrame:
    """Leave-one-image-out: exact p and median diff per omitted image."""
    name_a, name_b = pair
    a = features[features.batch == name_a]
    b = features[features.batch == name_b]
    rows = []
    for drop_id in list(a.image_id) + list(b.image_id):
        a2 = a[a.image_id != drop_id]
        b2 = b[b.image_id != drop_id]
        for feat in cols:
            va = a2[feat].to_numpy(float)
            vb = b2[feat].to_numpy(float)
            va = va[np.isfinite(va)]
            vb = vb[np.isfinite(vb)]
            if len(va) < 2 or len(vb) < 2:
                rows.append(dict(pair=f"{name_a}-{name_b}",
                                 dropped=drop_id, feature=feat,
                                 median_diff=np.nan, p_exact=np.nan))
                continue
            vals = np.c_[np.r_[va, vb]]
            null, obs = median_diff_null(vals, len(va))
            p = exact_pvalues(null, obs)
            rows.append(dict(pair=f"{name_a}-{name_b}", dropped=drop_id,
                             feature=feat, median_diff=obs[0],
                             p_exact=p[0]))
    return pd.DataFrame(rows)
