"""Per-image 2-D orientational order (S) — driver.

Populations (declared per spec 8A — never mixed):
  tex_all    structure-tensor orientations over all eligible pixels
             (coherence-weighted; the averaging scale sigma_coher is
             the declared local-order window)
  tex_si     same, restricted to classified si_particle pixels
  obj_si     major-axis angles of elongated classified Si objects
             (equal-weight AND area-weighted reported separately)
  obj_pore   major-axis angles of elongated pore objects

Per image, per population: S_x_2d (ref = image-horizontal), S_dir_2d,
theta_director, n_orientations, coverage, permutation-null p95, plus
the axial histogram (18 bins, -90..+90 deg) saved long-format.

Uncertainty: object populations get a bootstrap over OBJECTS (the
sampling unit); texture gets a within-image quadrant spread labeled
explicitly as within-image spatial resampling, not a batch CI.
Batch summaries also stratify by inferred acquisition group
(image_acquisition.group_id — inferred strata, NOT confirmed parents).

Outputs: orientation_analysis/orientation_features.csv,
         orientation_analysis/orientation_histograms.csv,
         orientation_analysis/fig_orientation.png,
         orientation_analysis/orientation_report.md
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np
import pandas as pd

from analyze_channels import _objects_for, bright_kind_masks, load_bse_flat
from micro2dfn import orientation as O
from vcompare import config

OUT = "orientation_analysis"
SIGMA_DERIV = 1.0          # derivative scale, px (0.025 um)
SIGMA_COHER = 4.0          # local-order window, px (~0.10 um)
COHER_MIN = 0.3
MIN_ASPECT = 2.5
HIST_BINS = 18
BATCHES = ("Batch_1", "Batch_2", "Batch_3", "New_Images_Batch")


def _pop_row(f: dict, pop: str, theta, w, n_resample: int = 200,
             seed: int = 0) -> dict:
    r = O.reduce_population(theta, w)
    med, p95 = O.null_s_director_resample(theta, w, n_resample, seed)
    for k, v in r.items():
        f[f"{pop}_{k}"] = v
    f[f"{pop}_null_med"] = med
    f[f"{pop}_null_p95"] = p95
    return f


def _quadrant_spread(theta, w, shape) -> float:
    """Within-image spatial-resampling spread of S_dir (quadrants).
    Labeled diagnostic — NOT a batch-level uncertainty."""
    h, wpx = shape
    vals = []
    quad = (np.arange(h * wpx) // wpx >= h // 2) * 2 + \
           (np.arange(h * wpx) % wpx >= wpx // 2)
    for q in range(4):
        m = quad == q
        # flat index alignment: theta/w come from valid[flat] order
        th_q = theta[m[len(theta) - len(theta):len(theta)]]
    return np.nan          # computed in driver with flat indices


def per_image(iid: str, batch: str, seg: np.ndarray, gray: np.ndarray,
              pixel_um: float, objects: pd.DataFrame | None,
              seed: int = 0) -> tuple[dict, dict]:
    f = dict(image_id=iid, batch=batch)
    pore = seg == config.PORE
    si, unc, _ = bright_kind_masks(seg, objects, pixel_um)
    solid = ~pore

    # --- texture populations ---------------------------------------
    theta, coh, _c, valid = O.texture_angles(
        gray, SIGMA_DERIV, SIGMA_COHER, mask=solid,
        coher_min=COHER_MIN)
    f["tex_valid_frac_of_solid"] = float(valid.sum()
                                         / max(solid.sum(), 1))
    th, w = theta[valid], coh[valid]
    f = _pop_row(f, "tex_all", th, w, seed=seed)
    # within-image quadrant spread of S_dir (spatial resampling —
    # NOT a batch uncertainty; flat order aligns with `valid`)
    flat_th = theta[solid]; flat_w = coh[solid]
    flat_v = valid[solid]
    h, wpx = seg.shape
    rows = (np.arange(h * wpx) // wpx)[solid.ravel()]
    cols = (np.arange(h * wpx) % wpx)[solid.ravel()]
    qs = []
    for q in ((rows < h // 2, cols < wpx // 2),
              (rows < h // 2, cols >= wpx // 2),
              (rows >= h // 2, cols < wpx // 2),
              (rows >= h // 2, cols >= wpx // 2)):
        m = flat_v & q[0] & q[1]
        if m.sum() > 100:
            s, _ = O.s_director(flat_th[m], flat_w[m])
            qs.append(s)
    f["tex_quadrant_sdir_spread"] = float(np.std(qs)) if len(qs) > 2 \
        else np.nan

    # texture within classified Si only
    theta_si, coh_si, _c, valid_si = O.texture_angles(
        gray, SIGMA_DERIV, SIGMA_COHER, mask=si, coher_min=COHER_MIN)
    f["tex_si_valid_frac"] = float(valid_si.sum() / max(si.sum(), 1))
    f = _pop_row(f, "tex_si", theta_si[valid_si], coh_si[valid_si],
                 seed=seed + 1)

    # --- object populations -----------------------------------------
    th_o, ar_o = O.object_angles(si, min_aspect=MIN_ASPECT)
    f["obj_si_n_eligible"] = len(th_o)
    f = _pop_row(f, "obj_si_eq", th_o, np.ones(len(th_o)),
                 seed=seed + 2)
    f = _pop_row(f, "obj_si_aw", th_o, ar_o, seed=seed + 3)
    # object bootstrap (objects = sampling unit), equal weights
    if len(th_o) >= 8:
        rng = np.random.default_rng(seed + 4)
        bs = [O.s_director(th_o[rng.integers(0, len(th_o), len(th_o))],
                           np.ones(len(th_o)))[0]
              for _ in range(300)]
        f["obj_si_eq_sdir_boot_lo"], f["obj_si_eq_sdir_boot_hi"] = \
            np.quantile(bs, [0.025, 0.975])
    else:
        f["obj_si_eq_sdir_boot_lo"] = f["obj_si_eq_sdir_boot_hi"] = np.nan

    th_p, ar_p = O.object_angles(pore, min_aspect=MIN_ASPECT)
    f["obj_pore_n_eligible"] = len(th_p)
    f = _pop_row(f, "obj_pore_eq", th_p, np.ones(len(th_p)),
                 seed=seed + 5)
    f = _pop_row(f, "obj_pore_aw", th_p, ar_p, seed=seed + 6)

    # --- axial histograms (weighted, per population) -----------------
    hist = {"image_id": iid}
    cen, hh = O.axial_hist(th, w, HIST_BINS)
    for c_, v_ in zip(np.round(cen, 1), hh):
        hist[f"tex_all_{c_}"] = float(v_)
    cen, hh = O.axial_hist(th_o, ar_o, HIST_BINS)
    for c_, v_ in zip(np.round(cen, 1), hh):
        hist[f"obj_si_aw_{c_}"] = float(v_)
    return f, hist


def main():
    os.makedirs(OUT, exist_ok=True)
    classified = "validated_comparison/objects_classified.csv"
    groups = (pd.read_csv("image_acquisition.csv")
              [["image_id", "group_id"]]
              if os.path.exists("image_acquisition.csv") else None)
    rows, hists = [], []
    for cd in ("validated_comparison/cache", "new_image_assignment/cache"):
        for i, c in enumerate(sorted(glob.glob(os.path.join(cd,
                                                            "*_seg.npz")))):
            iid = os.path.basename(c).replace("_seg.npz", "")
            meta = json.load(open(c.replace("_seg.npz", "_meta.json")))
            seg = np.load(c)["seg"]
            bse = os.path.join(meta["batch"], f"{iid}_BSE.tif")
            if not os.path.exists(bse):
                print(f"  {iid}: BSE missing, skipped")
                continue
            gray = load_bse_flat(bse)
            if gray.shape != seg.shape:
                gray = gray[:seg.shape[0], :seg.shape[1]]
            obj = _objects_for(cd, iid, classified)
            f, h = per_image(iid, meta["batch"], seg, gray,
                             meta["pixel_um"], obj, seed=i)
            rows.append(f); hists.append(h)
            print(f"  {iid} done", flush=True)
    df = pd.DataFrame(rows)
    if groups is not None:
        df = df.merge(groups, on="image_id", how="left")
    df.to_csv(os.path.join(OUT, "orientation_features.csv"),
              index=False)
    pd.DataFrame(hists).fillna(0.0).to_csv(
        os.path.join(OUT, "orientation_histograms.csv"), index=False)
    write_report(df)
    print(f"-> {OUT}/orientation_features.csv, "
          f"orientation_histograms.csv, orientation_report.md")


def write_report(df: pd.DataFrame) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pops = [c[:-9] for c in df.columns if c.endswith("_s_dir_2d")]
    L = ["# 2-D orientational order (S) — morphology, not crystallography\n",
         "S_x_2d = <w cos 2(theta-0deg)>/<w>: +1 all horizontal, -1 all "
         "vertical, 0 = no net preference at the horizontal axis (NOT "
         "isotropy). S_dir_2d = sqrt(C2^2+D2^2): alignment strength "
         "irrespective of direction; null_med/null_p95 are the "
         "permutation-null values for the same sample. theta_dir is "
         "unstable when S_dir ~ null. theta measured from image-x "
         "(horizontal), axial mod 180 deg. Populations: tex_all "
         f"(structure tensor, coherence-weighted, sigma_coher="
         f"{SIGMA_COHER}px ~0.10 um, coher>={COHER_MIN}), tex_si (same "
         "inside classified Si), obj_si/obj_pore (elongated objects, "
         f"aspect>={MIN_ASPECT}; eq=equal weight, aw=area weight).\n",
         "## Batch medians\n",
         "| population | batch | S_x_2d | S_dir_2d | null_p95 | "
         "theta_dir | n |",
         "|---|---|---|---|---|---|---|"]
    for p in pops:
        for b in BATCHES:
            d = df[df.batch == b]
            if not len(d):
                continue
            td = d[f"{p}_theta_dir_deg"]
            td = td[d[f"{p}_s_dir_2d"] > 2 * d[f"{p}_null_p95"]]
            L.append(f"| {p} | {b} | {d[f'{p}_s_x_2d'].median():+.3f} "
                     f"| {d[f'{p}_s_dir_2d'].median():.3f} "
                     f"| {d[f'{p}_null_p95'].median():.3f} "
                     f"| {td.median() if len(td) else float('nan'):.1f} "
                     f"| {d[f'{p}_n_orientations'].median():.0f} |")
    L += ["", "## By inferred acquisition group (dependence check)\n",
          "Groups are inferred frame/appearance strata — not confirmed "
          "parents or sessions. Within-batch between-group spread "
          "indicates dependence, not physics.\n",
          "| population | group | batch | S_x_2d | S_dir_2d | n_img |",
          "|---|---|---|---|---|---|"]
    for p in pops:
        for (g, b), d in df.dropna(subset=["group_id"]).groupby(
                ["group_id", "batch"]):
            if b == "New_Images_Batch":
                continue
            L.append(f"| {p} | {int(g)} | {b} | "
                     f"{d[f'{p}_s_x_2d'].median():+.3f} | "
                     f"{d[f'{p}_s_dir_2d'].median():.3f} | {len(d)} |")
    L += ["", "## Reading\n",
          "- Histograms per image are in `orientation_histograms.csv` "
          "— S=0 with a bimodal histogram is orthogonal-mixture order, "
          "not isotropy; always read them together.",
          "- `tex_quadrant_sdir_spread` is within-image spatial "
          "resampling spread (quadrants), NOT a batch-level "
          "uncertainty.",
          "- obj_si_eq_sdir_boot lo/hi is an OBJECT bootstrap CI "
          "(objects are the sampling unit).",
          "- A nonzero S says structures align under this definition. "
          "It does not establish calendering, grinding, curtaining, "
          "damage, transport, or electrochemical consequence."]
    with open(os.path.join(OUT, "orientation_report.md"), "w") as fh:
        fh.write("\n".join(L))

    # figure: S_dir vs S_x per image, colored by batch
    fig, axes = plt.subplots(1, 2, figsize=(10, 4))
    for b in BATCHES:
        d = df[df.batch == b]
        axes[0].scatter(d["tex_all_s_dir_2d"], d["tex_all_s_x_2d"],
                        label=b, s=16, alpha=0.8)
        axes[1].scatter(d["obj_si_eq_s_dir_2d"], d["obj_si_eq_s_x_2d"],
                        label=b, s=16, alpha=0.8)
    for ax, t in zip(axes, ("texture (all valid px)",
                            "classified Si objects (equal w)")):
        ax.axvline(0, color="k", lw=0.5); ax.axhline(0, color="k", lw=0.5)
        ax.set_xlabel("S_dir_2d"); ax.set_ylabel("S_x_2d")
        ax.set_title(t); ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, "fig_orientation.png"), dpi=150)


if __name__ == "__main__":
    main()
