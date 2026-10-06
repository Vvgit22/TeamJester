"""Build every image asset for the deck from TeamJester main's pinned data,
masks and tables (read-only). Annotation coordinates (image pixels) are
written to assets/annotations.json so build_deck.py can draw them as
editable PowerPoint shapes.

    python src/make_assets.py --repo /path/to/teamjester_main_<sha>
"""
import argparse
import json
import os
import pickle
import sys

import numpy as np
import pandas as pd
from PIL import Image
from scipy import ndimage as ndi
from skimage.measure import find_contours, regionprops
from skimage.segmentation import find_boundaries

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = os.path.dirname(HERE)
ASSETS = os.path.join(DECK, "assets")
sys.path.insert(0, HERE)
import style as S  # noqa: E402

IMG = "cfe5vt7s"                    # typical Batch_3 image (see ledger)
BATCH = "Batch_3"
REGION = (3500, 600, 1500, 800)     # x0, y0, w, h  (slide 3 panels)
CLOSEUP = (3850, 620, 450, 300)     # ambiguous object (slide 3 close-up)
HERO_ROWS = (450, 1750)             # banner rows (slide 1)
CONTACT_PX = 3                      # main's si_border_pore reach


def disp(g):
    """Display stretch = main's normalisation (1st-99.5th percentile)."""
    p1, p995 = np.percentile(g, [1, 99.5])
    return np.clip((g - p1) / max(p995 - p1, 1e-9), 0, 1)


def to_rgb(n):
    return np.repeat((n * 255.0)[..., None], 3, axis=2)


def tint(rgb, mask, col, a):
    rgb[mask] = rgb[mask] * (1 - a) + np.array(col, float) * a
    return rgb


def save(arr, name, scale=1.0):
    im = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8))
    if scale != 1.0:
        im = im.resize((int(im.width * scale), int(im.height * scale)),
                       Image.LANCZOS)
    p = os.path.join(ASSETS, name)
    im.save(p, optimize=True)
    return p


def overlay(n, pore, si, lab=None, edges=True):
    o = to_rgb(n)
    tint(o, pore, S.PORE_RGB, 0.72)
    tint(o, si, S.BRIGHT_RGB, 0.55)
    if lab is not None and edges:
        o[find_boundaries(lab, mode="inner")] = (35, 35, 35)
    return o


class Repo:
    def __init__(self, repo):
        self.repo = repo
        sys.path.insert(0, os.path.join(repo, "analysis"))
        import common as C          # main's own loader (read-only use)
        self.C = C
        self.locs = {r["image_id"]: r for r in C.find_locations(root=repo)}
        self.T = os.path.join(repo, "analysis", "outputs", "tables")

    def gray(self, iid, kind="bse"):
        rec = self.locs[iid]
        path = rec["bse"] if kind == "bse" else rec["inlens"] \
            if kind == "inlens" else rec["topo"]
        return self.C.load_gray(path)[0]

    def masks(self, iid):
        z = np.load(os.path.join(self.repo, "analysis", "outputs", "masks",
                                 f"{self.locs[iid]['batch']}_{iid}_masks.npz"))
        return z["pore"], z["silicon"], z["labels"]

    def table(self, name):
        return pd.read_csv(os.path.join(self.T, name))


# --------------------------------------------------------------------------
def hero(R, ann):
    g = R.gray(IMG)
    pore, si, lab = R.masks(IMG)
    y0, y1 = HERO_ROWS
    n = disp(g)[y0:y1]
    save(to_rgb(n), "hero.png", scale=0.5)
    P, Si, L = pore[y0:y1], si[y0:y1], lab[y0:y1]
    # callout targets: a large compact particle, a graphite interior point,
    # a large pore — chosen automatically from the masks
    props = [p for p in regionprops(L) if p.area > 2500 and p.solidity > 0.9
             and 1500 < p.centroid[1] < 3200 and 300 < p.centroid[0] < 1000]
    part = max(props, key=lambda p: p.area)
    gr = ~(P | Si)
    dg = ndi.distance_transform_edt(gr)
    dg[:, :4200] = 0
    dg[:, 5600:] = 0
    dg[:220] = 0
    dg[-220:] = 0
    gy, gx = np.unravel_index(np.argmax(dg), dg.shape)
    # a large pore in the left half, upper/middle rows (clear of the
    # bottom-band label); the arrow lands on its pixel nearest the centroid
    cc, nc = ndi.label(P)
    best, best_k = 0, None
    for p in regionprops(cc):
        cy_, cx_ = p.centroid
        if 700 < cx_ < 2600 and 250 < cy_ < 0.6 * P.shape[0] and \
                p.area > best:
            best, best_k = p.area, p.label
    pts = np.argwhere(cc == best_k)
    cy, cx = pts.mean(axis=0)
    py, px = pts[np.argmin(np.hypot(pts[:, 0] - cy, pts[:, 1] - cx))]
    ann["hero"] = dict(
        w=int(n.shape[1]), h=int(n.shape[0]), scale=0.5, image_id=IMG,
        rows=[int(y0), int(y1)],
        particle=[float(part.centroid[1]), float(part.centroid[0])],
        particle_diam_um=float(part.equivalent_diameter_area * 0.025),
        graphite=[float(gx), float(gy)],
        pore=[float(px), float(py)],
        um_per_px=0.025)


