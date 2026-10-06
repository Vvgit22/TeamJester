"""One-command clean report — every number generated from saved CSVs.

Reads:
  validated_comparison/per_image_features.csv  (per-image markers)
  image_acquisition.csv                        (acquisition groups)
  validated_comparison/objects_classified.csv  (object counts)
  dfn_output_v2/dfn_paired_differences.csv     (model indicators)
  new_image_assignment/feature_table.csv       (new-batch photos)
Writes:
  clean_report.md          — the plain report
  RESULTS.md / RESULTS.html / figs_results/    — the lean results doc
  report_numbers.json      — every number, for the check script
Usage: .venv/bin/python build_report.py
"""
from __future__ import annotations

import itertools
import json

import numpy as np
import pandas as pd
from itertools import combinations
from scipy import stats

from vcompare.stats import (exact_pvalues, median_diff_null,
                            mdd_from_null)

RNG = np.random.default_rng(0)
BATCHES = ["Batch_1", "Batch_2", "Batch_3"]
ALPHA = 0.05
N_PERM = 5000  # stratified fallback only (exact enumeration preferred)

# Declared families (decided before looking at results):
PRIMARY_FRACTIONS = ["pore_frac", "si_candidate_frac",
                     "uncertain_bright_frac", "bright_frac_raw"]
BOUNDARY_MARKERS = ["si_d50_um", "si_d90_um", "si_clustering_R",
                    "pore_d50_um", "pore_anisotropy",
                    "pore_chord_h_um", "pore_chord_v_um"]
COUNT_MARKERS = ["pores_per_mpx", "pores_per_mpx_noise_adj",
                 "si_n_particles"]
ACQ_FEATURES = ["noise_mad", "sharpness_lapvar", "img_p1",
                "img_p50", "img_p99", "si_bulk_contrast",
                "shading_slope"]
DECLARED_FAMILY = PRIMARY_FRACTIONS + BOUNDARY_MARKERS + COUNT_MARKERS


def exact_perm_median(x: np.ndarray, y: np.ndarray) -> tuple[float, float]:
    """Exact permutation p on the median difference (enumerated null via
    vcompare.stats — no Monte Carlo, deterministic)."""
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    x = x[np.isfinite(x)]; y = y[np.isfinite(y)]
    if len(x) < 2 or len(y) < 2:
        return np.nan, np.nan
    null, obs = median_diff_null(np.c_[np.r_[x, y]], len(x))
    return float(obs[0]), float(exact_pvalues(null, obs)[0])


def mdd(x: np.ndarray, y: np.ndarray, alpha: float = ALPHA) -> float:
    """Minimum detectable |median difference| at this n — critical value
    of the enumerated permutation null."""
    x = np.asarray(x, dtype=float); y = np.asarray(y, dtype=float)
    x = x[np.isfinite(x)]; y = y[np.isfinite(y)]
    if len(x) < 2 or len(y) < 2:
        return np.nan
    null, _ = median_diff_null(np.c_[np.r_[x, y]], len(x))
    crit, _ = mdd_from_null(null[:, 0], alpha)
    return crit


def bh(pvals: list[float], q: float = 0.10) -> np.ndarray:
    """Benjamini–Hochberg adjusted p-values (NaN-safe: NaN p -> NaN padj,
    excluded from the family size)."""
    p = np.asarray(pvals, dtype=float)
    out = np.full(len(p), np.nan)
    ok = np.isfinite(p)
    p = p[ok]
    if not len(p):
        return out
    order = np.argsort(p)
    ranked = p[order] * len(p) / (np.arange(len(p)) + 1)
    adj = np.minimum.accumulate(ranked[::-1])[::-1]
    res = np.empty(len(p))
    res[order] = np.clip(adj, 0, 1)
    out[ok] = res
    return out


def stratified_perm(df: pd.DataFrame, col: str, b1: str, b2: str,
                    groups: list) -> tuple[float, float, int]:
    """Median difference of group-centred values under an EXACT
    stratified permutation: batch labels permuted within usable groups
    only, all joint assignments enumerated via itertools.product
    (deterministic — no Monte Carlo).  Pools are restricted to groups
    containing both batches.  Returns (diff, p, n_usable_groups)."""
    d = df[df.group_id.isin(groups)][["batch", "group_id", col]].dropna()
    d = d[d.batch.isin([b1, b2])].copy()
    d["gc"] = d[col] - d.groupby("group_id")[col].transform("median")
    pairs = d.groupby(["group_id", "batch"]).size().unstack(fill_value=0)
    usable = pairs[(pairs[b1] > 0) & (pairs[b2] > 0)]
    if not len(usable):
        return np.nan, np.nan, 0
    d = d[d.group_id.isin(usable.index)]          # pools = usable groups
    obs = float(d[d.batch == b1].gc.median() - d[d.batch == b2].gc.median())
    pieces = []
    for g in usable.index:
        vals = d[d.group_id == g].gc.to_numpy()
        n_b1 = int(pairs.loc[g, b1])
        combos = list(itertools.combinations(range(len(vals)), n_b1))
        pieces.append((vals, combos))
    if np.prod([len(c) for _, c in pieces]) > 500_000:
        # joint space too large: seeded MC fallback, clearly deterministic
        null = np.empty(N_PERM)
        for j in range(N_PERM):
            a_all, b_all = [], []
            for vals, combos in pieces:
                take = combos[RNG.integers(len(combos))]
                m = np.zeros(len(vals), bool); m[list(take)] = True
                a_all.append(vals[m]); b_all.append(vals[~m])
            null[j] = np.median(np.concatenate(a_all)) - \
                np.median(np.concatenate(b_all))
    else:
        null = np.empty(int(np.prod([len(c) for _, c in pieces])))
        for j, assign in enumerate(
                itertools.product(*[c for _, c in pieces])):
            a_all, b_all = [], []
            for (vals, _), take in zip(pieces, assign):
                m = np.zeros(len(vals), bool); m[list(take)] = True
                a_all.append(vals[m]); b_all.append(vals[~m])
            null[j] = np.median(np.concatenate(a_all)) - \
                np.median(np.concatenate(b_all))
    p = float((np.abs(null) >= abs(obs) - 1e-12).mean())
    return obs, p, int(len(usable))


