"""2-D nematic orientational order (S) for BSE cross-sections.

Conventions (declared, tested in tests/test_orientation.py):
  * image x = columns (horizontal), y = rows (downward-vertical).
  * theta in (-90, +90] deg, AXIAL: theta and theta+180 identical.
  * theta = 0 -> alignment with image-horizontal; theta = +/-90 ->
    image-vertical; measured FROM the +x axis.
  * reference axis theta0 = 0 deg (image-horizontal) unless stated.

Statistics (per declared angle population + weighting):
  S_ref(theta0)   = <w cos 2(theta-theta0)> / <w>
                  = 2 <cos^2(theta-theta0)>_w - 1   in [-1, +1]
    +1 all parallel to theta0, -1 all perpendicular, 0 no net
    preference AT THIS AXIS (NOT isotropy: 45 deg alignment or an
    equal H/V mix also give 0).
  C2 = <w cos 2theta>/<w>;  D2 = <w sin 2theta>/<w>
  S_director_2d = sqrt(C2^2 + D2^2)  in [0, 1] — alignment strength
    irrespective of direction; an equal orthogonal mix can still
    give ~0, so the histogram must accompany every S.
  theta_director = 0.5 atan2(D2, C2) mod 180 — unstable when
    S_director is small; reported with the isotropic-null baseline.

This is MORPHOLOGICAL order of image structures — not EBSD/IPF
crystallographic orientation, not 3-D order (the 3-D Hermans
(3<cos^2>-1)/2 has a different isotropic reference), and no causal
reading (calendering, curtaining, damage) is implied.
"""
from __future__ import annotations

import numpy as np
from scipy.ndimage import gaussian_filter
from skimage.feature import structure_tensor
from skimage.measure import regionprops


# --------------------------------------------------------------------------
# reducers (pure math on angle populations)
# --------------------------------------------------------------------------

def axial_moments(theta_deg: np.ndarray, w: np.ndarray
                  ) -> tuple[float, float]:
    """(C2, D2) = weighted means of cos 2theta, sin 2theta."""
    w = np.asarray(w, float)
    t = np.deg2rad(np.asarray(theta_deg, float))
    wsum = w.sum()
    if wsum <= 0 or not len(t):
        return np.nan, np.nan
    return (float((w * np.cos(2 * t)).sum() / wsum),
            float((w * np.sin(2 * t)).sum() / wsum))


def s_ref(theta_deg: np.ndarray, w: np.ndarray,
          theta0_deg: float = 0.0) -> float:
    """S relative to reference axis theta0 (default: horizontal)."""
    c2, d2 = axial_moments(np.asarray(theta_deg) - theta0_deg, w)
    return c2   # cos 2(theta - theta0) IS C2 of the shifted population


def s_director(theta_deg: np.ndarray, w: np.ndarray
               ) -> tuple[float, float]:
    """(S_director_2d, theta_director_deg mod 180)."""
    c2, d2 = axial_moments(theta_deg, w)
    s = float(np.hypot(c2, d2))
    th = float(np.degrees(0.5 * np.arctan2(d2, c2)) % 180.0)
    if th > 90.0:
        th -= 180.0
    return s, th


def null_s_director(n_eff: float) -> float:
    """Finite-sample expected S_director under uniform axial angles:
    E[sqrt(C2^2+D2^2)] ~ 1/sqrt(n_eff) for INDEPENDENT orientations.
    Spatially correlated populations (texture maps) have a much smaller
    effective n — treat this as a lower bound and prefer
    null_s_blocks() for real images."""
    return float(1.0 / np.sqrt(max(n_eff, 1.0)))


def null_s_director_resample(theta_deg: np.ndarray, w: np.ndarray,
                             n_resample: int = 200, seed: int = 0
                             ) -> tuple[float, float]:
    """Empirical isotropic-null S_director for THIS weight vector.

    Draws n angles i.i.d. uniform on (-90, +90] (the axial-isotropic
    null) against the SAME weights, then S_director. Returns (median,
    p95) — p95 is the value exceeded by pure chance 5% of the time.

    NOTE: permuting (theta, w) pairs would be WRONG here — S_director
    is a population statistic, invariant to pair order, so a pair
    permutation returns the observed value (equal-weight case
    degenerates entirely). Caveat: for texture populations pixels are
    spatially correlated, so this n-based null is OPTIMISTIC — treat
    marginal exceedances as 'can't tell', not detections."""
    w = np.asarray(w, float)
    rng = np.random.default_rng(seed)
    n = len(theta_deg)
    if n < 4:
        return np.nan, np.nan
    out = np.empty(n_resample)
    for i in range(n_resample):
        s, _ = s_director(rng.uniform(-90.0, 90.0, n), w)
        out[i] = s
    return float(np.median(out)), float(np.quantile(out, 0.95))