def segmentation_panels(R, ann):
    g = R.gray(IMG)
    pore, si, lab = R.masks(IMG)
    s, _, _ = R.C.normalise(g)                 # main: percentile + gauss 1.5
    seg = R.table("segment_info.csv").set_index("image_id").loc[IMG]
    t_lo, t_b = float(seg.t_lo), float(seg.t_bright)
    x0, y0, w, h = REGION
    sl = (slice(y0, y0 + h), slice(x0, x0 + w))
    raw = disp(g)
    save(to_rgb(raw[sl]), "seg_original.png", scale=0.6)
    th = to_rgb(s[sl])
    tint(th, s[sl] < t_lo, S.PORE_RGB, 0.72)
    tint(th, s[sl] > t_b, S.BRIGHT_RGB, 0.55)
    save(th, "seg_threshold.png", scale=0.6)
    save(overlay(raw[sl], pore[sl], si[sl], lab[sl]), "seg_overlay.png",
         scale=0.6)
    cx0, cy0, cw, ch = CLOSEUP
    csl = (slice(cy0, cy0 + ch), slice(cx0, cx0 + cw))
    save(to_rgb(raw[csl]), "closeup_original.png")
    save(overlay(raw[csl], pore[csl], si[csl], lab[csl]), "closeup_overlay.png")
    n_pieces = len(np.unique(lab[csl][si[csl]])) - (0 in lab[csl][si[csl]])
    # arrow targets inside the region (region pixel coordinates)
    Lr, Pr, Sr = lab[sl], pore[sl], si[sl]
    split = np.zeros_like(Sr)
    for dy, dx in ((0, 1), (1, 0)):
        a = Lr[:Lr.shape[0] - dy, :Lr.shape[1] - dx]
        b = Lr[dy:, dx:]
        m = (a != b) & (a > 0) & (b > 0)
        split[:m.shape[0], :m.shape[1]] |= m
    sp = np.argwhere(split)
    sp = sp[(sp[:, 1] > 0.55 * w) & (sp[:, 0] > 0.45 * h)] if len(sp) else sp
    sy, sx = sp[len(sp) // 2] if len(sp) else (h // 2, w // 2)
    cc, _ = ndi.label(Pr)
    sz = np.bincount(cc.ravel())
    sz[0] = 0
    pts = np.argwhere(cc == int(np.argmax(sz)))
    py, px = pts[len(pts) // 2]
    big = max((p for p in regionprops(Lr) if p.solidity > 0.85),
              key=lambda p: p.area)
    # histogram of the normalised image with the two cuts (whole image)
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    S.register_mpl_fonts()
    fig, ax = plt.subplots(figsize=(3.3, 1.55), dpi=300)
    hist, edges = np.histogram(s[::2, ::2], bins=256, range=(0, 1))
    cen = (edges[:-1] + edges[1:]) / 2
    ax.fill_between(cen, hist / hist.max(), color="#" + S.NAVY2, alpha=0.85,
                    lw=0)
    ax.axvspan(0, t_lo, color=np.array(S.PORE_RGB) / 255, alpha=0.22, lw=0)
    ax.axvspan(t_b, 1, color=np.array(S.BRIGHT_RGB) / 255, alpha=0.35, lw=0)
    for t, c in ((t_lo, S.PORE_RGB), (t_b, (170, 120, 0))):
        ax.axvline(t, color=np.array(c) / 255, lw=1.4)
    ax.set_xlim(0, 1)
    ax.set_ylim(0, 1.05)
    ax.set_yticks([])
    ax.set_xticks([0, 0.5, 1])
    ax.tick_params(labelsize=9, length=2)
    ax.set_xlabel("normalised brightness", fontsize=9.5, labelpad=1)
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    fig.tight_layout(pad=0.2)
    fig.savefig(os.path.join(ASSETS, "seg_histogram.png"), transparent=True)
    plt.close(fig)
    ann["seg"] = dict(
        region=list(REGION), closeup=list(CLOSEUP), image_id=IMG,
        w=int(w * 0.6), h=int(h * 0.6), scale=0.6, t_lo=t_lo, t_b=t_b,
        closeup_pieces=int(n_pieces), um_per_px=0.025,
        region_si=float(si[sl].mean()), region_pore=float(pore[sl].mean()),
        split=[float(sx), float(sy)], pore=[float(px), float(py)],
        particle=[float(big.centroid[1]), float(big.centroid[0])])


# --------------------------------------------------------------------------
def thumbs(R, ann):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    S.register_mpl_fonts()
    x0, y0 = 3900, 1000
    tiles = []
    for kind in ("bse", "inlens", "topo"):
        gg = R.gray(IMG, kind)
        tiles.append(to_rgb(disp(gg[y0:y0 + 520, x0:x0 + 300])))
        tiles.append(np.full((520, 14, 3), 255.0))
    save(np.concatenate(tiles[:-1], axis=1), "thumb_detectors.png", scale=0.8)
    pore, si, lab = R.masks(IMG)
    g = R.gray(IMG)
    sl = (slice(y0, y0 + 520), slice(x0 - 300, x0 + 600))
    save(overlay(disp(g)[sl], pore[sl], si[sl], lab[sl]), "thumb_segment.png",
         scale=0.6)

    def mini(w=1.9, h=1.07):
        fig, ax = plt.subplots(figsize=(w, h), dpi=320)
        for sp in ("top", "right"):
            ax.spines[sp].set_visible(False)
        for sp in ("left", "bottom"):
            ax.spines[sp].set_color("#" + S.GREY)
            ax.spines[sp].set_linewidth(0.6)
        ax.tick_params(labelsize=8, length=0, pad=1.5)
        ax.set_yticks([])
        return fig, ax

    def done(fig, name):
        fig.tight_layout(pad=0.15)
        fig.savefig(os.path.join(ASSETS, name), transparent=True)
        plt.close(fig)

    order = {"Batch_1": 0, "Batch_2": 1, "Batch_3": 2}
    rng = np.random.default_rng(1)

    def batch_x():
        return [0, 1, 2], ["B1", "B2", "B3"]

    q = R.table("quality_guards.csv")
    fig, ax = mini()
    for b, gq in q.groupby("batch"):
        x = order[b] + rng.uniform(-0.2, 0.2, len(gq))
        ax.scatter(x, gq.si_bulk_contrast, s=10,
                   c=["white" if f else "#" + S.BATCH[b] for f in gq.flagged],
                   edgecolors="#" + S.BATCH[b], linewidths=0.9, zorder=3)
    ax.axhline(2.8, color="#" + S.TEAL, lw=1, ls="--")
    ax.text(2.55, 2.55, "guard", fontsize=8, color="#" + S.TEAL, va="top",
            ha="right")
    ax.set_xticks(*batch_x())
    ax.set_ylim(1.6, 5.0)
    done(fig, "thumb_quality.png")

    F = R.table("features.csv")
    wide = F.pivot_table(index="image_id", columns="subset",
                         values="pore_frac")
    fig, ax = mini()
    ax.plot([6, 18], [6, 18], color="#" + S.RULE, lw=1)
    ax.scatter(wide["L"] * 100, wide["R"] * 100, s=8, color="#" + S.NAVY2,
               zorder=3)
    ax.set_xlim(6, 18)
    ax.set_ylim(6, 18)
    ax.set_xticks([])
    ax.set_xlabel("left half", fontsize=8, labelpad=1)
    ax.set_ylabel("right half", fontsize=8, labelpad=1)
    done(fig, "thumb_measure.png")

    full = F[F.subset == "full"]
    st = R.table("baseline_stats.csv").set_index("feature")
    fig, ax = mini()
    ax.axhspan(st.loc["pore_frac", "env_lo"] * 100,
               st.loc["pore_frac", "env_hi"] * 100,
               color="#" + S.BATCH["Batch_3"], alpha=0.13, lw=0)
    for b, gf in full.groupby("batch"):
        x = order[b] + rng.uniform(-0.2, 0.2, len(gf))
        ax.scatter(x, gf.pore_frac * 100, s=9, color="#" + S.BATCH[b],
                   zorder=3)
        ax.plot([order[b] - 0.3, order[b] + 0.3],
                [gf.pore_frac.mean() * 100] * 2, color="#" + S.NAVY, lw=1.3,
                zorder=4)
    ax.set_xticks(*batch_x())
    done(fig, "thumb_compare.png")

    P = R.table("loo_predictions_allfeatures.csv")
    fig, ax = mini()
    for b, gp in P.groupby("batch"):
        x = order[b] + rng.uniform(-0.2, 0.2, len(gp))
        ax.scatter(x, gp.dist / gp.threshold, s=9, color="#" + S.BATCH[b],
                   zorder=3)
    ax.axhline(1, color="#" + S.TEAL, lw=1, ls="--")
    ax.text(2.6, 1.25, "OUT", fontsize=8, color="#" + S.TEAL, ha="right",
            va="bottom")
    ax.text(2.6, 0.8, "IN", fontsize=8, color="#" + S.TEAL, ha="right",
            va="top")
    ax.set_yscale("log")
    ax.set_yticks([])
    ax.minorticks_off()
    ax.set_xticks(*batch_x())
    done(fig, "thumb_categorise.png")

    with open(os.path.join(R.T, "dfn_curves.pkl"), "rb") as f:
        curves = pickle.load(f)
    fig, ax = mini(1.9, 1.0)
    for b in ("Batch_1", "Batch_2", "Batch_3"):
        c = curves.get((b, "measured", 2.0))
        if c is not None:
            ax.plot(c["Q"], c["V_md"], color="#" + S.BATCH[b], lw=1.2)
    ax.set_xticks([])
    ax.set_xlabel("capacity", fontsize=8, labelpad=1)
    ax.set_ylabel("voltage", fontsize=8, labelpad=1)
    done(fig, "thumb_dfn.png")


# --------------------------------------------------------------------------
def marker_examples(R, ann):
    g = R.gray(IMG)
    pore, si, lab = R.masks(IMG)
    raw = disp(g)
    out = {}
    Pp = R.table("particles.csv")
    pe = Pp[Pp.image_id == IMG].set_index("label")

    # (a) particle size: a compact, isolated 2.5-4.5 um particle, crop
    # centred on it (10 x 6.75 um)
    w, h = 400, 270
    cands = []
    for p in regionprops(lab):
        d_um = p.equivalent_diameter_area * 0.025
        cy_, cx_ = p.centroid
        if 2.5 < d_um < 4.5 and p.solidity > 0.93 and \
                h < cy_ < lab.shape[0] - h and w < cx_ < lab.shape[1] - w:
            cands.append(p)
    part0 = max(cands, key=lambda p: p.solidity)
    x0 = int(part0.centroid[1] - w / 2)
    y0 = int(part0.centroid[0] - h / 2)
    sl = (slice(y0, y0 + h), slice(x0, x0 + w))
    o = overlay(raw[sl], pore[sl], si[sl], lab[sl], edges=True)
    save(o, "ex_size.png")
    L = lab[sl]
    part = [p for p in regionprops(L) if p.label == part0.label][0]
    cont = find_contours((L == part.label).astype(float), 0.5)[0]
    cont = cont[:: max(1, len(cont) // 80)]
    lab_id = int(part.label)
    out["size"] = dict(
        crop=[x0, y0, w, h], w=w, h=h,
        contour=[[float(c[1]), float(c[0])] for c in cont],
        centroid=[float(part.centroid[1]), float(part.centroid[0])],
        eq_diam_px=float(part.equivalent_diameter_area),
        eq_diam_um=float(pe.loc[lab_id, "diam_um"]),
        table_label=lab_id)

    # (b) visible pores: pores highlighted on the raw image
    x0, y0, w, h = 900, 980, 760, 520
    sl = (slice(y0, y0 + h), slice(x0, x0 + w))
    o = to_rgb(raw[sl])
    tint(o, pore[sl], S.PORE_RGB, 0.78)
    save(o, "ex_pores.png")
    cc, _ = ndi.label(pore[sl])
    sz = np.bincount(cc.ravel())
    sz[0] = 0
    k = int(np.argmax(sz))
    pts = np.argwhere(cc == k)
    py, px = pts[len(pts) // 2]
    out["pores"] = dict(crop=[x0, y0, w, h], w=w, h=h,
                        crop_pore_frac=float(pore[sl].mean()),
                        target=[float(px), float(py)])

    # (c) contact: boundary pixels <= 3 px from a pore cyan, others navy;
    # 250-nm ring (10 px) shaded. Boundary = main's definition
    # (extra_features: si & ~skimage binary_erosion(si)).
    from skimage.morphology import binary_erosion as sk_erosion
    d2p = ndi.distance_transform_edt(~pore)
    border = si & ~sk_erosion(si)
    near = border & (d2p <= CONTACT_PX)
    w, h = 700, 470
    w, h = 560, 376
    big = pe[pe.area_px > 900]
    best, best_xy = -1, None
    for yy in range(150, si.shape[0] - h - 150, 40):
        for xx in range(150, si.shape[1] - w - 150, 40):
            m = ((big.cx > xx + 40) & (big.cx < xx + w - 40) &
                 (big.cy > yy + 40) & (big.cy < yy + h - 40))
            nt = int((big.d_min_px[m] <= CONTACT_PX).sum())
            nn = int(m.sum()) - nt
            score = min(nt, nn) * 2 + int(m.sum()) * 0.2
            if nn >= 2 and nt >= 2 and score > best:
                best, best_xy = score, (xx, yy)
    x0, y0 = best_xy
    sl = (slice(y0, y0 + h), slice(x0, x0 + w))
    d_out = ndi.distance_transform_edt(~si)
    ring = (d_out > 0) & (d_out <= 10)
    o = to_rgb(raw[sl])
    tint(o, pore[sl], S.PORE_RGB, 0.72)
    tint(o, si[sl], S.BRIGHT_RGB, 0.45)
    tint(o, ring[sl] & ~pore[sl], (255, 255, 255), 0.35)
    bd = ndi.binary_dilation(border[sl] & ~near[sl], iterations=1) & si[sl]
    nd = ndi.binary_dilation(near[sl], iterations=3)
    o[bd] = S.FAR_RGB
    o[nd] = S.NEAR_RGB
    save(o, "ex_contact.png")
    pts = np.argwhere(near[sl])
    ty, tx = pts[np.argmin(np.hypot(pts[:, 0] - h * 0.5, pts[:, 1] - w * 0.5))]
    touch = pe.d_min_px <= CONTACT_PX
    whole_border = float(near.sum() / max(border.sum(), 1))
    out["contact"] = dict(
        crop=[x0, y0, w, h], w=w, h=h, target=[float(tx), float(ty)],
        n_particles=int(len(pe)), n_touch=int(touch.sum()),
        number_share=float(touch.mean()),
        area_share=float(pe.area_px[touch].sum() / pe.area_px.sum()),
        boundary_share=whole_border,
        ring_porosity=float(pore[ring].mean()))

    # (d) graphite alignment: sample horizontal & vertical chords in grey
    x0, y0, w, h = 5000, 900, 760, 520
    sl = (slice(y0, y0 + h), slice(x0, x0 + w))
    gr = ~(pore | si)
    o = to_rgb(raw[sl])
    tint(o, pore[sl], S.PORE_RGB, 0.6)
    tint(o, si[sl], S.BRIGHT_RGB, 0.45)
    save(o, "ex_align.png")
    G = gr[sl]

    def runs(line):
        d = np.diff(np.r_[0, line.astype(np.int8), 0])
        st, en = np.nonzero(d == 1)[0], np.nonzero(d == -1)[0]
        return list(zip(st, en))

    hseg, vseg = [], []
    for yy in (120, 260, 400):
        for a, b in runs(G[yy]):
            if b - a > 25 and a > 0 and b < w:
                hseg.append([float(a), float(yy), float(b), float(yy)])
    for xx in (150, 380, 610):
        for a, b in runs(G[:, xx]):
            if b - a > 25 and a > 0 and b < h:
                vseg.append([float(xx), float(a), float(xx), float(b)])
    out["align"] = dict(crop=[x0, y0, w, h], w=w, h=h, hseg=hseg, vseg=vseg)
    ann["examples"] = out


def slide6_data(R):
    F = R.table("features.csv")
    full = F[F.subset == "full"][["batch", "image_id", "pore_frac",
                                  "silicon_frac", "bse_bulk_texture"]]
    q = R.table("quality_guards.csv")[["image_id", "noise_mad", "flagged"]]
    full = full.merge(q, on="image_id")
    full.to_csv(os.path.join(DECK, "provenance", "slide6_data.csv"),
                index=False)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()
    os.makedirs(ASSETS, exist_ok=True)
    R = Repo(os.path.abspath(a.repo))
    ann = {}
    hero(R, ann)
    segmentation_panels(R, ann)
    thumbs(R, ann)
    marker_examples(R, ann)
    slide6_data(R)
    with open(os.path.join(ASSETS, "annotations.json"), "w") as f:
        json.dump(ann, f, indent=1)
    print("assets written:", sorted(os.listdir(ASSETS)))


if __name__ == "__main__":
    main()