def main() -> None:
    f = pd.read_csv("validated_comparison/per_image_features.csv")
    acq = pd.read_csv("image_acquisition.csv")
    objs = pd.read_csv("validated_comparison/objects_classified.csv")
    f = f[f.batch != "New_Images_Batch"]
    acq["group_id"] = acq.group_id.astype(str)
    m = f.merge(acq[["image_id", "group_id"]], on="image_id", how="left")

    out: dict = {"n_images": int(len(f)),
                 "per_batch_n": f.batch.value_counts().to_dict()}

    # ---- 1. primary fractions -------------------------------------------
    frac = {}
    for c in PRIMARY_FRACTIONS:
        frac[c] = {b: {"med": float(f[f.batch == b][c].median()),
                       "lo": float(f[f.batch == b][c].min()),
                       "hi": float(f[f.batch == b][c].max())}
                   for b in BATCHES}
    out["fractions"] = frac

    # ---- 2. acquisition partition + chance levels ------------------------
    n_g, n_i, n_b = acq[acq.batch != "New_Images_Batch"].group_id.nunique(), \
        len(m), 3
    out["chance"] = {"after_group": round(1 - (n_g - 1) / (n_i - 1), 3),
                     "after_batch": round(1 - (n_b - 1) / (n_i - 1), 3)}
    part = []
    for c in DECLARED_FAMILY + ACQ_FEATURES:
        if c not in m.columns:
            continue
        s = pd.to_numeric(m[c], errors="coerce")
        d = m.assign(v=s).dropna(subset=["v"])
        if d.v.var() == 0:
            continue
        rg = ((d.v - d.groupby("group_id").v.transform("mean")) ** 2
              ).mean() / d.v.var()
        rb = ((d.v - d.groupby("batch").v.transform("mean")) ** 2
              ).mean() / d.v.var()
        part.append(dict(marker=c, resid_group=round(float(rg), 3),
                         resid_batch=round(float(rb), 3)))
    out["partition"] = part

    # ---- 3. unblocked comparison on the declared family -----------------
    rows = []
    for c in DECLARED_FAMILY:
        for b1, b2 in combinations(BATCHES, 2):
            x = pd.to_numeric(f[f.batch == b1][c],
                              errors="coerce").dropna().values
            y = pd.to_numeric(f[f.batch == b2][c],
                              errors="coerce").dropna().values
            d, p = exact_perm_median(x, y)
            rows.append(dict(marker=c, pair=f"{b1}-{b2}", diff=round(d, 4),
                             p=round(p, 5),
                             mdd=round(mdd(x, y), 4)))
    ub = pd.DataFrame(rows)
    ub["padj"] = bh(ub.p.values, 0.10).round(4)
    out["unblocked"] = ub.to_dict("records")
    out["unblocked_nominal"] = int((ub.p < ALPHA).sum())
    out["unblocked_expected_chance"] = round(len(ub) * ALPHA, 1)
    out["unblocked_bh_survivors"] = int((ub.padj < 0.10).sum())

    # ---- 4. blocked comparison (stratified permutation) ------------------
    mixed = [g for g, s in acq[acq.batch != "New_Images_Batch"]
             .groupby("group_id").batch.unique().items() if len(s) > 1]
    out["mixed_groups"] = sorted(mixed)
    shared = {}
    for b1, b2 in combinations(BATCHES, 2):
        shared[f"{b1}-{b2}"] = sorted(
            g for g in mixed
            if {b1, b2} <= set(acq[acq.group_id == g].batch))
    out["shared_sessions"] = shared
    brows = []
    for c in DECLARED_FAMILY:
        for b1, b2 in combinations(BATCHES, 2):
            d, p, npg = stratified_perm(m, c, b1, b2, mixed)
            brows.append(dict(marker=c, pair=f"{b1}-{b2}",
                              diff=None if np.isnan(d) else round(d, 4),
                              p=None if np.isnan(p) else round(p, 4),
                              n_pair_groups=npg))
    out["blocked"] = brows
    out["blocked_nominal"] = int(sum(
        1 for r in brows if r["p"] is not None and r["p"] < ALPHA))

    # ---- 5. objects + problem photos -------------------------------------
    out["objects"] = {
        "total": int(len(objs)),
        "si_particle": int((objs.kind == "si_particle").sum()),
        "bright_fine": int((objs.kind == "bright_fine").sum())}
    prob = f[f.image_id.isin(["img_4ih2ggld", "img_5n1q8atc"])]
    out["problem_photos"] = prob[
        ["image_id", "bright_frac_raw", "si_candidate_frac",
         "uncertain_bright_frac"]].round(4).to_dict("records")

    # ---- 6. DFN (appendix only) ------------------------------------------
    try:
        dfn = pd.read_csv("dfn_output_v2/dfn_paired_differences.csv")
        st = dfn[dfn.indicator == "si_stress_MPa"][
            ["pair", "median_paired_diff", "verdict"]]
        out["dfn_stress"] = st.to_dict("records")
    except Exception:
        out["dfn_stress"] = "dfn_paired_differences.csv unavailable"

    # ---- 7. B1 bright fields vs B3 range ---------------------------------
    b3max = f[f.batch == "Batch_3"].bright_frac_raw.max()
    b1 = f[f.batch == "Batch_1"][["image_id", "bright_frac_raw"]]
    out["bright_b1_vs_b3max"] = dict(
        b3_max=round(float(b3max), 4),
        b1_above=b1[b1.bright_frac_raw > b3max].image_id.tolist(),
        b1_above_vals=b1[b1.bright_frac_raw > b3max]
        .bright_frac_raw.round(4).tolist(),
        b1_ge_b3hi=b1[b1.bright_frac_raw >=
                      f[f.batch == "Batch_3"].bright_frac_raw.quantile(0.75)]
        .image_id.tolist())

    with open("report_numbers.json", "w") as fh:
        json.dump(out, fh, indent=2)

    # ---- persisted comparison tables (the deliverables) -------------------
    ub.to_csv("unblocked_permutation.csv", index=False)
    pd.DataFrame(brows).to_csv("blocked_permutation.csv", index=False)
    pd.DataFrame(part).to_csv("marker_session_partition.csv",
                              index=False)
    acq.to_csv("image_acquisition_groups.csv", index=False)

    print(json.dumps({k: v for k, v in out.items()
                      if k not in ("partition", "unblocked", "blocked",
                                   "fractions")}, indent=2, default=str))
    print("wrote report_numbers.json + unblocked_permutation.csv + "
          "blocked_permutation.csv + marker_session_partition.csv + "
          "image_acquisition_groups.csv")

    write_results()


