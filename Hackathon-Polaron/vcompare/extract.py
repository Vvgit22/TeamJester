"""Per-image extraction at native resolution under a frozen recipe.

Produces, per image:
  * a 4-class label map  (pore / bulk / si_candidate / uncertain_bright)
  * one row of pixel-level features + imaging diagnostics
  * an objects table (watershed-split bright objects, unclassified)

Classification is applied post-hoc from the recipe's `t_core`, so cached
extractions survive recipe re-fits and scenario reclassifications.
"""
from __future__ import annotations

import hashlib
import json
import os

import numpy as np
import pandas as pd
import tifffile
from scipy import spatial
from scipy.ndimage import (binary_erosion, distance_transform_edt,
                           gaussian_filter, zoom)
from skimage.feature import peak_local_max
from skimage.filters import threshold_multiotsu
from skimage.measure import label, regionprops
from skimage.segmentation import watershed

from . import config


# ---------------------------------------------------------------------------
# loading / preprocessing
# ---------------------------------------------------------------------------
def _pixel_size_um(path: str) -> float:
    try:
        with tifffile.TiffFile(path) as t:
            tags = t.pages[0].tags
            if "XResolution" in tags and "ResolutionUnit" in tags:
                num, den = tags["XResolution"].value
                unit = tags["ResolutionUnit"].value
                if unit == 2:
                    return 25_400.0 / (num / den)
                if unit == 3:
                    return 10_000.0 / (num / den)
    except Exception:
        pass
    return config.PIXEL_NM_FALLBACK / 1000.0


def _flat_field(raw: np.ndarray, sigma_um: float, pixel_um: float
                ) -> np.ndarray:
    g = 16
    sigma_px = sigma_um / pixel_um
    small = raw[::g, ::g]
    bg_s = gaussian_filter(small, sigma_px / g, mode="reflect")
    bg = zoom(bg_s, (raw.shape[0] / small.shape[0],
                     raw.shape[1] / small.shape[1]), order=1)
    bg = bg[:raw.shape[0], :raw.shape[1]]
    flat = raw / np.maximum(bg, 1.0)
    return flat / np.median(flat)


class Image:
    def __init__(self, path: str, batch: str, downsample: int = 1):
        img = tifffile.imread(path)
        if img.ndim == 3:
            img = img[..., 0]
        img = np.ascontiguousarray(img[:, :-2])
        if downsample > 1:
            img = img[::downsample, ::downsample]
        self.raw = img.astype(np.float32)
        self.native_pixel_um = _pixel_size_um(path)
        self.pixel_um = self.native_pixel_um * downsample
        self.gray = _flat_field(self.raw, config.FLATFIELD_SIGMA_UM,
                                self.pixel_um)
        self.image_id = os.path.basename(path).replace("_BSE.tif", "")
        self.batch = batch
        self.path = path
        self.channels = {d: path.replace("_BSE.tif", f"_{d}.tif")
                         for d in ("Inlens", "ETD", "SE")
                         if os.path.exists(
                             path.replace("_BSE.tif", f"_{d}.tif"))}


def px_params(pixel_um: float) -> dict:
    """Convert the physical-unit recipe to pixel units for one image."""
    return dict(
        smooth_sigma_px=config.SEG_SMOOTH_SIGMA_UM / pixel_um,
        min_bright_px=max(1, round(config.MIN_BRIGHT_AREA_UM2
                                   / pixel_um ** 2)),
        min_pore_px=max(1, round(config.MIN_PORE_AREA_UM2
                                 / pixel_um ** 2)),
        erode_px=max(1, round(config.OBJECT_ERODE_UM / pixel_um)),
        contact_px=max(1, round(config.CONTACT_DILATION_UM / pixel_um)),
        watershed_min_dist_px=max(1, round(config.WATERSHED_MIN_DIST_UM
                                           / pixel_um)),
    )


def file_md5(path: str) -> str:
    h = hashlib.md5()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


