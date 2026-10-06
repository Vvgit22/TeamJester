"""Matched disagreement panels + expert review sheet.

For each selected image: same crop shown as raw BSE | QC-recipe labels |
harmonized 4-class labels | disagreement map, with a scale bar and fixed
contrast.  Selection rule is recorded in the review sheet.
"""
from __future__ import annotations

import os

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from matplotlib import colors as mcolors
from matplotlib.patches import Rectangle

from . import config, extract

CROP = 1024  # crop side in pixels (~26 um at 25 nm/px)

_LABEL_COLORS = {config.PORE: (0.05, 0.05, 0.10),
                 config.BULK: (0.55, 0.55, 0.60),
                 config.SI_CAND: (0.95, 0.55, 0.10),
                 config.UNCERTAIN: (0.90, 0.20, 0.60)}
_LABEL_NAMES = {config.PORE: "pore", config.BULK: "bulk",
                config.SI_CAND: "Si candidate",
                config.UNCERTAIN: "uncertain bright"}


def _pick_crop(disagree_density: np.ndarray, shape) -> tuple[int, int]:
    """Crop centred on the densest disagreement region."""
    if disagree_density.sum() == 0:
        return (shape[0] // 2 - CROP // 2, shape[1] // 2 - CROP // 2)
    from scipy.ndimage import uniform_filter
    dens = uniform_filter(disagree_density.astype(np.float32),
                          size=CROP // 2)
    y, x = np.unravel_index(np.argmax(dens), dens.shape)
    return (int(np.clip(y - CROP // 2, 0, shape[0] - CROP)),
            int(np.clip(x - CROP // 2, 0, shape[1] - CROP)))


def _cmap_labels():
    cmap = mcolors.ListedColormap(
        [_LABEL_COLORS[k] for k in sorted(_LABEL_COLORS)])
    return cmap, mcolors.BoundaryNorm(range(5), cmap.N)


def _scale_bar(ax, pixel_um: float, length_um: float = 10.0):
    px = length_um / pixel_um
    y0, x0 = CROP - 40, CROP - 40 - px
    ax.add_patch(Rectangle((x0, y0), px, 14, color="white"))
    ax.text(x0 + px / 2, y0 - 30, f"{length_um:g} µm", color="white",
            ha="center", fontsize=11)


def make_panels(images: dict[str, tuple[str, str]], extractions,
                objects_cls: pd.DataFrame, qc_thresholds,
                recipe: dict, out_dir: str) -> pd.DataFrame:
    """images: image_id -> (batch, path) for the selected subset.

    Returns the review-sheet table (one row per panelled image).
    """
    from .assemble import four_class_map
    os.makedirs(out_dir, exist_ok=True)
    cmap, norm = _cmap_labels()
    rows = []
    qc_tp, qc_ts = qc_thresholds
    for image_id, (batch, path) in images.items():
        ext = extractions[image_id]
        seg_h = four_class_map(ext, objects_cls)
        # QC-recipe labels: pooled thresholds, no object filter
        im = extract.Image(path, batch,
                           downsample=ext["meta"]["downsample"])
        px = extract.px_params(im.pixel_um)
        seg_qc = extract.segment(im.gray, qc_tp, qc_ts, px)
        # disagreement: QC calls Si but harmonized says uncertain, etc.
        qc_si = seg_qc == config.SI_CAND
        h_si = seg_h == config.SI_CAND
        h_un = seg_h == config.UNCERTAIN
        disagree = np.zeros(seg_h.shape, np.uint8)
        disagree[qc_si & h_si] = 1            # both call it Si
        disagree[qc_si & ~h_si & ~h_un] = 2   # QC only
        disagree[h_un] = 3                    # harmonized uncertain
        disagree[~qc_si & h_si] = 4           # harmonized only

        y0, x0 = _pick_crop((seg_h == config.UNCERTAIN), seg_h.shape)
        sl = np.s_[y0:y0 + CROP, x0:x0 + CROP]
        raw = im.raw[sl]
        lo, hi = np.percentile(raw, (1, 99))

        fig, axes = plt.subplots(1, 4, figsize=(22, 6.2))
        for ax, data, title in zip(
                axes,
                [raw, seg_qc[sl], seg_h[sl], disagree[sl]],
                ["BSE raw", "QC labels (pooled recipe, no filter)",
                 "Harmonized labels (frozen, reference-fit)",
                 "Disagreement"]):
            ax.set_xticks([]); ax.set_yticks([])
            if data is raw:
                ax.imshow(data, cmap="gray", vmin=lo, vmax=hi)
            elif title == "Disagreement":
                dc = mcolors.ListedColormap(
                    [(0.05, 0.05, 0.10), (0.2, 0.7, 0.3),
                     (0.9, 0.1, 0.1), (0.90, 0.20, 0.60),
                     (0.1, 0.4, 0.9)])
                ax.imshow(data, cmap=dc, vmin=0, vmax=4,
                          interpolation="nearest")
            else:
                ax.imshow(data, cmap=cmap, norm=norm,
                          interpolation="nearest")
            ax.set_title(title, fontsize=13)
        _scale_bar(axes[0], im.pixel_um)
        fig.suptitle(f"{image_id}  ({batch})   "
                     f"crop y[{y0}:{y0 + CROP}] x[{x0}:{x0 + CROP}]",
                     fontsize=15, fontweight="bold")
        handles = [plt.Rectangle((0, 0), 1, 1, color=_LABEL_COLORS[k])
                   for k in sorted(_LABEL_COLORS)]
        fig.legend(handles, [_LABEL_NAMES[k] for k in sorted(_LABEL_COLORS)],
                   loc="lower center", ncol=4, fontsize=11,
                   title="label map key", title_fontsize=11)
        fig.tight_layout(rect=(0, 0.06, 1, 0.94))
        png = os.path.join(out_dir, f"panel_{image_id}.png")
        fig.savefig(png, dpi=140)
        plt.close(fig)
        rows.append(dict(
            image_id=image_id, batch=batch, panel_png=png,
            crop_y0=y0, crop_y1=y0 + CROP, crop_x0=x0, crop_x1=x0 + CROP,
            pixel_um=im.pixel_um,
            uncertain_bright_frac=float((seg_h == config.UNCERTAIN).mean()),
            si_candidate_frac=float((seg_h == config.SI_CAND).mean()),
            qc_si_frac=float(qc_si.mean()),
            disagreement_frac=float((disagree >= 2).mean()),
            expert_label="", expert_comment=""))
    return pd.DataFrame(rows)
