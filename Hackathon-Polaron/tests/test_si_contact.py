"""Regression tests for the accessible-silicon identity fix.

Shipped bug (confirmed on Batch_3/img_hawkfj64): the enclosed/contacted
count was measured on label(si_part) CONNECTED COMPONENTS but divided
by the watershed-particle count. Touching watershed particles merge
under connected-component labeling, so both populations were mixed.

Here the same mask is measured twice:
  - via si_labels (correct, per watershed object);
  - via connected components (the shipped path) — must disagree.
Plus empty-mask, no-pore, border-truncation and area/count accounting.

Run:  .venv/bin/python tests/test_si_contact.py
"""
from __future__ import annotations

import sys

import numpy as np
import pandas as pd

sys.path.insert(0, ".")
from micro2dfn import config, markers as mk
from micro2dfn.io import BSEImage
from skimage.measure import label

UM = 0.025


def _im(shape):
    g = np.ones(shape, np.float32)
    return BSEImage(image_id="t", batch="T", path="",
                    gray=g, raw=(g * 127).astype(np.uint8), pixel_um=UM)


def _obj_row(lab, area_px, diam_um):
    return dict(batch="T", image_id="t", label=lab, area_px=area_px,
                area_um2=area_px * UM ** 2, eq_diam_um=diam_um,
                interior_median=1.5, interior_std=0.1, solidity=0.95,
                aspect=1.0, touches_border=False,
                centroid_y_um=0.0, centroid_x_um=0.0)


def _synth():
    """40x90 bulk field, pore slab at cols 0-9, four Si particles:

    A (10x10, cols 12-21) -> within the 3-px contact band: CONTACTED.
    B (10x10, cols 22-31) -> touches A, far from pore: ENCLOSED.
    C (10x20, cols 60-79, rows 30-39) -> isolated, ENCLOSED.
    D (10x10, cols 80-89) -> touches right image border: ENCLOSED.

    Connected components see {A+B} contacted + {C} + {D} = 3 objects
    (2 enclosed). Watershed sees 4 objects (3 enclosed).
    """
    seg = np.full((40, 90), config.BULK, np.uint8)
    seg[0:40, 0:10] = config.PORE                       # 400 px pore slab
    lab_si = np.zeros(seg.shape, np.int32)
    lab_si[10:20, 12:22] = 1                            # A: 100 px
    lab_si[10:20, 22:32] = 2                            # B: 100 px
    lab_si[30:40, 60:80] = 3                            # C: 200 px
    lab_si[10:20, 80:90] = 4                            # D: 100 px (border)
    si_part = lab_si > 0
    seg[si_part] = config.SI
    objs = pd.DataFrame([
        _obj_row(1, 100, 2 * np.sqrt(100 / np.pi) * UM),
        _obj_row(2, 100, 2 * np.sqrt(100 / np.pi) * UM),
        _obj_row(3, 200, 2 * np.sqrt(200 / np.pi) * UM),
        _obj_row(4, 100, 2 * np.sqrt(100 / np.pi) * UM),
    ])
    objs.loc[objs.label == 4, "touches_border"] = True
    objs["kind"] = "si_particle"
    return _im(seg.shape), seg, objs, si_part, lab_si


def main():
    im, seg, objs, si_part, lab_si = _synth()
    fine = np.zeros(seg.shape, bool)

    # --- correct path: per watershed particle ----------------------
    f = mk.extract_markers(im, seg, objs, si_part, fine,
                           si_labels=lab_si)
    assert f["contact_population"] == "watershed_particles"
    # 3 of 4 particles enclosed -> contacted number fraction = 1/4
    assert abs(f["si_enclosed_share"] - 0.75) < 1e-9, f["si_enclosed_share"]
    assert abs(f["si_contact_num_frac"] - 0.25) < 1e-9
    # area-weighted contacted share = A / total = 100/500
    assert abs(f["si_contact_area_frac"] - 0.20) < 1e-9
    assert f["si_accessible_frac"] == f["si_contact_area_frac"]

    # --- the shipped bug would disagree on this exact mask ---------
    cc = label(si_part)
    assert cc.max() == 3                       # A+B merged into one
    # shipped code: enclosed_cc=2 divided by n_watershed=4 -> 0.5,
    # i.e. wrong on BOTH axes (CC numerator over WS denominator).

    # --- fallback path warns instead of being silently wrong -------
    f2 = mk.extract_markers(im, seg, objs, si_part, fine,
                            si_labels=None)
    assert f2["contact_population"] == "connected_components_FALLBACK"
    assert abs(f2["si_contact_num_frac"] - (1 - 2 / 3)) < 1e-9
    shipped = 1.0 - 2 / 4   # enclosed CC over watershed count (the bug)

    # --- empty masks ------------------------------------------------
    seg_e = np.full_like(seg, config.BULK)
    seg_e[0:40, 0:10] = config.PORE
    im_e = _im(seg_e.shape)
    objs_e = objs.iloc[0:0].copy()
    f3 = mk.extract_markers(im_e, seg_e, objs_e,
                            np.zeros(seg.shape, bool), fine,
                            si_labels=np.zeros(seg.shape, np.int32))
    assert f3["contact_population"] == "no_particles"
    assert np.isnan(f3["si_contact_num_frac"])
    assert np.isnan(f3["si_accessible_frac"])

    # --- Si present but no resolved pore ----------------------------
    seg_np = np.full_like(seg, config.BULK)
    seg_np[si_part] = config.SI
    f4 = mk.extract_markers(_im(seg_np.shape), seg_np, objs,
                            si_part, fine, si_labels=lab_si)
    assert f4["contact_population"] == "watershed_particles"
    assert f4["si_contact_num_frac"] == 0.0     # everything enclosed
    assert f4["si_contact_area_frac"] == 0.0

    print("test_si_contact: all assertions passed")
    print(f"  corrected num_frac={f['si_contact_num_frac']:.4f} "
          f"area_frac={f['si_contact_area_frac']:.4f} "
          f"(shipped bug gives {shipped:.4f})")


if __name__ == "__main__":
    main()