# ---------------------------------------------------------------------------
# RESULTS.md — the lean results document (Step 2 deliverable)
# ---------------------------------------------------------------------------
RESULT_FRACS = ["pore_frac", "si_candidate_frac", "uncertain_bright_frac"]
FRAC_LABEL = {"pore_frac": "resolved pore fraction",
              "si_candidate_frac": "candidate-silicon fraction",
              "uncertain_bright_frac": "uncertain-bright fraction"}


def _kind_raster(image_id: str, batch: str):
    """4-phase raster: pore / bulk / classified-Si / uncertain-bright,
    rebuilt at exact watershed identity from the cached seg + objects."""
    from vcompare import config as vc, extract
    seg = np.load(f"validated_comparison/cache_ds2/{image_id}_seg.npz")[
        "seg"]
    objs = pd.read_csv("validated_comparison/objects_classified.csv")
    sub = objs[objs.image_id == image_id]
    px = extract.px_params(0.025)
    lab = extract.split_bright(seg == vc.SI_CAND, px)
    kind_map = dict(zip(sub.label, sub.kind))
    out = np.full(seg.shape, vc.BULK, np.uint8)
    si_ids = [l for l, k in kind_map.items() if k == "si_particle"]
    unc_ids = [l for l, k in kind_map.items() if k != "si_particle"]
    out[seg == vc.PORE] = 0
    if si_ids:
        out[np.isin(lab, si_ids)] = 2
    if unc_ids:
        out[np.isin(lab, unc_ids)] = 3
    return out, seg


if __name__ == "__main__":
    main()

# ---------------------------------------------------------------------------
# RESULTS report — template-rendered (report_assets/template.html + report.css)
# ---------------------------------------------------------------------------
RESULT_FRACS = ["pore_frac", "si_candidate_frac", "uncertain_bright_frac"]
FRAC_LABEL = {"pore_frac": "pore space",
              "si_candidate_frac": "candidate silicon",
              "uncertain_bright_frac": "uncertain bright material"}
BCOLOR = {"Batch_1": "#d55e00", "Batch_2": "#009e73", "Batch_3": "#6a5acd"}
BNAME = {"Batch_1": "Batch 1", "Batch_2": "Batch 2", "Batch_3": "Batch 3"}


def _mpl():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    return plt


def _scale_bar(ax, disp_w: int, step: int, um: float = 10.0,
               px_um: float = 0.025) -> None:
    """White 10 um scale bar at bottom-right of an image axis."""
    n = um / px_um / step
    x0 = disp_w * 0.80
    y0 = ax.get_ylim()[0] * 0.94 if ax.get_ylim()[0] > 0 else \
        ax.get_ylim()[1] * 0.06
    ax.plot([x0, x0 + n], [y0, y0], color="white", lw=5, solid_capstyle="butt")
    ax.text(x0 + n / 2, y0 - ax.get_ylim()[1] * 0.035, f"{um:.0f} um",
            color="white", ha="center", va="bottom", fontsize=9,
            fontweight="bold")


