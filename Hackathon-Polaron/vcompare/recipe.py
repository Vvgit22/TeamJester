"""The frozen reference recipe — fitted on the reference batch ONLY.

Adding a future batch must never change it: everything in `recipe.json`
derives from Batch_3 pixels/objects plus fixed physical-unit parameters.
`fit_recipe` is deterministic (seeded), which the regression checks verify.
"""
from __future__ import annotations

import json
import os

import numpy as np
import pandas as pd

from . import config, extract


def fit_recipe(ref_extractions: list[dict], t_pore: float, t_si: float,
               image_files: dict, seed: int = config.SEED) -> dict:
    """Build the frozen recipe from reference-only ingredients.

    `t_pore`/`t_si` are fitted upstream on reference pixels only
    (deterministic, seeded).  `ref_extractions` are the cached per-image
    dicts for the reference batch under those thresholds.
    """

    # object classifier cutoff from reference objects only
    objects = pd.concat([e["objects"] for e in ref_extractions],
                        ignore_index=True)
    t_core = extract.calibrate_t_core(objects)

    # noise adjustment for pore count: reference images only
    feats = pd.DataFrame([e["features"] for e in ref_extractions])
    ref_pixel_ums = feats["pixel_um"].to_numpy()
    ok = feats["noise_mad"].notna() & feats["pores_per_mpx"].notna()
    x = feats.loc[ok, "noise_mad"].to_numpy()
    y = feats.loc[ok, "pores_per_mpx"].to_numpy()
    slope, intercept = np.polyfit(x, y, 1)
    recipe = dict(
        recipe_version=config.RECIPE_VERSION,
        fitted_on=config.REFERENCE_BATCH,
        n_reference_images=len(ref_extractions),
        seed=seed,
        pixel_um_expected=float(np.median(ref_pixel_ums)),
        t_pore=float(t_pore), t_si=float(t_si), t_core=t_core,
        noise_adj=dict(slope=float(slope), intercept=float(intercept),
                       ref_noise_median=float(np.median(x)),
                       n_used=int(ok.sum()),
                       ref_r2=float(np.corrcoef(x, y)[0, 1] ** 2)
                       if ok.sum() > 2 else np.nan),
        params_um=dict(
            flatfield_sigma_um=config.FLATFIELD_SIGMA_UM,
            seg_smooth_sigma_um=config.SEG_SMOOTH_SIGMA_UM,
            object_erode_um=config.OBJECT_ERODE_UM,
            contact_dilation_um=config.CONTACT_DILATION_UM,
            watershed_min_dist_um=config.WATERSHED_MIN_DIST_UM,
            min_bright_area_um2=config.MIN_BRIGHT_AREA_UM2,
            min_pore_area_um2=config.MIN_PORE_AREA_UM2,
            si_calib_min_diam_um=config.SI_CALIB_MIN_DIAM_UM,
            si_calib_min_solidity=config.SI_CALIB_MIN_SOLIDITY,
            si_core_percentile=config.SI_CORE_PERCENTILE,
            si_min_solidity=config.SI_MIN_SOLIDITY),
        file_md5={iid: extract.file_md5(p)
                  for iid, p in image_files.items()},
    )
    return recipe


def save_recipe(recipe: dict, path: str) -> None:
    with open(path, "w") as fh:
        json.dump(recipe, fh, indent=2)


def load_recipe(path: str) -> dict:
    with open(path) as fh:
        return json.load(fh)


def noise_adjust(pores_per_mpx: np.ndarray, noise_mad: np.ndarray,
                 recipe: dict) -> np.ndarray:
    """Remove the reference-fitted noise contribution from pore counts.

    adj = raw - slope * (noise_mad - ref_median_noise)
    Fitted on reference images only; NaN diagnostics stay NaN.
    """
    na = recipe["noise_adj"]
    out = pores_per_mpx - na["slope"] * (noise_mad - na["ref_noise_median"])
    return out
