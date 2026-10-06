"""Assemble the per-image feature table from cached extractions + recipe.

Classification is applied here (post-hoc), so scenario variants that only
change `t_core` reuse the identical objects — exactly what the disputed-
image diagnostics need.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import config, extract, recipe as recipe_mod


def classify_objects(objects: pd.DataFrame, t_core: float) -> pd.DataFrame:
    objects = objects.copy()
    objects["kind"] = extract.classify(objects, t_core)
    return objects


def build_features(extractions: dict[str, dict], objects_all: pd.DataFrame,
                   recipe: dict) -> pd.DataFrame:
    """One row per image: pixel features + Si features + noise-adjusted
    pore count + diagnostics.  `objects_all` must already carry `kind`."""
    rows = []
    for image_id, ext in extractions.items():
        f = dict(ext["features"])
        si = extract.si_features(
            objects_all, image_id, ext["seg"].shape,
            ext["meta"]["pixel_um"])
        f.update(si)
        # uncertain bright = bright area not classified as si_candidate
        f["uncertain_bright_frac"] = float(
            f["bright_frac_raw"] - f.get("si_candidate_frac", 0.0))
        # 4-class accounting check column (validated later by checks.py)
        f["label_frac_sum"] = float(
            f["pore_frac"] + f["bulk_frac"] + f["bright_frac_raw"])
        rows.append(f)
    table = pd.DataFrame(rows)
    table["pores_per_mpx_noise_adj"] = recipe_mod.noise_adjust(
        table["pores_per_mpx"].to_numpy(float),
        table["noise_mad"].to_numpy(float), recipe)
    table["is_disputed"] = table["image_id"].isin(config.DISPUTED_IMAGES)
    table["diagnostic_status"] = np.where(
        table[["noise_mad", "si_bulk_contrast", "sharpness_lapvar"]]
        .notna().all(axis=1), "complete", "missing")
    return table


def four_class_map(ext: dict, objects_classified: pd.DataFrame
                   ) -> np.ndarray:
    """Rebuild the 4-class label map for one image (for panels)."""
    seg = ext["seg"].copy()
    image_id = ext["meta"]["image_id"]
    px = extract.px_params(ext["meta"]["pixel_um"])
    lab = extract.split_bright(seg == config.SI_CAND, px)
    fine_ids = set(objects_classified.loc[
        (objects_classified["image_id"] == image_id)
        & (objects_classified["kind"] == "bright_fine"), "label"])
    seg[np.isin(lab, list(fine_ids))] = config.UNCERTAIN
    return seg
