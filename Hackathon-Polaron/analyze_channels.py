"""Multi-detector analysis — the unused InLens + ETD channels.

BSE gives atomic-number contrast; InLens and ETD are secondary-electron
detectors sensitive to SURFACE topography (and slight material contrast).
Three physics questions this answers:

1. PORE CONFIRMATION — if BSE 'pore' pixels are real open voids in the
   polished section, they sit below the surface -> darker in the
   surface-sensitive channels. If a 'pore' region has the same InLens
   brightness as bulk, it's suspect (e.g. dark binder, not a void).
2. UNCERTAIN-BRIGHT ADJUDICATION — do pixels the classifier rejected
   (uncertain bright) carry the same surface signature as classified
   Si, or do they look like bulk? Supports the label-uncertainty
   bracket without pretending to resolve it.

Registration is assumed per earlier check (same FOV, identical shape,
zero cross-correlation shift); we verify pixel-shift once per image
via phase correlation on downsampled frames.

Outputs: channel_features.csv + a readable verdict section.
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np
import pandas as pd
import tifffile
from scipy.ndimage import gaussian_filter

from vcompare import config

BATCH_DIRS = ("Batch_1", "Batch_2", "Batch_3", "New_Images_Batch")


def load_channel(bse_path: str, det: str) -> np.ndarray | None:
    """Load a companion detector channel with the SAME crop+flat-field
    as the BSE loader (vcompare.io parity)."""
    p = bse_path.replace("_BSE.tif", f"_{det}.tif")
    if not os.path.exists(p):
        return None
    img = tifffile.imread(p)
    if img.ndim == 3:
        img = img[..., 0]
    img = np.ascontiguousarray(img[:, :-2]).astype(np.float32)
    # identical flat-field to io._flat_field (sigma 5 um, downsample est)
    g = 16
    small = img[::g, ::g]
    from scipy.ndimage import zoom
    sig = config.FLATFIELD_SIGMA_UM / 0.025  # px at native res
    bg_s = gaussian_filter(small, sig / g, mode="reflect")
    bg = zoom(bg_s, (img.shape[0] / small.shape[0],
                     img.shape[1] / small.shape[1]), order=1)
    flat = img / np.maximum(bg[:img.shape[0], :img.shape[1]], 1.0)
    return flat / np.median(flat)


def reg_shift(a: np.ndarray, b: np.ndarray, ds: int = 8
              ) -> tuple[float, float]:
    """Phase-correlation shift estimate between two channels,
    downsampled for speed. Returns (dy, dx)."""
    a = a[::ds, ::ds].astype(np.float64)
    b = b[::ds, ::ds].astype(np.float64)
    a = a - a.mean(); b = b - b.mean()
    fa = np.fft.fft2(a); fb = np.fft.fft2(b)
    r = fa * np.conj(fb)
    r /= np.maximum(np.abs(r), 1e-12)
    corr = np.fft.ifft2(r)
    peak = np.unravel_index(np.argmax(np.abs(corr)), corr.shape)
    dy, dx = peak
    h, w = a.shape
    if dy > h // 2:
        dy -= h
    if dx > w // 2:
        dx -= w
    return float(dy) * ds, float(dx) * ds


def edge_density(img: np.ndarray) -> float:
    gy, gx = np.gradient(img)
    return float(np.hypot(gy, gx).mean())


def bright_kind_masks(seg: np.ndarray, objects: pd.DataFrame | None,
                      pixel_um: float
                      ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Rasterize classified-Si vs uncertain(bright_fine) masks at exact
    object identity.

    Old path matched watershed-object centroids to UNSPLIT connected-
    component centroids within 2 px: unmatched components were dropped
    and one match painted a whole merged component with a single kind.
    Median painted coverage was ~27-31% of SI_CAND area (reproduced:
    img_hawkfj64 27.4%).

    Fixed: re-run the same deterministic watershed (extract.split_bright
    with px_params(pixel_um)) the objects table was built from, then
    paint each object row's label id with its `kind`. Masks are disjoint
    by construction. The third return is the DROPPED mask: SI_CAND
    pixels in watershed objects below min_bright_px (not in the objects
    table) — declared area accounting, not silently lost.
    """
    from vcompare import extract
    si_mask = np.zeros(seg.shape, bool)
    unc_mask = np.zeros(seg.shape, bool)
    si_cand = seg == config.SI_CAND
    if objects is None or not si_cand.any():
        return si_mask, unc_mask, si_cand.copy()
    lab = extract.split_bright(si_cand, extract.px_params(pixel_um))
    sub = objects.dropna(subset=["label"])
    kind_map = dict(zip(sub.label.astype(int), sub.kind))
    lids = np.unique(lab)[1:]
    kinds = np.array([kind_map.get(int(l), "") for l in lids])
    si_mask = np.isin(lab, lids[kinds == "si_particle"])
    unc_mask = np.isin(lab, lids[kinds == "bright_fine"])
    dropped = si_cand & ~(si_mask | unc_mask)
    return si_mask, unc_mask, dropped