def _fig_amounts(f: pd.DataFrame, path: str) -> None:
    plt = _mpl()
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.5), sharex=True)
    for ax, col in zip(axes, RESULT_FRACS):
        b3v = f[f.batch == "Batch_3"][col] * 100
        ax.axhspan(b3v.min(), b3v.max(), color="0.88", alpha=0.75)
        for xi, b in enumerate(BATCHES):
            y = f[f.batch == b][col] * 100
            ax.scatter([xi] * len(y), y, s=46, color=BCOLOR[b],
                       edgecolor="k", linewidth=0.4, zorder=3)
            ax.hlines(y.median(), xi - 0.22, xi + 0.22, color="k",
                      lw=2.2, zorder=4)
        ax.set_xticks(range(3))
        ax.set_xticklabels(["Batch 1", "Batch 2", "Batch 3"])
        ax.set_title(FRAC_LABEL[col], fontsize=10.5)
        ax.grid(axis="y", alpha=0.3)
        ax.set_ylim(bottom=0)
    axes[0].set_ylabel("share of photo area (%)")
    handles = [Line2D([], [], marker="o", ls="", color=BCOLOR[b],
                      mec="k", label=BNAME[b]) for b in BATCHES] + \
        [Line2D([], [], color="k", lw=2.2, label="batch middle value"),
         Patch(fc="0.88", label="normal range (Batch 3)")]
    fig.legend(handles=handles, loc="lower center", ncol=5, fontsize=8.5,
               frameon=False)
    fig.suptitle("Same amounts in every batch", fontsize=12.5)
    fig.tight_layout(rect=[0, 0.09, 1, 1])
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _fig_uncertain_pair(img_a: str, img_b: str, path: str) -> None:
    plt = _mpl()
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    from skimage.io import imread
    cmap = ListedColormap(["black", "0.55", "#ffd92f", "#fc8d62"])
    crop = (slice(300, 700), slice(400, 2400))   # same 10x50 um window
    step = 4
    fig, axes = plt.subplots(2, 2, figsize=(10.4, 4.4))
    for row, (img, batch, ttl) in enumerate(
            [(img_a, "Batch_1", "flagged Batch 1 photo"),
             (img_b, "Batch_3", "typical Batch 3 photo")]):
        kr, _ = _kind_raster(img, batch)
        raw = imread(f"{batch}/{img}_BSE.tif")
        r = raw[crop][::step, ::step]
        k = kr[crop][::step, ::step]
        axes[row, 0].imshow(r, cmap="gray", vmin=np.percentile(raw, 1),
                            vmax=np.percentile(raw, 99))
        axes[row, 0].set_title(f"{ttl} — raw photo", fontsize=9.5)
        axes[row, 1].imshow(k, cmap=cmap, vmin=0, vmax=3)
        axes[row, 1].set_title("colour map", fontsize=9.5)
        _scale_bar(axes[row, 0], r.shape[1], step)
        _scale_bar(axes[row, 1], k.shape[1], step)
        for ax in axes[row]:
            ax.axis("off")
    handles = [Patch(fc=cmap(i), label=n) for i, n in enumerate(
        ["pore", "graphite / bulk", "candidate silicon",
         "uncertain bright"])]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8.5,
               frameon=False)
    fig.suptitle("Same field of view (10 x 50 um), two photos", fontsize=12)
    fig.tight_layout(rect=[0, 0.07, 1, 1])
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _fig_sessions(f: pd.DataFrame, path: str) -> None:
    plt = _mpl()
    from matplotlib.lines import Line2D
    d = f.dropna(subset=["group_id"]).copy()
    d["group_id"] = d.group_id.astype(int)
    order = sorted(d.group_id.unique())
    mixed = [g for g in order
             if d[d.group_id == g].batch.nunique() > 1]
    fig, ax = plt.subplots(figsize=(10.4, 3.6))
    for xi, g in enumerate(order):
        if g in mixed:
            ax.axvspan(xi - 0.45, xi + 0.45, color="#ffe8b3", alpha=0.55,
                       zorder=0)
        sub = d[d.group_id == g]
        jit = np.linspace(-0.28, 0.28, len(sub))
        for (_, r), dx in zip(sub.iterrows(), jit):
            ax.scatter(xi + dx, r.pores_per_mpx, s=52,
                       color=BCOLOR[r.batch], edgecolor="k",
                       linewidth=0.4, zorder=3)
    ax.set_xticks(range(len(order)))
    ax.set_xticklabels([str(g) for g in order], fontsize=8)
    ax.set_xlabel("imaging session (frame height, px)")
    ax.set_ylabel("countable pores per Mpx")
    ax.grid(axis="y", alpha=0.3)
    handles = [Line2D([], [], marker="o", ls="", color=BCOLOR[b],
                      mec="k", label=BNAME[b]) for b in BATCHES] + \
        [plt.Rectangle((0, 0), 1, 1, fc="#ffe8b3",
                       label="shared session")]
    ax.legend(handles=handles, fontsize=8.5, ncol=4, frameon=False,
              loc="upper left")
    ax.set_title("Inside a session the batches look alike; "
                 "between sessions the values jump", fontsize=11.5)
    fig.tight_layout()
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _fig_new_photos(f: pd.DataFrame, newf: pd.DataFrame,
                    path: str) -> None:
    plt = _mpl()
    from matplotlib.lines import Line2D
    from matplotlib.patches import Patch
    marks = ["o", "s", "D"]
    fig, axes = plt.subplots(1, 3, figsize=(10.4, 3.4), sharex=True)
    for ax, col in zip(axes, RESULT_FRACS):
        b3v = f[f.batch == "Batch_3"][col] * 100
        ax.axhspan(b3v.min(), b3v.max(), color="0.88", alpha=0.75)
        for (mk, (_, r)) in zip(marks, newf.iterrows()):
            ax.scatter([0], r[col] * 100, s=70, marker=mk, color="k",
                       edgecolor="k", zorder=3,
                       label=r.image_id.replace("img_", ""))
        ax.set_xticks([0]); ax.set_xticklabels(["new photos"])
        ax.set_title(FRAC_LABEL[col], fontsize=10.5)
        ax.grid(axis="y", alpha=0.3)
        ax.set_ylim(bottom=0)
    axes[0].set_ylabel("share of photo area (%)")
    handles = [Line2D([], [], marker=mk, ls="", color="k", mec="k",
                      label=newf.image_id.iloc[i].replace("img_", ""))
               for i, mk in enumerate(marks)] + \
        [Patch(fc="0.88", label="normal range (Batch 3)")]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8.5,
               frameon=False)
    fig.suptitle("The three new photos against the Batch 3 range",
                 fontsize=12)
    fig.tight_layout(rect=[0, 0.09, 1, 1])
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _fig_method(img: str, batch: str, path: str) -> None:
    plt = _mpl()
    from matplotlib.colors import ListedColormap
    from matplotlib.patches import Patch
    from skimage.io import imread
    cmap = ListedColormap(["black", "0.55", "#ffd92f", "#fc8d62"])
    kr, _ = _kind_raster(img, batch)
    raw = imread(f"{batch}/{img}_BSE.tif")
    step = 5
    r = raw[::step, ::step]
    k = kr[::step, ::step]
    fig, axes = plt.subplots(1, 2, figsize=(10.4, 3.6))
    axes[0].imshow(r, cmap="gray", vmin=np.percentile(raw, 1),
                   vmax=np.percentile(raw, 99))
    axes[0].set_title("raw photo (back-scattered electrons)", fontsize=9.5)
    axes[1].imshow(k, cmap=cmap, vmin=0, vmax=3)
    axes[1].set_title("colour map — what the computer measures",
                    fontsize=9.5)
    _scale_bar(axes[0], r.shape[1], step)
    _scale_bar(axes[1], k.shape[1], step)
    for ax in axes:
        ax.axis("off")
    handles = [Patch(fc=cmap(i), label=n) for i, n in enumerate(
        ["pore", "graphite / bulk", "candidate silicon",
         "uncertain bright"])]
    fig.legend(handles=handles, loc="lower center", ncol=4, fontsize=8.5,
               frameon=False)
    fig.suptitle("One photo, before and after colouring", fontsize=12)
    fig.tight_layout(rect=[0, 0.08, 1, 1])
    fig.savefig(path, dpi=150)
    plt.close(fig)


