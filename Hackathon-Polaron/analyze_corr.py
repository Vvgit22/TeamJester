"""analyze_corr.py — spatial-correlation + multiscale clustering view.

S2(r): two-point probability for binary phase masks, computed by LINEAR
(zero-padded) autocorrelation with exact valid-pair normalisation for a
rectangular frame — no circular wraparound.  Directional slices along
image x and y plus a radial average.  Characteristic length = first lag
where normalised covariance < 1/e; if absent the length is reported as
NaN with censored=True (never a cap presented as a measurement).

PCF g(r): pair-correlation of classified-si_particle centroids vs a
CSR simulation envelope (same window, same n) — 199 sims.  Uniform
centroids are NOT a physically exact null for tightly packed finite-size
particles; the envelope is reported, not hidden.

Outputs: corr_analysis/{s2_curves,s2_summary,pcf_curves,pcf_summary}.csv
Inline sanity asserts run first (uniform vs clustered vs periodic).
"""
import os

import numpy as np
import pandas as pd

PX_UM = 0.025
RMAX_PX = 400          # 10 um max lag analysed
RMAX_PCF_UM = 15.0     # ~half of min frame height
PCF_DR_UM = 0.5
N_SIM = 199
RNG = np.random.default_rng(0)
PHASES = {"pore": 0, "bright": 2}
CACHE = "validated_comparison/cache_ds2"
OUT = "corr_analysis"


def s2_curves(mask: np.ndarray) -> dict:
    """Valid-pair-normalised two-point probability + norm covariance."""
    f = mask.astype(np.float64)
    H, W = f.shape
    p = f.mean()
    if p < 1e-4 or p > 1 - 1e-4:
        return None
    F = np.fft.rfft2(f, s=(2 * H, 2 * W))
    ac = np.fft.irfft2(F * np.conj(F), s=(2 * H, 2 * W))[:H, :W]
    ys = np.arange(H)[:, None]
    xs = np.arange(W)[None, :]
    pairs = (H - ys) * (W - xs)          # rectangle valid-pair counts
    s2 = ac / pairs
    norm = (s2 - p * p) / (p * (1 - p))
    r = np.hypot(ys, xs).astype(np.int32)
    keep = r <= RMAX_PX
    sums = np.bincount(r[keep].ravel(), weights=norm[keep].ravel())
    cnt = np.bincount(r[keep].ravel())
    return {"r_px": np.arange(RMAX_PX + 1),
            "radial": sums / np.maximum(cnt, 1),
            "x": norm[0, :RMAX_PX + 1],
            "y": norm[:RMAX_PX + 1, 0]}


def corr_length(curve: np.ndarray, px_um: float) -> tuple:
    """First lag where normalised cov < 1/e.  NaN + censored if absent."""
    below = np.where(curve[1:] < 1.0 / np.e)[0] + 1
    if not len(below):
        return np.nan, True
    return float(below[0]) * px_um, False


def pcf(points: np.ndarray, w_um: float, h_um: float,
        n_sim: int = N_SIM) -> dict:
    """g(r) vs CSR envelope.  points: (n,2) um within w x h window."""
    n = len(points)
    if n < 20:
        return None
    from scipy.spatial.distance import pdist
    edges = np.arange(0, RMAX_PCF_UM + PCF_DR_UM, PCF_DR_UM)
    obs = np.histogram(pdist(points), bins=edges)[0]
    sims = np.empty((n_sim, len(edges) - 1))
    for s in range(n_sim):
        pts = np.column_stack([RNG.uniform(0, w_um, n),
                               RNG.uniform(0, h_um, n)])
        sims[s] = np.histogram(pdist(pts), bins=edges)[0]
    exp = sims.mean(0)
    return {"r_um": edges[:-1] + PCF_DR_UM / 2,
            "g": np.where(exp > 0, obs / exp, np.nan),
            "lo": np.quantile(np.where(exp > 0, sims / exp, np.nan),
                              0.025, axis=0),
            "hi": np.quantile(np.where(exp > 0, sims / exp, np.nan),
                              0.975, axis=0),
            "n": n}


