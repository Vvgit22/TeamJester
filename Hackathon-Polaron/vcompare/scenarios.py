"""Robustness scenarios — justified alternatives + labelled stress tests.

Each scenario produces a per-image feature table (or the subset of
features the variant legitimately affects) and the pairwise table is
rerun.  `omit_disputed` is a dependence diagnostic: a changed conclusion
may reflect heterogeneity or reduced power, not automatically an artefact.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from . import assemble, config, extract


PIXEL_LEVEL_FEATURES = ("pore_frac", "pores_per_mpx", "pore_anisotropy",
                        "pores_per_mpx_noise_adj")


def scenario_tables(extractions: dict, objects_all: pd.DataFrame,
                    recipe: dict, feats: pd.DataFrame,
                    batch_paths: dict[str, list[str]],
                    extractions_2x: dict | None = None,
                    objects_2x: pd.DataFrame | None = None,
                    ) -> dict[str, pd.DataFrame]:
    """Return {scenario_name: feature_table}."""
    out = {}

    out["harmonized_ref"] = feats.copy()

    # pooled classifier: identical objects, t_core refit on ALL batches
    t_core_pooled = extract.calibrate_t_core(objects_all)
    objs_pooled = assemble.classify_objects(objects_all, t_core_pooled)
    out["pooled_classifier"] = assemble.build_features(
        extractions, objs_pooled, recipe)

    # downsampled_2x: same physical recipe at 50 nm/px — legitimate now
    # that all spatial parameters are physical units
    if extractions_2x is not None and objects_2x is not None:
        objs2 = assemble.classify_objects(objects_2x, recipe["t_core"])
        out["downsampled_2x"] = assemble.build_features(
            extractions_2x, objs2, recipe)

    # omit the two disputed photos (diagnostic only)
    out["omit_disputed"] = feats[~feats.is_disputed].copy()

    return out


def threshold_stress(batch_paths: dict[str, list[str]], recipe: dict,
                     deltas=(-0.02, 0.02)) -> pd.DataFrame:
    """Pixel-level features under t_pore/t_si +/- delta.

    Objects are not re-split — this is a labelled stress test of the
    pixel-level features only, not a full alternative recipe.
    """
    rows = []
    for batch, paths in batch_paths.items():
        for path in paths:
            im = extract.Image(path, batch)
            px = extract.px_params(im.pixel_um)
            for tag, dt_p, dt_s in (("plus", deltas[1], deltas[1]),
                                    ("minus", deltas[0], deltas[0])):
                seg = extract.segment(im.gray, recipe["t_pore"] + dt_p,
                                      recipe["t_si"] + dt_s, px)
                f = extract.pixel_features(im, seg)
                f["scenario"] = f"thresholds_{tag}_002"
                rows.append(f)
    tab = pd.DataFrame(rows)
    # noise adjustment is threshold-independent (fitted on noise_mad vs
    # pore count on the reference), so it applies under stress too
    from . import recipe as recipe_mod
    tab["pores_per_mpx_noise_adj"] = recipe_mod.noise_adjust(
        tab["pores_per_mpx"].to_numpy(float),
        tab["noise_mad"].to_numpy(float), recipe)
    return tab