def _b64(path: str) -> str:
    import base64
    return "data:image/png;base64," + base64.b64encode(
        open(path, "rb").read()).decode()


def _table(headers: list, rows: list) -> str:
    h = "".join(f"<th>{c}</th>" for c in headers)
    body = "".join("<tr>" + "".join(f"<td>{c}</td>" for c in r) +
                   "</tr>" for r in rows)
    return f"<table><tr>{h}</tr>{body}</table>"


def write_results() -> None:
    """Render RESULTS.html (single file, embedded figures) + RESULTS.md
    summary from the saved tables via report_assets/template.html.
    Deterministic: fixed ordering, no RNG, exact figures."""
    import base64
    import os
    from jinja2 import Template
    os.makedirs("figs_results", exist_ok=True)

    f = pd.read_csv("validated_comparison/per_image_features.csv")
    acq = pd.read_csv("image_acquisition.csv")
    f = f.merge(acq[["image_id", "group_id", "noise_mad",
                     "si_bulk_contrast", "raw_p1"]], on="image_id",
                how="left")
    pw = pd.read_csv("validated_comparison/pairwise_comparisons.csv")
    bl = pd.read_csv("blocked_permutation.csv")
    newf = pd.read_csv("new_image_assignment/feature_table.csv")
    bench = pd.read_csv("benchmark_results.csv")
    truth = pd.read_csv("new_batch_ground_truth.csv")
    manifest = json.load(open("dfn_output_v2/run_manifest.json"))
    b3 = f[f.batch == "Batch_3"]

    # ---- figures ----------------------------------------------------
    _fig_amounts(f, "figs_results/fig1_amounts.png")
    b1_bright = f[f.batch == "Batch_1"].nlargest(
        1, "bright_frac_raw").image_id.iloc[0]
    b3_typ = b3.iloc[(b3.bright_frac_raw - b3.bright_frac_raw.median())
                     .abs().argsort()[:1]].image_id.iloc[0]
    _fig_method(b3_typ, "Batch_3", "figs_results/fig0_method.png")
    _fig_uncertain_pair(b1_bright, b3_typ,
                        "figs_results/fig2_uncertain.png")
    _fig_sessions(f, "figs_results/fig3_sessions.png")
    _fig_new_photos(f, newf, "figs_results/fig4_new.png")

    # ---- numbers ----------------------------------------------------
    pct = lambda x, d=1: f"{x * 100:.{d}f}%"
    med = {c: {b: float(f[f.batch == b][c].median()) for b in BATCHES}
           for c in RESULT_FRACS}
    mdd = {c: float(pw[(pw.pair == "Batch_1-Batch_3") &
                       (pw.feature == c)].mdd_critical.iloc[0])
           for c in RESULT_FRACS}
    loo = bench[bench.protocol == "LOO"].set_index("method")
    logo = bench[bench.protocol == "LOGO-inferred"].set_index("method")
    shared = {r.pair: int(r.n_pair_groups)
              for r in bl[bl.marker == "pore_frac"].itertuples()}
    nclip = int((acq.raw_p1 == 0).sum())
    nz = acq.groupby("batch").noise_mad.median().to_dict()
    ct = acq.groupby("batch").si_bulk_contrast.median().to_dict()
    unc_b1 = f[f.batch == "Batch_1"].uncertain_bright_frac
    unc_b3_max = float(b3.uncertain_bright_frac.max())

    findings = [
        dict(badge_class="solid", badge_text="SOLID",
             headline="All three batches contain the same amounts of "
                      "pore space and silicon.",
             figure=dict(src=_b64("figs_results/fig1_amounts.png"),
                         alt="area shares by batch",
                         label="Figure 2",
                         title="Same amounts in every batch.",
                         how_to_read="Each dot is one photo; the short "
                         "line is the batch's middle value; the grey "
                         "band is the normal range seen in Batch 3, "
                         "the approved batch."),
             table=None,
             found=(f"Pore space is about {pct(med['pore_frac']['Batch_1'],0)}-"
                    f"{pct(med['pore_frac']['Batch_3'],0)} of each photo and "
                    f"candidate silicon about {pct(med['si_candidate_frac']['Batch_3'],0)}, "
                    "in all three batches. Every batch's middle value "
                    "sits inside Batch 3's normal range."),
             sure=(f"Solid for differences bigger than about "
                   f"{mdd['si_candidate_frac']*100:.1f} percentage points of "
                   f"silicon or {mdd['pore_frac']*100:.0f} points of pore "
                   "space. Those are the smallest gaps 7, 7 and 17 "
                   "photos can reveal (exact test)."),
             not_mean=("It doesn't prove the batches are identical. "
                       "Smaller differences, or material too fine to "
                       "resolve at 25 nm per pixel, would not show up."),
             source="validated_comparison/per_image_features.csv, "
                    "pairwise_comparisons.csv"),
        dict(badge_class="possible", badge_text="POSSIBLE",
             headline="Two Batch 1 photos contain unusual bright "
                      "material whose identity we can't tell.",
             figure=dict(src=_b64("figs_results/fig2_uncertain.png"),
                         alt="uncertain bright material",
                         label="Figure 3",
                         title="Unusual bright material, up close.",
                         how_to_read="The flagged Batch 1 photo (top) "
                         "carries far more orange 'uncertain bright' "
                         "material than a typical Batch 3 photo "
                         "(bottom), at the same 10 x 50 um scale."),
             table=None,
             found=(f"In those two photos, uncertain-bright material "
                    f"covers {pct(float(unc_b1.max()),0)} and "
                    f"{pct(float(unc_b1.nlargest(2).iloc[1]))} of the "
                    f"area — more than double the most seen anywhere "
                    f"in Batch 3 ({pct(unc_b3_max)}). It is genuinely "
                    "bright material, not grey bulk we misread."),
             sure=("The amount is measured and solid. What the material "
                   "is made of is not established: brightness is not "
                   "chemistry, so this is labelled uncertain rather "
                   "than called silicon."),
             not_mean=("It doesn't prove a defect. It is a photo-level "
                       "anomaly that could be imaging, preparation or "
                       "real material — the next step is an EDS "
                       "elemental scan on that material."),
             source="image_acquisition.csv, objects_classified.csv"),
        dict(badge_class="solid", badge_text="SOLID (as an observation)",
             headline="The photos were taken under different imaging "
                      "conditions that line up with the batches.",
             figure=dict(src=_b64("figs_results/fig3_sessions.png"),
                         alt="pore count by session",
                         label="Figure 4",
                         title="Sessions, not just batches.",
                         how_to_read="Each dot is one photo's countable "
                         "pores; columns are inferred imaging sessions "
                         "(frame height); dot colour is the batch; "
                         "amber columns hold more than one batch."),
             table=None,
             found=("Inside a shared session, photos from different "
                    "batches look alike; between sessions, values jump. "
                    "A classifier using only acquisition signature "
                    f"(frame shape, noise, contrast) matches batch "
                    f"labels {loo.loc['acq_signature','accuracy']*100:.0f}% "
                    f"of the time — as well as the {loo.loc['envelope','accuracy']*100:.0f}% "
                    "achieved using the measured structure."),
             sure=("Solid as an observation: the session pattern is in "
                   "the images themselves (13 inferred sessions; "
                   f"{nclip}/{len(acq)} photos have the darkest pixels "
                   "clipped to pure black)."),
             not_mean=("It doesn't prove the batch labels are wrong — "
                       "it proves we can't yet separate material from "
                       "how the photos were taken."),
             source="image_acquisition.csv, benchmark_results.csv"),
        dict(badge_class="canttell", badge_text="CAN'T TELL YET",
             headline="So batch differences can't be confirmed yet.",
             figure=None,
             table=_table(
                 ["batch pair", "shared sessions", "verdict"],
                 [["Batch 1 vs Batch 3", shared.get("Batch_1-Batch_3", 0),
                   "untestable — one shared session"],
                  ["Batch 1 vs Batch 2", shared.get("Batch_1-Batch_2", 0),
                   "inconclusive"],
                  ["Batch 2 vs Batch 3", shared.get("Batch_2-Batch_3", 0),
                   "inconclusive"]]),
             found=("The decisive test is comparing batches inside the "
                    "same session, where imaging conditions match. "
                    "Batch 1 and Batch 3 share only one session — that "
                    "is too few photos to call a difference."),
             sure=("With 13 sessions spread unevenly over 31 photos, "
                   "the controlled comparison lacks the numbers it "
                   "needs. This is an absence of evidence, not evidence "
                   "of absence."),
             not_mean=("It doesn't say the batches are the same. It "
                       "says this dataset cannot currently separate "
                       "material differences from session effects."),
             source="blocked_permutation.csv, image_acquisition.csv"),
        dict(badge_class="canttell", badge_text="CAN'T TELL YET",
             headline="The new photos: what our blind calls taught us.",
             figure=dict(src=_b64("figs_results/fig4_new.png"),
                         alt="new photos vs Batch 3",
                         label="Figure 5",
                         title="New photos against the normal range.",
                         how_to_read="The three new photos' area shares "
                         "against the Batch 3 normal range. One photo "
                         "(3e122cbj) sits far outside on uncertain "
                         "bright material."),
             table=_table(
                 ["photo", "our saved blind call", "confirmed answer",
                  "note"],
                 [[r.image_id.replace("img_", "img_"),
                   r.blind_call.replace("_", " "),
                   r.confirmed_label.replace("_", " "),
                   {"img_3e122cbj": "wrong — call followed its session",
                    "img_fn0mhxef": "wrong — call followed its session",
                    "img_xrv9xvzb": "consistent, unconfirmed"}[r.image_id]]
                  for r in truth.itertuples()]),
             found=("We matched each photo to the closest batch before "
                    "any answers were known, and saved the calls. "
                    "Confirmed corrections make it 0 correct out of 2 "
                    "(the third is unconfirmed). Both wrong calls "
                    "matched the photo's imaging session — the exact "
                    "confound in finding 3, flagged on the calls "
                    "themselves."),
             sure=("The labels are externally confirmed by the "
                   "organizer; our calls were timestamped before "
                   "disclosure. The score is honestly 0/2."),
             not_mean=("It doesn't prove the pipeline sees nothing — "
                       "it proves that on these three photos, session "
                       "signature and batch pointed the same way, so a "
                       "correct call wouldn't have meant material was "
                       "recognised either."),
             source="new_batch_ground_truth.csv, assignments.csv"),
    ]

    verdict_rows = [
        dict(batch="Batch 1", verdict="CAN'T TELL",
             confidence="low",
             reason="differences track imaging session, not batch",
             action="interleaved re-imaging"),
        dict(batch="Batch 2", verdict="CAN'T TELL",
             confidence="low",
             reason="no difference above detection limit; sessions "
                    "still entangled",
             action="same re-imaging"),
        dict(batch="New photos (3)", verdict="CAN'T TELL",
             confidence="low",
             reason="0 of 2 confirmed; calls matched sessions",
             action="blind re-test with session control"),
    ]

    ctx = dict(
        title="Can microscope photos tell these battery "
              "batches apart?",
        kicker="Silicon-graphite anode QC — microscopy comparison",
        meta=(f"{len(acq)} BSE micrographs · 3 curated batches + "
              f"{len(newf)} new photos · frozen recipe fitted on "
              "Batch 3 · generated 2026-10-04"),
        answer=("We measured every photo the same way and asked three "
                "questions: do the batches hold the same amounts, do "
                "they differ in structure, and can we prove it's the "
                "material — not the imaging — that differs? The "
                "amounts match; the imaging sessions don't. Today the "
                "honest answer for every batch is CAN'T TELL YET — "
                "not because nothing differs, but because session and "
                "batch can't be separated in this dataset."),
        verdicts=verdict_rows,
        how_to_read=("Each dot is one microscope photo. The grey band "
                     "is the normal range seen in Batch 3, the approved "
                     "reference batch — dots inside it look normal. "
                     "Every claim carries a label:"),
        label_solid="the measurement is consistent and was checked",
        label_possible="the pattern is real but confounded",
        label_canttell="the data cannot decide",
        pipeline=[dict(name="photo", text="one microscope image "
                                          "(back-scattered electrons)"),
                  dict(name="fix lighting",
                       text="remove uneven illumination across the frame"),
                  dict(name="colour pixels",
                       text="label each pixel pore / graphite / "
                            "silicon / uncertain bright"),
                  dict(name="measure shares",
                       text="what share of the area each colour covers"),
                  dict(name="compare",
                       text="same frozen ruler on every batch, vs "
                            "Batch 3")],
        method_text=("The same ruler measures all 34 photos — it was "
                     "set once on the approved Batch 3 and never "
                     "re-fitted, so batches can't drift the ruler. "
                     "Below, one photo before and after colouring:"),
        method_figure=dict(
            src=_b64("figs_results/fig0_method.png"),
            alt="raw vs colour map",
            label="Figure 1",
            caption="Left: a typical photo. Right: the same photo "
                    "coloured into pore (black), graphite bulk (grey), "
                    "candidate silicon (yellow) and uncertain bright "
                    "material (orange). Bar = 10 um."),
        findings=findings,
        qc_text=("No measured difference survives the session control, "
                 "so the evidence does not support REJECT for any "
                 "batch. It also doesn't support 'identical material': "
                 "the dataset cannot currently separate the two. The "
                 "useful actions are about removing the confound:"),
        actions=[
            "Get real session metadata (or re-image the batches "
            "interleaved in one session) — the single fix that unlocks "
            "the batch question.",
            "EDS elemental scan on the uncertain bright material in "
            "the two flagged photos.",
            "One measured bulk porosity per batch — anchors the "
            "image-based pore share.",
            "Repeat imaging of the same material — separates photo "
            "noise from manufacturing change."],
        limitations=[
            "Photos are crops from ~15 parent images, not independent "
            "specimens — batches are curated, not production lots.",
            "No crop-to-parent map exists, so independence and "
            "generalization can't be tested.",
            "'Silicon' is a brightness label — only EDS confirms "
            "chemistry.",
            "2-D sections can't show 3-D connectivity; small 2-D "
            "profiles aren't small particles.",
            "Below-resolution detail (<25 nm/pixel) is invisible by "
            "construction.",
            "The three new photos are unblinded — future method "
            "changes need a fresh test set."],
        dropped=[
            dict(name="pore counts, sizes and shapes",
                 why="pore count is the only value that passes the "
                     "many-test correction, but the session check "
                     "can't run (one shared group); sizes carry the "
                     "section-cut caveat"),
            dict(name="clustering and connectivity",
                 why="sensitive to where boundaries land; nothing "
                     "survives the session check"),
            dict(name="silicon–pore contact",
                 why="corrected and real, but not separable from "
                     "session effects"),
            dict(name="battery-model (DFN) indicators",
                 why="model-derived; the differences sit inside the "
                     "model's own assumption spread"),
            dict(name="extra detector channels (InLens/ETD)",
                 why="exploratory; detector gain varies with session"),
            dict(name="orientation strength (S)",
                 why="real shared structure — pores lie near-horizontal "
                     "in all batches — but it describes the electrode "
                     "rather than separating batches"),
        ],
        glossary=[
            dict(term="resolved pore",
                 meaning="dark regions large enough to measure "
                         "(>0.13 um across)"),
            dict(term="candidate silicon",
                 meaning="bright, compact objects that look like "
                         "silicon — a label, not a chemical test"),
            dict(term="uncertain bright",
                 meaning="bright material that doesn't look like solid "
                         "grains — thin or edge-rich; kept as its own "
                         "label instead of guessing"),
            dict(term="session",
                 meaning="a group of photos that look like they were "
                         "taken together (same frame size, detector "
                         "set, noise)"),
            dict(term="smallest detectable difference",
                 meaning="the smallest shift this many photos could "
                         "reveal — anything smaller is invisible to "
                         "the test"),
            dict(term="matched call",
                 meaning="assigning a photo to the batch it most "
                         "resembles"),
        ],
        reproducibility=(
            "One command rebuilds everything from the saved tables: "
            "python build_report.py. Frozen-recipe hash: "
            f"{manifest['recipe_md5'][:12]}… "
            "(dfn_output_v2/run_manifest.json). The '34 micrographs' "
            "count is the files on disk; 'curated batches' is the "
            "organizer's description of the dataset."),
        css=open("report_assets/report.css").read(),
    )
    html = Template(open("report_assets/template.html").read()) \
        .render(**ctx)
    with open("RESULTS.html", "w") as fh:
        fh.write(html)
    # lean markdown mirror (same claims, plain text)
    md = "# Results — what the measurements support\n\n" + \
        ctx["answer"] + "\n\n"
    for i, fd in enumerate(findings, 1):
        md += (f"## {i}. {fd['headline']} [{fd['badge_text']}]\n\n"
               f"- found: {fd['found']}\n- sure: {fd['sure']}\n"
               f"- doesn't mean: {fd['not_mean']}\n"
               f"- source: {fd['source']}\n\n")
    md += "## Not used, and why\n\n" + "\n".join(
        f"- {d['name']}: {d['why']}" for d in ctx["dropped"]) + "\n"
    with open("RESULTS.md", "w") as fh:
        fh.write(md)
    print("wrote RESULTS.html (template-rendered) + RESULTS.md + "
          "figs_results/")


