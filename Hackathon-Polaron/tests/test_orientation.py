"""Regression tests for micro2dfn/orientation.py — spec 8H.

Validates BOTH the math reducer (angle population -> S) and the
image->angle extractor on synthetics with known answers — a tested
formula cannot compensate reversed/biased extracted angles.

Run:  .venv/bin/python tests/test_orientation.py
"""
from __future__ import annotations

import sys

import numpy as np

sys.path.insert(0, ".")
from micro2dfn import orientation as O


def _stripe(shape, angle_deg, period=12, duty=0.5):
    """Bright stripes whose LONG axis is `angle_deg` from +x."""
    h, w = shape
    yy, xx = np.mgrid[0:h, 0:w]
    a = np.deg2rad(angle_deg)
    # coordinate along the stripe normal
    u = -xx * np.sin(a) + yy * np.cos(a)
    return ((u / period) % 1.0 < duty).astype(float)


def _tex(m, **kw):
    th, coh, _c, valid = O.texture_angles(m, sigma_deriv=1.0,
                                        sigma_coher=4.0, **kw)
    th, w = th[valid], coh[valid]
    assert len(th), "no valid texture pixels"
    return th, w, valid


def main():
    one = np.ones(5)

    # ---- 8H.1-3: reducer on known angle populations -----------------
    assert abs(O.s_ref(np.zeros(8), np.ones(8)) - 1.0) < 1e-12     # H
    assert abs(O.s_ref(90 * np.ones(8), np.ones(8)) + 1.0) < 1e-12  # V
    assert abs(O.s_ref(45 * np.ones(8), np.ones(8))) < 1e-9        # 45deg
    s, th = O.s_director(45 * np.ones(8), np.ones(8))
    assert abs(s - 1) < 1e-12 and abs(th - 45) < 1e-9

    # ---- 8H.4: equal H/V mixture -> S_x=0 AND S_dir=0 (bimodal!) ----
    hv = np.r_[np.zeros(50), 90 * np.ones(50)]
    assert abs(O.s_ref(hv, np.ones(100))) < 1e-12
    s, _ = O.s_director(hv, np.ones(100))
    assert abs(s) < 1e-12                      # S=0 != isotropic here
    cen, hist = O.axial_hist(hv, np.ones(100))
    # modes: theta=0 (horizontal, mid-range) and +90 (vertical, last bin)
    assert hist[9] > 0.4 and hist[-1] > 0.4, hist

    # ---- 8H.5: uniform axial angles -> second moments ~0 ------------
    uni = np.linspace(-90, 90, 360, endpoint=False)
    s, _ = O.s_director(uni, np.ones(360))
    assert s < 0.02, s

    # ---- 8H.6: rotation behaviour ----------------------------------
    s1, th1 = O.s_director(10 * np.ones(16), np.ones(16))
    s2, th2 = O.s_director(30 * np.ones(16), np.ones(16))
    assert abs(s1 - s2) < 1e-12 and abs((th2 - th1) - 20) < 1e-9
    # 90-deg rotation flips S_x sign
    assert abs(O.s_ref(30 * np.ones(8), np.ones(8))
               + O.s_ref((30 + 90) * np.ones(8), np.ones(8))) < 1e-9

    # ---- extractor: horizontal stripes -> theta~0, S_x~+1 -----------
    for ang, expect in ((0, 0), (90, 90), (45, 45)):
        img = _stripe((200, 200), ang)
        th, w, valid = _tex(img)
        r = O.reduce_population(th, w)
        assert abs(r["s_dir_2d"]) > 0.8, (ang, r)
        d = abs(((r["theta_dir_deg"] - expect + 90) % 180) - 90)
        assert d < 5, (ang, r["theta_dir_deg"])
    # horizontal stripes: S_x ~ +1 ; vertical: S_x ~ -1
    th, w, _ = _tex(_stripe((200, 200), 0))
    assert O.s_ref(th, w) > 0.8
    th, w, _ = _tex(_stripe((200, 200), 90))
    assert O.s_ref(th, w) < -0.8

    # ---- 8H.7: isotropic noise, TALL + WIDE + REAL frames ----------
    # (the FFT failure mode: it scored +0.70 on tall-frame noise purely
    # from frame aspect ratio; structure-tensor S_x must not)
    rng = np.random.default_rng(0)
    for shape in ((400, 120), (120, 400), (1034, 3500)):
        noise = rng.normal(0, 1, shape)
        th, w, _ = _tex(noise)
        r = O.reduce_population(th, w)
        assert abs(r["s_x_2d"]) < 0.1, (shape, r["s_x_2d"])
        # at the real frame size the null is tight; small frames have
        # a wider correlated-noise null (measured ~0.1-0.2 at 200-400px)
    noise = rng.normal(0, 1, (1034, 3500))
    th, w, _ = _tex(noise)
    r = O.reduce_population(th, w)
    med, p95 = O.null_s_director_resample(th, w, n_resample=50, seed=1)
    assert r["s_dir_2d"] < 0.1, r["s_dir_2d"]
    assert p95 < 0.05, p95                       # tight null at real size

    # ---- object angles: eligibility + convention --------------------
    m = np.zeros((100, 100), np.uint8)
    m[10:14, 10:60] = 1        # horizontal bar (long in x)
    m[70:95, 70:74] = 1        # vertical bar (long in y)
    m[40:45, 40:45] = 1        # round-ish -> excluded (aspect<2.5)
    th, ar = O.object_angles(m)
    assert len(th) == 2, th
    assert abs(th[0]) < 5, th                    # horizontal ~0
    assert abs(abs(th[1]) - 90) < 5, th          # vertical ~90
    # equal weighting: H+V mix -> 0; area weighting: (200-100)/300
    assert abs(O.s_ref(th, np.ones(2))) < 0.05
    assert abs(O.s_ref(th, ar) - (200 - 100) / 300) < 0.05

    # transpose/wrap sanity: an image and its transpose give mirrored S
    img = _stripe((160, 160), 0)
    r_a = O.reduce_population(*_tex(img)[:2])
    r_b = O.reduce_population(*_tex(img.T)[:2])
    assert abs(r_a["s_x_2d"] + r_b["s_x_2d"]) < 0.1

    # ---- empty/degenerate inputs ------------------------------------
    r = O.reduce_population(np.array([]), np.array([]))
    assert np.isnan(r["s_x_2d"])
    flat = np.ones((100, 100))
    th, coh, _c, valid = O.texture_angles(flat)
    assert valid.sum() == 0                      # flat -> all excluded

    print("test_orientation: all assertions passed")


if __name__ == "__main__":
    main()