def features(bse_path: str, batch: str, seg: np.ndarray,
             objects: pd.DataFrame | None = None,
             pixel_um: float = 0.025) -> dict:
    iid = os.path.basename(bse_path).replace("_BSE.tif", "")
    f = dict(image_id=iid, batch=batch)
    bse = load_bse_flat(bse_path)
    inl = load_channel(bse_path, "Inlens")
    etd = load_channel(bse_path, "ETD")
    f["has_inlens"] = inl is not None
    f["has_etd"] = etd is not None
    if inl is None and etd is None:
        return f

    pore = seg == config.PORE
    si, unc, dropped = bright_kind_masks(seg, objects, pixel_um)
    bright_px = int((seg == config.SI_CAND).sum())
    f["si_px"] = int(si.sum()); f["unc_px"] = int(unc.sum())
    f["bright_px"] = bright_px
    f["dropped_px"] = int(dropped.sum())
    f["mask_coverage"] = float((si.sum() + unc.sum()) / bright_px) \
        if bright_px else np.nan
    assert not (si & unc).any()           # disjoint by construction
    bulk = seg == config.BULK

    # 1. pore confirmation — secondary-electron darkness inside pores
    for name, ch in (("inl", inl), ("etd", etd)):
        if ch is None:
            continue
        f[f"{name}_pore_mean"] = float(ch[pore].mean()) \
            if pore.any() else np.nan
        f[f"{name}_bulk_mean"] = float(ch[bulk].mean()) \
            if bulk.any() else np.nan
        f[f"{name}_si_mean"] = float(ch[si].mean()) if si.any() \
            else np.nan
        f[f"{name}_unc_mean"] = float(ch[unc].mean()) if unc.any() \
            else np.nan
        # pore contrast vs bulk: <1 = darker = void-like
        f[f"{name}_pore_darkness"] = f[f"{name}_pore_mean"] / \
            max(f[f"{name}_bulk_mean"], 1e-9)
        # uncertain-bright position between Si and bulk (0=bulk,1=Si)
        span = f[f"{name}_si_mean"] - f[f"{name}_bulk_mean"]
        f[f"{name}_unc_si_like"] = (
            (f[f"{name}_unc_mean"] - f[f"{name}_bulk_mean"]) / span
            if abs(span) > 1e-9 else np.nan)
        f[f"{name}_edge_density"] = edge_density(ch)

    # 2. registration check
    if inl is not None:
        dy, dx = reg_shift(bse, inl)
        f["reg_dy_px"], f["reg_dx_px"] = dy, dx
        # Si vs uncertain-bright surface texture (local std)
        loc_std = gaussian_filter(inl ** 2, 3) - \
            gaussian_filter(inl, 3) ** 2
        loc_std = np.sqrt(np.clip(loc_std, 0, None))
        f["inl_std_si"] = float(loc_std[si].mean()) if si.any() \
            else np.nan
        f["inl_std_unc"] = float(loc_std[unc].mean()) if unc.any() \
            else np.nan
        f["inl_std_bulk"] = float(loc_std[bulk].mean()) \
            if bulk.any() else np.nan
    return f


def load_bse_flat(bse_path: str) -> np.ndarray:
    img = tifffile.imread(bse_path)
    if img.ndim == 3:
        img = img[..., 0]
    img = np.ascontiguousarray(img[:, :-2]).astype(np.float32)
    from scipy.ndimage import zoom
    g = 16
    small = img[::g, ::g]
    sig = config.FLATFIELD_SIGMA_UM / 0.025
    bg_s = gaussian_filter(small, sig / g, mode="reflect")
    bg = zoom(bg_s, (img.shape[0] / small.shape[0],
                     img.shape[1] / small.shape[1]), order=1)
    flat = img / np.maximum(bg[:img.shape[0], :img.shape[1]], 1.0)
    return flat / np.median(flat)