def axial_hist(theta_deg: np.ndarray, w: np.ndarray,
               bins: int = 18) -> tuple[np.ndarray, np.ndarray]:
    """Weighted axial histogram on (-90, +90]; returns (centers, frac)."""
    edges = np.linspace(-90.0, 90.0, bins + 1)
    h, _ = np.histogram(np.asarray(theta_deg, float), bins=edges,
                        weights=w)
    return 0.5 * (edges[:-1] + edges[1:]), h / max(h.sum(), 1e-12)


def reduce_population(theta_deg: np.ndarray, w: np.ndarray,
                      theta0_deg: float = 0.0) -> dict:
    """Full S bundle for one declared population."""
    theta_deg = np.asarray(theta_deg, float)
    w = np.asarray(w, float)
    ok = np.isfinite(theta_deg) & np.isfinite(w) & (w > 0)
    theta_deg, w = theta_deg[ok], w[ok]
    n = len(theta_deg)
    out = dict(n_orientations=n, w_sum=float(w.sum()))
    if not n:
        out.update(s_x_2d=np.nan, s_dir_2d=np.nan,
                   theta_dir_deg=np.nan, null_s=np.nan)
        return out
    s_dir, th_dir = s_director(theta_deg, w)
    out.update(
        s_x_2d=s_ref(theta_deg, w, theta0_deg),
        s_dir_2d=s_dir, theta_dir_deg=th_dir,
        null_s=null_s_director(float((w.sum() ** 2) / (w ** 2).sum())))
    return out


# --------------------------------------------------------------------------
# extractors (image/mask -> angle populations)
# --------------------------------------------------------------------------

def texture_angles(gray: np.ndarray, sigma_deriv: float = 1.0,
                   sigma_coher: float = 4.0,
                   mask: np.ndarray | None = None,
                   coher_min: float = 0.3, energy_min: float = 1e-4
                   ) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Structure-tensor texture orientations.

    Returns (theta_deg, weight, coherence, valid) where valid marks
    pixels passing eligibility (coherence + tensor-energy thresholds).
    Angles are the direction ALONG the visible structure — the
    smallest-eigenvalue axis of the smoothed tensor (the dominant
    eigenvector is the gradient NORMAL, 90 deg away; validated on
    synthetic stripes).

    sigma_deriv: derivative scale (px). sigma_coher: averaging window
    (px) — the local order scale; declared in outputs.
    """
    gy, gx = np.gradient(gaussian_filter(gray.astype(float),
                                         sigma_deriv))
    jxx = gaussian_filter(gx * gx, sigma_coher)
    jxy = gaussian_filter(gx * gy, sigma_coher)
    jyy = gaussian_filter(gy * gy, sigma_coher)
    tr = jxx + jyy
    det_term = np.hypot(jxx - jyy, 2 * jxy)
    coherence = np.divide(det_term, tr, out=np.zeros_like(tr),
                          where=tr > 0)
    # direction along structure = principal axis of the tensor + 90deg;
    # axial so the wrap is irrelevant
    theta = np.degrees(0.5 * np.arctan2(2 * jxy, jxx - jyy)) + 90.0
    theta = ((theta + 90.0) % 180.0) - 90.0
    valid = (coherence >= coher_min) & (tr >= energy_min)
    if mask is not None:
        valid &= mask
    return theta, coherence, coherence, valid


def object_angles(mask: np.ndarray, min_aspect: float = 2.5,
                  min_minor_px: float = 3.0, min_area_px: float = 20,
                  label_image: np.ndarray | None = None
                  ) -> tuple[np.ndarray, np.ndarray]:
    """Major-axis orientations of elongated objects.

    Eligibility (prespecified): area >= min_area_px,
    aspect >= min_aspect, minor axis >= min_minor_px — nearly round
    objects have unstable axes and are excluded (counted as coverage).

    skimage regionprops.orientation is measured FROM the row axis
    (vertical); converted here to our +x convention:
        theta_x = 90 - theta_row      (mod 180, onto (-90, +90])
    Returns (theta_deg, weight=area_px) — equal-weight callers can
    pass np.ones instead downstream; we return area so BOTH weightings
    stay computable."""
    lab = label_image if label_image is not None else None
    if lab is None:
        from skimage.measure import label as _label
        lab = _label(mask)
    thetas, areas = [], []
    for r in regionprops(lab):
        minor = max(r.axis_minor_length, 1e-9)
        if (r.area < min_area_px or minor < min_minor_px
                or r.axis_major_length / minor < min_aspect):
            continue
        th = (90.0 - np.degrees(r.orientation)) % 180.0
        if th > 90.0:
            th -= 180.0
        thetas.append(th)
        areas.append(float(r.area))
    return np.asarray(thetas), np.asarray(areas)