# ---------------------------------------------------------------------------
# segmentation + objects
# ---------------------------------------------------------------------------
def fit_thresholds(grays: list[np.ndarray], pixel_ums: list[float],
                   seed: int = 0) -> tuple[float, float]:
    """Pooled multi-Otsu on a list of flat-fielded images (the reference
    batch for the frozen recipe; all images for the QC reproduction)."""
    rng = np.random.default_rng(seed)
    per = max(10_000, config.SEG_SUBSAMPLE // max(1, len(grays)))
    samples = []
    for gray, px in zip(grays, pixel_ums):
        sm = gaussian_filter(gray, config.SEG_SMOOTH_SIGMA_UM / px)
        flat = sm.ravel()
        samples.append(flat[rng.choice(flat.size, min(per, flat.size),
                                       replace=False)])
    t1, t2 = threshold_multiotsu(np.concatenate(samples), classes=3,
                                 nbins=256)
    return float(t1), float(t2)


def segment(gray: np.ndarray, t_pore: float, t_si: float,
            px: dict) -> np.ndarray:
    sm = gaussian_filter(gray, px["smooth_sigma_px"])
    seg = np.ones(sm.shape, np.uint8) * config.BULK
    seg[sm < t_pore] = config.PORE
    seg[sm >= t_si] = config.SI_CAND
    for phase, key in ((config.SI_CAND, "min_bright_px"),
                       (config.PORE, "min_pore_px")):
        lab = label(seg == phase)
        counts = np.bincount(lab.ravel())
        drop = np.where(counts < px[key])[0]
        drop = drop[drop != 0]
        if len(drop):
            seg[np.isin(lab, drop)] = config.BULK
    return seg


def split_bright(si_mask: np.ndarray, px: dict) -> np.ndarray:
    dist = distance_transform_edt(si_mask)
    coords = peak_local_max(dist, min_distance=px["watershed_min_dist_px"],
                            labels=si_mask)
    markers = np.zeros(si_mask.shape, np.int32)
    markers[tuple(coords.T)] = np.arange(1, len(coords) + 1)
    if len(coords) == 0:
        return label(si_mask)
    return watershed(-dist, markers, mask=si_mask)


def extract_objects(gray: np.ndarray, si_mask: np.ndarray, pixel_um: float,
                    px: dict, image_id: str, batch: str) -> pd.DataFrame:
    lab = split_bright(si_mask, px)
    border = np.zeros(si_mask.shape, bool)
    border[[0, -1], :] = True
    border[:, [0, -1]] = True
    rows = []
    for r in regionprops(lab):
        if r.area < px["min_bright_px"]:
            continue
        # erode within the object bbox only (full-image erosion per object
        # is O(n_objects * n_px) — the dominant cost otherwise)
        sl = r.slice
        eroded = binary_erosion(lab[sl] == r.label,
                                iterations=px["erode_px"])
        interior = gray[sl][eroded] if eroded.any() \
            else gray[tuple(r.coords.T)]
        rows.append(dict(
            image_id=image_id, batch=batch, label=int(r.label),
            area_px=int(r.area), area_um2=float(r.area * pixel_um ** 2),
            eq_diam_um=float(np.sqrt(4 * r.area / np.pi) * pixel_um),
            interior_median=float(np.median(interior)),
            interior_std=float(interior.std()),
            solidity=float(r.solidity),
            aspect=float(r.axis_major_length
                         / max(r.axis_minor_length, 1e-9)),
            touches_border=bool(border[tuple(r.coords.T)].any()),
            centroid_y_um=float(r.centroid[0] * pixel_um),
            centroid_x_um=float(r.centroid[1] * pixel_um)))
    return pd.DataFrame(rows), lab


def calibrate_t_core(objects: pd.DataFrame) -> float:
    calib = objects[(objects["eq_diam_um"] >= config.SI_CALIB_MIN_DIAM_UM)
                    & (objects["solidity"] >= config.SI_CALIB_MIN_SOLIDITY)]
    if len(calib) < 20:
        return float(np.percentile(objects["interior_median"], 25))
    return float(np.percentile(calib["interior_median"],
                               config.SI_CORE_PERCENTILE))


def classify(objects: pd.DataFrame, t_core: float) -> pd.Series:
    return pd.Series(np.where(
        (objects["interior_median"] >= t_core)
        & (objects["solidity"] >= config.SI_MIN_SOLIDITY),
        "si_particle", "bright_fine"), index=objects.index, name="kind")


# ---------------------------------------------------------------------------
# feature extraction
# ---------------------------------------------------------------------------
def _chord_lengths(mask: np.ndarray, axis: int) -> np.ndarray:
    lens = []
    for line in (mask if axis == 1 else mask.T):
        d = np.diff(np.concatenate([[0], line.view(np.int8), [0]]))
        starts = np.where(d == 1)[0]
        lens.extend(np.where(d == -1)[0] - starts)
    return np.asarray(lens)


def _weighted_quantile(values, weights, q):
    order = np.argsort(values)
    v, w = values[order], weights[order]
    cw = (np.cumsum(w) - 0.5 * w) / np.sum(w)
    return float(np.interp(q, cw, v))


def pixel_features(im: Image, seg: np.ndarray) -> dict:
    """Everything computable before object classification."""
    um = im.pixel_um
    n = seg.size
    pore = seg == config.PORE
    bulk = seg == config.BULK
    bright = seg == config.SI_CAND
    f = dict(image_id=im.image_id, batch=im.batch, path=im.path,
             n_px=int(n), pixel_um=float(um),
             height_um=float(seg.shape[0] * um),
             width_um=float(seg.shape[1] * um))
    f["pore_frac"] = float(pore.mean())
    f["bright_frac_raw"] = float(bright.mean())
    f["bulk_frac"] = float(bulk.mean())

    pore_lab = label(pore)
    pore_props = [r for r in regionprops(pore_lab)
                  if r.area >= px_params(um)["min_pore_px"]]
    f["pores_per_mpx"] = len(pore_props) / (n / 1e6)
    if pore_props:
        pd_um = [np.sqrt(4 * r.area / np.pi) * um for r in pore_props]
        f["pore_d50_um"] = float(np.median(pd_um))
    else:
        f["pore_d50_um"] = np.nan
    ch = _chord_lengths(pore, axis=1)
    cv = _chord_lengths(pore, axis=0)
    f["pore_chord_h_um"] = float(ch.mean() * um) if len(ch) else 0.0
    f["pore_chord_v_um"] = float(cv.mean() * um) if len(cv) else 0.0
    f["pore_anisotropy"] = f["pore_chord_h_um"] / max(f["pore_chord_v_um"],
                                                    1e-9)

    # imaging diagnostics
    raw = im.raw
    f["img_p1"] = float(np.percentile(raw, 1))
    f["img_p50"] = float(np.percentile(raw, 50))
    f["img_p99"] = float(np.percentile(raw, 99))
    i_p = raw[pore].mean() if pore.any() else np.nan
    i_b = raw[bulk].mean() if bulk.any() else np.nan
    i_s = raw[bright].mean() if bright.any() else np.nan
    f["si_bulk_contrast"] = ((i_s - i_p) / max(i_b - i_p, 1e-6)
                             if np.isfinite(i_s) else np.nan)
    resid = raw - gaussian_filter(raw, 2)
    bulk_resid = resid[bulk]
    f["noise_mad"] = float(1.4826 * np.median(np.abs(
        bulk_resid - np.median(bulk_resid)))) if bulk.any() else np.nan
    lap = np.abs(np.gradient(np.gradient(raw, axis=0), axis=0)
                 + np.gradient(np.gradient(raw, axis=1), axis=1))
    f["sharpness_lapvar"] = float(lap[bulk].var()) if bulk.any() else np.nan
    row_med = np.median(raw * bulk, axis=1)
    yy = np.arange(len(row_med))
    f["shading_slope"] = float(np.polyfit(yy, row_med, 1)[0]) \
        if len(yy) > 2 else np.nan
    f["has_inlens"] = int("Inlens" in im.channels)
    f["has_second_channel"] = int(bool(im.channels))
    return f


def si_features(objects_classified: pd.DataFrame, image_id: str,
                shape: tuple[int, int], pixel_um: float) -> dict:
    """Si-particle features for one image given a `kind` column."""
    sub = objects_classified[
        (objects_classified["image_id"] == image_id)
        & (objects_classified["kind"] == "si_particle")]
    n = shape[0] * shape[1]
    out = dict(si_n_particles=len(sub))
    if len(sub):
        d = sub["eq_diam_um"].to_numpy()
        a = sub["area_um2"].to_numpy()
        out["si_d50_um"] = _weighted_quantile(d, a, 0.5)
        out["si_d90_um"] = _weighted_quantile(d, a, 0.9)
        out["si_candidate_frac"] = float(
            sub["area_px"].sum() / n)
        if len(sub) > 2:
            cents = sub[["centroid_y_um", "centroid_x_um"]].to_numpy()
            tree = spatial.KDTree(cents)
            nn = tree.query(cents, k=2)[0][:, 1]
            lam = len(sub) / (n * pixel_um ** 2)
            exp_nn = 0.5 / np.sqrt(lam)
            per = 2 * (shape[0] + shape[1]) * pixel_um
            exp_nn += ((0.0514 + 0.041 / np.sqrt(len(sub)))
                       * per / len(sub))
            out["si_clustering_R"] = float(nn.mean() / exp_nn)
        else:
            out["si_clustering_R"] = np.nan
    else:
        out.update(si_d50_um=np.nan, si_d90_um=np.nan,
                   si_candidate_frac=0.0, si_clustering_R=np.nan)
    return out


# ---------------------------------------------------------------------------
# cached per-image pipeline
# ---------------------------------------------------------------------------
def extract_cached(im_path: str, batch: str, cache_dir: str,
                   downsample: int = 1) -> dict:
    """Extract (or load) raw per-image data: pixel features, objects, seg.

    Cache key: file md5 + recipe version + downsample.  Classification is
    deliberately NOT cached — it is applied at assembly time.
    """
    os.makedirs(cache_dir, exist_ok=True)
    image_id = os.path.basename(im_path).replace("_BSE.tif", "")
    meta_path = os.path.join(cache_dir, f"{image_id}_meta.json")
    md5 = file_md5(im_path)
    if os.path.exists(meta_path):
        meta = json.load(open(meta_path))
        if (meta["md5"] == md5 and meta["downsample"] == downsample
                and meta["recipe_version"] == config.RECIPE_VERSION):
            feats = json.load(open(
                os.path.join(cache_dir, f"{image_id}_features.json")))
            objects = pd.read_csv(
                os.path.join(cache_dir, f"{image_id}_objects.csv"))
            seg = np.load(os.path.join(
                cache_dir, f"{image_id}_seg.npz"))["seg"]
            return dict(features=feats, objects=objects, seg=seg,
                        meta=meta)

    im = Image(im_path, batch, downsample)
    px = px_params(im.pixel_um)
    # thresholds live in the recipe; extraction needs them — caller passes
    # via module-level stash set by `set_thresholds` before extraction.
    t_pore, t_si = _CURRENT_THRESHOLDS
    seg = segment(im.gray, t_pore, t_si, px)
    objects, _ = extract_objects(im.gray, seg == config.SI_CAND,
                                 im.pixel_um, px, image_id, batch)
    feats = pixel_features(im, seg)
    meta = dict(image_id=image_id, batch=batch, md5=md5,
                downsample=downsample, native_pixel_um=im.native_pixel_um,
                recipe_version=config.RECIPE_VERSION,
                pixel_um=im.pixel_um)
    # write all artifacts first, meta LAST (its presence = cache valid)
    json.dump(feats, open(os.path.join(
        cache_dir, f"{image_id}_features.json"), "w"), indent=2,
        default=float)
    objects.to_csv(os.path.join(
        cache_dir, f"{image_id}_objects.csv"), index=False)
    np.savez_compressed(os.path.join(cache_dir, f"{image_id}_seg.npz"),
                        seg=seg)
    json.dump(meta, open(meta_path, "w"), indent=2)
    return dict(features=feats, objects=objects, seg=seg, meta=meta)


_CURRENT_THRESHOLDS = (None, None)


def set_thresholds(t_pore: float, t_si: float) -> None:
    global _CURRENT_THRESHOLDS
    _CURRENT_THRESHOLDS = (t_pore, t_si)