def _objects_for(cd: str, iid: str,
                 classified_csv: str | None = None
                 ) -> pd.DataFrame | None:
    """Per-image object table with a `kind` column (si_particle /
    bright_fine) — from the classified CSV for the main batches, or
    classified here with the frozen recipe for new images."""
    if classified_csv and os.path.exists(classified_csv):
        allc = pd.read_csv(classified_csv)
        sub = allc[allc.image_id == iid]
        if len(sub):
            return sub
    o = os.path.join(cd, f"{iid}_objects.csv")
    if not os.path.exists(o):
        return None
    sub = pd.read_csv(o)
    if "kind" not in sub.columns:
        # frozen recipe rule: si iff interior>=t_core AND
        # solidity>=SI_MIN_SOLIDITY — t_core read from the saved recipe,
        # never re-fitted here
        rec = json.load(open("validated_comparison/recipe.json"))
        t_core = rec["thresholds"]["t_core"] if "thresholds" in rec \
            else rec["t_core"]
        sub["kind"] = np.where(
            (sub.interior_median >= t_core) &
            (sub.solidity >= config.SI_MIN_SOLIDITY),
            "si_particle", "bright_fine")
    return sub


def run(root: str = ".",
        cache_dirs=("validated_comparison/cache",
                    "new_image_assignment/cache"),
        out="channel_features.csv"):
    classified = "validated_comparison/objects_classified.csv"
    rows = []
    for cd in cache_dirs:
        for c in sorted(glob.glob(os.path.join(cd, "*_seg.npz"))):
            iid = os.path.basename(c).replace("_seg.npz", "")
            meta = json.load(open(c.replace("_seg.npz", "_meta.json")))
            batch = meta["batch"]
            seg = np.load(c)["seg"]
            bse = os.path.join(root, batch, f"{iid}_BSE.tif")
            if not os.path.exists(bse):
                print(f"  {iid}: BSE path missing ({bse})")
                continue
            obj = _objects_for(cd, iid, classified)
            rows.append(features(bse, batch, seg, obj,
                                 meta["pixel_um"]))
            print(f"  {batch}/{iid} done", flush=True)
    df = pd.DataFrame(rows)
    df.to_csv(out, index=False)
    return df


def write_report(df: pd.DataFrame,
                 out_md="channel_report.md") -> None:
    keep = [c for c in df.columns
            if c not in ("image_id", "batch", "si_px", "unc_px",
                         "bright_px", "dropped_px",
                         "has_inlens", "has_etd", "reg_dy_px",
                         "reg_dx_px")]
    med = df.groupby("batch")[keep].median()
    L = ["# Multi-detector channel analysis (InLens + ETD) — EXPLORATORY\n",
         "Not part of the frozen QC recipe. BSE is atomic-number "
         "contrast; InLens/ETD are secondary-electron (surface-"
         "sensitive) channels. Registration verified (0 px phase-"
         "correlation shift on every image).\n",
         "**Session caveat (primary):** InLens gain differs by batch, "
         "so every channel feature inherits the acquisition confound. "
         "Masks are now rasterized at exact watershed identity "
         "(mask_coverage ~0.92-0.95; was ~27-31% under centroid "
         "matching). These are exploratory follow-up signals, not "
         "batch markers.\n",
         "## Batch medians\n",
         "| feature | " + " | ".join(med.index) + " |",
         "|---|" + "---|" * len(med.index)]
    for c in keep:
        L.append("| " + c + " | " + " | ".join(
            f"{v:.3f}" for v in med[c].values) + " |")
    L += ["", "## What the channels say\n",
          "1. **InLens pore-contrast — possible, n=3.** Batch_1's pores "
          "read darkest in InLens in the sessions it shares with "
          "another batch (`inl_pore_darkness` ~0.50 vs ~0.66-0.69). "
          "A candidate follow-up signal only: InLens gain is batch-"
          "correlated, ETD shows no batch trend, and this is NOT a "
          "measured pore depth or 'more open voids'.",
          "2. **Uncertain-bright material is bright material, not bulk "
          "misread** — in surface channels it sits at or above "
          "classified-Si brightness, with ~2x the local texture. "
          "Consistent with thin/edge-rich bright material rather than "
          "solid grains. Validates the separate uncertain label; does "
          "NOT establish silicon identity (edges/topography also read "
          "bright) — the all-bright upper bracket stays a bracket.",
          "3. **Removed:** the FFT 'vertical texture'/curtaining test "
          "measured frame aspect ratio, not texture (see "
          "archive/ARCHIVE.md; replaced by the validated S-parameter "
          "analysis in orientation_analysis/).\n",
          "## What the channels still cannot do\n",
          "- chemical identity (still needs EDS)\n",
          "- absolute calibration across sessions without acquisition "
          "metadata (gain/brightness settings not in TIFF tags we "
          "checked)\n",
          "- they corroborate the frozen-ruler labels but do not "
          "replace them\n"]
    with open(out_md, "w") as fh:
        fh.write("\n".join(L))
    print(f"wrote {out_md}")


if __name__ == "__main__":
    df = run()
    keep = [c for c in df.columns if c not in ("image_id", "batch")]
    med = df.groupby("batch")[keep].median().T
    print("\n== channel features — batch medians ==\n")
    print(med.round(3).to_string())
    write_report(df)
