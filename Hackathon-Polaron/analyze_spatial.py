"""Spatial heterogeneity analysis — the defect-risk signals.

Per image, from the cached 4-class segmentations (frozen recipe), for
TWO bright populations separately (the label semantics fix):

  bright_*  ALL thresholded bright material (seg == SI_CAND):
            classified si_particle + uncertain bright_fine together.
  si_*      CLASSIFIED si_particle objects only, rasterized at exact
            watershed identity (same split the objects table used).
  unc_share_of_bright  uncertain-bright share of bright area —
            the abstention category's footprint, not a chemistry.

Metrics per population:
  *_hotspot_ratio   max/median density over a 6x6 patch grid
  *_maxpatch_frac   share of image where the densest patch sits
  *_topbot_ratio    fraction top band / bottom band (frame
                    gradient — foil not in frame; 'top'/'bottom'
                    are conventions; physical axis unconfirmed)
  *_depth_slope     linear slope of band fractions
  *_lr_asym         |left-right| fraction asymmetry
  largest_si_cluster_frac  largest connected region / total Si area
                    (classified population; agglomerate score)
  cracklike_frac    pore area share in objects with aspect>4 AND
                    major axis within 30 deg of the frame-ROW axis
                    (frame-vertical). skimage regionprops.orientation
                    is measured FROM the row axis: 0 deg = vertically
                    elongated, +/-90 deg = horizontally elongated.
                    (Bug fix 2026-10: the old `abs(deg)>60` test
                    selected near-HORIZONTAL objects while calling
                    them vertical.)
  si_near_pore_frac Si fraction within ~0.15 um of a pore

DIAGNOSTIC/EXPLORATORY layer only — boundary-sensitive, and none
survive within-session blocking (see marker_session_partition.csv).

Outputs: spatial_features_v2.csv + fig_spatial.png + spatial_report.md
(v2: orientation-convention fix + bright/classified split; the v1
values in historical reports measured all-bright with a reversed
orientation selector).
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np
import pandas as pd
from scipy.ndimage import binary_dilation, label as ndi_label
from skimage.measure import regionprops

from analyze_channels import _objects_for, bright_kind_masks
from vcompare import config

BANDS = 6
GRID = 6
NEAR_PORE_UM = 0.15
VERTICAL_HALF_ANGLE_DEG = 30.0


def band_frac(mask: np.ndarray) -> np.ndarray:
    h = mask.shape[0]
    edges = np.linspace(0, h, BANDS + 1).astype(int)
    return np.array([mask[edges[i]:edges[i + 1]].mean()
                     for i in range(BANDS)])


def grid_stats(mask: np.ndarray, n: int = GRID) -> tuple[float, float]:
    """(max patch frac / median patch frac, densest patch frac)."""
    h, w = mask.shape
    fr = []
    for i in range(n):
        for j in range(n):
            fr.append(mask[i * h // n:(i + 1) * h // n,
                           j * w // n:(j + 1) * w // n].mean())
    fr = np.asarray(fr)
    med = np.median(fr)
    return float(fr.max() / max(med, 1e-9)), float(fr.max())


def _population(mask: np.ndarray, prefix: str, f: dict) -> None:
    """The shared spatial-metric set for one binary population."""
    sb = band_frac(mask)
    f[f"{prefix}_topbot_ratio"] = float(sb[0] / max(sb[-1], 1e-9))
    f[f"{prefix}_depth_slope"] = float(np.polyfit(np.arange(BANDS),
                                                  sb, 1)[0])
    hot, maxp = grid_stats(mask)
    f[f"{prefix}_hotspot_ratio"] = hot
    f[f"{prefix}_maxpatch_frac"] = maxp
    h, w = mask.shape
    f[f"{prefix}_lr_asym"] = float(abs(mask[:, :w // 2].mean()
                                       - mask[:, w // 2:].mean()))


def spatial_features(image_id: str, seg: np.ndarray, pixel_um: float,
                     batch: str,
                     objects: pd.DataFrame | None = None) -> dict:
    bright = seg == config.SI_CAND
    pore = seg == config.PORE
    f = dict(image_id=image_id, batch=batch)

    # ---- all-bright population (segmented SI_CAND, pre-classification)
    _population(bright, "bright", f)
    pb = band_frac(pore)
    f["pore_topbot_ratio"] = float(pb[0] / max(pb[-1], 1e-9))
    f["pore_depth_slope"] = float(np.polyfit(np.arange(BANDS), pb, 1)[0])
    f["pore_hotspot_ratio"], _ = grid_stats(pore)

    # ---- classified populations at exact watershed identity ---------
    si, unc, _dropped = bright_kind_masks(seg, objects, pixel_um)
    f["unc_share_of_bright"] = float(unc.sum() / max(bright.sum(), 1))
    _population(si, "si", f)

    # largest connected Si agglomerate (classified population, raw
    # mask connectivity — the 'one continuous cluster' score)
    lab, n = ndi_label(si)
    f["largest_si_cluster_frac"] = float(
        np.bincount(lab.ravel())[1:].max() / max(si.sum(), 1)) \
        if n else 0.0

    # crack-like pores: elongated (aspect>4) AND major axis within
    # 30 deg of the frame-ROW axis. skimage orientation is measured
    # FROM the row axis -> near-vertical objects have |deg| < 30.
    plab, _np = ndi_label(pore)
    crack = np.zeros_like(pore)
    for r in regionprops(plab):
        if r.area < 20:
            continue
        asp = r.axis_major_length / max(r.axis_minor_length, 1e-9)
        if asp > 4 and abs(np.degrees(r.orientation)) \
                < VERTICAL_HALF_ANGLE_DEG:
            crack[tuple(r.coords.T)] = True
    f["cracklike_frac"] = float(crack.sum() / max(pore.sum(), 1))

    # Si within ~0.15 um of a pore (classified population)
    d = max(1, round(NEAR_PORE_UM / pixel_um))
    near = binary_dilation(pore, iterations=d)
    f["si_near_pore_frac"] = float((si & near).sum() / max(si.sum(), 1))
    return f


def run(cache_dirs=("validated_comparison/cache",
                    "new_image_assignment/cache"),
        out="spatial_features_v2.csv"):
    classified = "validated_comparison/objects_classified.csv"
    rows = []
    for cd in cache_dirs:
        for c in sorted(glob.glob(os.path.join(cd, "*_seg.npz"))):
            iid = os.path.basename(c).replace("_seg.npz", "")
            meta = json.load(open(c.replace("_seg.npz", "_meta.json")))
            seg = np.load(c)["seg"]
            obj = _objects_for(cd, iid, classified)
            rows.append(spatial_features(iid, seg, meta["pixel_um"],
                                         meta["batch"], obj))
            print(f"  {iid} done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    return df


def report(df: pd.DataFrame, out_md="spatial_report.md",
           out_fig="fig_spatial.png"):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    cols = [c for c in df.columns if c not in ("image_id", "batch")]
    L = ["# Spatial heterogeneity — the defect-risk signals\n",
         "All values from the frozen vcompare recipe — "
         "**diagnostic/exploratory layer**: these markers depend on "
         "where object boundaries land and none survive acquisition "
         "blocking, so they are not batch markers (see "
         "`marker_session_partition.csv`). `top`/`bottom` are frame "
         "edges; the foil is not in frame and the "
         "direction-to-physical-axis mapping is unconfirmed (the "
         "earlier FFT-based orientation claim was withdrawn — see "
         "`archive/ARCHIVE.md`).\n",
         "Two bright populations are reported separately (v2): "
         "`bright_*` = ALL segmented bright material; `si_*` = "
         "classified si_particle objects only, rasterized at exact "
         "watershed identity. `cracklike_frac` now tests the skimage "
         "row-axis convention correctly (within 30 deg of "
         "frame-vertical — the v1 test selected near-horizontal "
         "objects while calling them vertical). "
         "Batch medians [min-max]:\n",
         "| signal | Batch_1 | Batch_2 | Batch_3 | New |",
         "|---|---|---|---|---|"]
    med = {}
    for c in cols:
        line = [f"| {c} |"]
        for b in ("Batch_1", "Batch_2", "Batch_3", "New_Images_Batch"):
            v = df[df.batch == b][c]
            med.setdefault(b, {})[c] = v.median()
            line.append(f"{v.median():.3f} [{v.min():.3f},"
                        f"{v.max():.3f}] |" if len(v) else "n/a |")
        L.append(" ".join(line))
    L.append("\n## Reading the signals\n")
    L.append("- `*_hotspot_ratio` high = one patch carries much more "
             "of that phase than typical -> uneven loading, local "
             "swelling stress. `bright_*` includes uncertain material; "
             "`si_*` is the classified population.")
    L.append("- `largest_si_cluster_frac` = share of classified Si "
             "that is ONE connected region — the 'enormous continuous "
             "cluster' case.")
    L.append("- `*_topbot_ratio` != 1 = phase segregated top-to-bottom "
             "in the frame (drying/calendering hypothesis only — "
             "physical direction unconfirmed).")
    L.append("- `cracklike_frac` = share of pore area in thin objects "
             "whose major axis sits within 30 deg of frame-vertical — "
             "crack-like rather than round voids. Caveat: streaking "
             "can also be a sectioning artefact, it is "
             "session-sensitive, and the earlier version of this "
             "metric measured the perpendicular population.")
    L.append("- `si_near_pore_frac` = classified Si within 0.15 µm of "
             "a resolved pore in this 2-D slice — a measured blind "
             "spot (sub-resolution pores dominate real porosity), "
             "not a batch marker.")
    L.append("- `unc_share_of_bright` = uncertain-bright share of the "
             "bright area — the abstention category's footprint.")

    fig, axes = plt.subplots(1, 3, figsize=(12, 3.4))
    for ax, c, t in zip(axes,
                        ("si_hotspot_ratio", "si_topbot_ratio",
                         "cracklike_frac"),
                        ("Si hotspot ratio (max/med patch)",
                         "Si top/bottom depth ratio",
                         "Crack-like pore share (frame-vertical)")):
        for i, b in enumerate(("Batch_1", "Batch_2", "Batch_3",
                               "New_Images_Batch")):
            v = df[df.batch == b][c].dropna()
            ax.boxplot([v], positions=[i], widths=0.5,
                       showfliers=False)
            ax.scatter(np.full(len(v), i) +
                       np.linspace(-0.1, 0.1, len(v)), v,
                       s=10, alpha=0.7)
            ax.set_xticks(range(4), ["B1", "B2", "B3", "new"])
            ax.set_title(t, fontsize=9)
    fig.tight_layout()
    fig.savefig(out_fig, dpi=150)
    with open(out_md, "w") as fh:
        fh.write("\n".join(L))
    return out_md, out_fig


if __name__ == "__main__":
    df = run()
    print("\nbatch medians:")
    print(df.groupby("batch").median(numeric_only=True).round(3)
          .to_string())
    report(df)
    print("-> spatial_report.md, fig_spatial.png")