def _sanity() -> None:
    """Known-answer checks: uniform noise ~0 cov; stripes periodic;
    clustered points g(0) above CSR envelope."""
    rng = np.random.default_rng(1)
    u = rng.random((300, 400)) < 0.2
    c = s2_curves(u)
    assert c is not None and abs(c["radial"][5]) < 0.1, "uniform cov!"
    st = np.zeros((300, 400), bool)
    st[:, ::40] = True                      # 40px-period stripes (x)
    c2 = s2_curves(st)
    assert c2["x"][40] > 0.5, "periodic stripes must correlate at period"
    clustered = np.concatenate([
        rng.uniform(0, 30, (200, 2)) + np.array([i * 40, 0])
        for i in range(8)])
    clustered[:, 1] %= 60.0
    r = pcf(clustered[clustered[:, 0] < 320], 320.0, 60.0, n_sim=19)
    assert r is not None and np.nanmax(r["g"]) > 2, "cluster g<2!"
    print("sanity: uniform cov≈0, stripe period resolved, cluster g>2")


def main() -> None:
    _sanity()
    os.makedirs(OUT, exist_ok=True)
    objs = pd.read_csv("validated_comparison/objects_classified.csv")
    acq = pd.read_csv("image_acquisition.csv")
    idcol = "image_id" if "image_id" in acq.columns else acq.columns[0]
    s2_rows, s2_sum, pcf_rows, pcf_sum = [], [], [], []
    for fn in sorted(os.listdir(CACHE)):
        if not fn.endswith("_seg.npz"):
            continue
        img = fn[:-8]
        seg = np.load(os.path.join(CACHE, fn))["seg"]
        for phase, code in PHASES.items():
            c = s2_curves(seg == code)
            if c is None:
                continue
            for d, arr in (("radial", c["radial"]), ("x", c["x"]),
                           ("y", c["y"])):
                for i, v in enumerate(arr):
                    s2_rows.append((img, phase, d, i * PX_UM,
                                    round(float(v), 5)))
            lx, cx = corr_length(c["x"], PX_UM)
            ly, cy = corr_length(c["y"], PX_UM)
            lr, cr = corr_length(c["radial"], PX_UM)
            s2_sum.append(dict(image_id=img, phase=phase,
                               len_x_um=lx, len_y_um=ly, len_r_um=lr,
                               censored=int(cx or cy or cr),
                               anisotropy=(lx / ly) if ly and not
                               (cx or cy) else np.nan))
        sub = objs[(objs.image_id == img) & (objs.kind == "si_particle")]
        pts = sub[["centroid_x_um", "centroid_y_um"]].values
        if len(pts) >= 20:
            meta = acq[acq[idcol] == img]
            w_um = float(meta.w_px.iloc[0]) * PX_UM if "w_px" in meta \
                else float(seg.shape[1]) * PX_UM
            h_um = float(meta.h_px.iloc[0]) * PX_UM if "h_px" in meta \
                else float(seg.shape[0]) * PX_UM
            r = pcf(pts, w_um, h_um)
            if r:
                for i in range(len(r["r_um"])):
                    pcf_rows.append((img, round(r["r_um"][i], 3),
                                     round(float(r["g"][i]), 4),
                                     round(float(r["lo"][i]), 4),
                                     round(float(r["hi"][i]), 4)))
                peak = int(np.nanargmax(r["g"]))
                pcf_sum.append(dict(image_id=img, n_si=r["n"],
                                    g_peak=float(r["g"][peak]),
                                    peak_r_um=float(r["r_um"][peak]),
                                    g_above_env=bool(
                                        np.any(r["g"] > r["hi"]))))
        print(f"  {img} done")
    pd.DataFrame(s2_rows, columns=["image_id", "phase", "direction",
                                   "r_um", "norm_cov"]).to_csv(
        f"{OUT}/s2_curves.csv", index=False)
    pd.DataFrame(s2_sum).to_csv(f"{OUT}/s2_summary.csv", index=False)
    pd.DataFrame(pcf_rows, columns=["image_id", "r_um", "g",
                                    "env_lo", "env_hi"]).to_csv(
        f"{OUT}/pcf_curves.csv", index=False)
    pd.DataFrame(pcf_sum).to_csv(f"{OUT}/pcf_summary.csv", index=False)
    print("wrote", OUT)


if __name__ == "__main__":
    main()
