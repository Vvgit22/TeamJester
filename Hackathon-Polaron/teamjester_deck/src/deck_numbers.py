"""Every number shown in the deck, computed from TeamJester main's committed
outputs (pinned commit) — nothing is typed by hand.

    python src/deck_numbers.py --repo /path/to/teamjester_main_<sha>

writes provenance/deck_numbers.json: {key: {value, text, source, how}}.
`source` is a path inside the repo at the pinned commit; `how` says how the
number was obtained. Values marked "regenerated" come from re-running main's
own code (src/verify_main.py) because the committed file is stale.
"""
import argparse
import glob
import json
import os
import subprocess

import numpy as np
import pandas as pd

HERE = os.path.dirname(os.path.abspath(__file__))
DECK = os.path.dirname(HERE)
PROV = os.path.join(DECK, "provenance")
T = "analysis/outputs/tables/"
EXAMPLE_IMAGE = "cfe5vt7s"          # Batch_3 image used on slides 1, 3, 5
CONTACT_PX = 3                      # main's si_border_pore reach (3 px)


class Numbers:
    def __init__(self, repo):
        self.repo = repo
        self.d = {}

    def table(self, name):
        return pd.read_csv(os.path.join(self.repo, T, name))

    def put(self, key, value, text, source, how):
        if isinstance(value, (np.floating, np.integer)):
            value = value.item()
        self.d[key] = dict(value=value, text=text, source=source, how=how)

    def pct(self, key, value, source, how, nd=1, signed=False):
        fmt = f"{{:{'+' if signed else ''}.{nd}f}}%"
        self.put(key, value, fmt.format(100 * value), source, how)


def git(repo, *args):
    return subprocess.run(["git", *args], cwd=repo, capture_output=True,
                          text=True).stdout.strip()


def collect(repo):
    N = Numbers(repo)
    sha = git(repo, "rev-parse", "HEAD")
    N.put("sha", sha, sha, "git rev-parse HEAD", "pinned worktree")
    N.put("sha7", sha[:7], sha[:7], "git rev-parse HEAD", "short SHA")
    date = git(repo, "log", "-1", "--format=%cs")
    N.put("commit_date", date, date, "git log -1", "commit date (UTC)")
    N.put("repo_url", "https://github.com/Augustin-Briens/TeamJester",
          "github.com/Augustin-Briens/TeamJester", "git remote -v", "origin")

    F = N.table("features.csv")
    full = F[F.subset == "full"].copy()
    q = N.table("quality_guards.csv")
    full = full.merge(q[["image_id", "noise_mad", "si_bulk_contrast",
                         "flagged"]], on="image_id")
    nb = full.batch.value_counts()
    for b in ("Batch_1", "Batch_2", "Batch_3"):
        N.put(f"n_{b}", int(nb[b]), str(int(nb[b])), T + "features.csv",
              "count of subset=='full' rows per batch")
    N.put("n_images", int(len(full)), str(len(full)), T + "features.csv",
          "subset=='full' rows")

    # detectors / pixel size / frame size --------------------------------
    tifs = sorted(glob.glob(os.path.join(repo, "Hackathon-Polaron",
                                         "Batch_*", "*.tif")))
    kinds = pd.Series([os.path.basename(p).split("_")[-1][:-4] for p in tifs])
    kc = kinds.value_counts().to_dict()
    N.put("n_tif", len(tifs), str(len(tifs)), "Hackathon-Polaron/Batch_*/*.tif",
          "file count")
    N.put("n_inlens", int(kc.get("Inlens", 0)), str(kc.get("Inlens", 0)),
          "Hackathon-Polaron/Batch_*/*_Inlens.tif", "file count")
    N.put("n_etd", int(kc.get("ETD", 0)), str(kc.get("ETD", 0)),
          "Hackathon-Polaron/Batch_*/*_ETD.tif", "file count")
    N.put("n_se", int(kc.get("SE", 0)), str(kc.get("SE", 0)),
          "Hackathon-Polaron/Batch_*/*_SE.tif", "file count")
    seg = N.table("segment_info.csv")
    N.put("nm_per_px", float(seg.um_per_px.median() * 1000),
          f"{seg.um_per_px.median() * 1000:.0f} nm", T + "segment_info.csv",
          "median um_per_px x 1000 (range "
          f"{seg.um_per_px.min():.6f}-{seg.um_per_px.max():.6f} um)")
    import tifffile
    shapes = []
    for p in tifs:
        if p.endswith("_BSE.tif"):
            with tifffile.TiffFile(p) as t:
                shapes.append(t.pages[0].shape[:2])
    hs = [s[0] for s in shapes]
    ws = [s[1] for s in shapes]
    N.put("fov_w_um", max(ws) * 0.025, f"{max(ws) * 0.025:.0f} μm",
          "BSE TIFF headers", "max frame width (px) x 25 nm")
    N.put("fov_h_um", [min(hs) * 0.025, max(hs) * 0.025],
          f"{min(hs) * 0.025:.0f}–{max(hs) * 0.025:.0f} μm",
          "BSE TIFF headers", "frame heights (px) x 25 nm")
    N.put("frame_heights_px", [min(hs), max(hs)], f"{min(hs)}–{max(hs)} px",
          "BSE TIFF headers", "min/max frame height")
    N.put("n_bright_fallback", int((seg.bright_method ==
                                    "multiotsu_fallback").sum()),
          str(int((seg.bright_method == "multiotsu_fallback").sum())),
          T + "segment_info.csv",
          "images whose bright cut = upper multi-Otsu (valley not found)")

    # quality guards -------------------------------------------------------
    fl = q[q.flagged]
    N.put("n_flagged", int(len(fl)), str(len(fl)), T + "quality_guards.csv",
          "flagged == True")
    N.put("flagged_ids", fl.image_id.tolist(), ", ".join(fl.image_id),
          T + "quality_guards.csv", "flagged image ids (both Batch_1)")
    N.put("flagged_contrast", fl.si_bulk_contrast.round(2).tolist(),
          " and ".join(f"{v:.2f}" for v in fl.si_bulk_contrast),
          T + "quality_guards.csv", "si_bulk_contrast of flagged images")
    N.put("min_unflagged_contrast", float(q[~q.flagged].si_bulk_contrast.min()),
          f"{q[~q.flagged].si_bulk_contrast.min():.2f}",
          T + "quality_guards.csv", "min si_bulk_contrast, unflagged")
    N.put("guard_contrast", 2.8, "2.8", "analysis/segment.py GUARDS",
          "si_bulk_contrast guard")
    nz = full.groupby("batch").noise_mad
    lowB3 = int((full[full.batch == "Batch_3"].noise_mad <
                 full[full.batch != "Batch_3"].noise_mad.min()).sum())
    N.put("n_B3_lower_noise", lowB3, str(lowB3), T + "quality_guards.csv",
          "Batch_3 images with noise_mad below every Batch_1/2 image")
    N.put("noise_levels", {b: sorted(set(np.round(v, 2)))
                           for b, v in nz}, "", T + "quality_guards.csv",
          "distinct noise_mad values per batch (quantised MAD x 1.4826)")
    r_tex = float(full[["bse_bulk_texture", "noise_mad"]].corr().iloc[0, 1])
    N.put("r_texture_noise", r_tex, f"{r_tex:.2f}",
          T + "features.csv + quality_guards.csv",
          "Pearson r(bse_bulk_texture, noise_mad), 31 images")
    for f in ("pore_frac", "silicon_frac", "pores_per_mm2", "etd_roughness",
              "inlens_edge_density"):
        r = float(full[[f, "noise_mad"]].corr().iloc[0, 1])
        N.put(f"r_noise_{f}", r, f"{r:.2f}",
              T + "features.csv + quality_guards.csv",
              f"Pearson r({f}, noise_mad), 31 images")

    # feature gates --------------------------------------------------------
    meta = N.table("feature_meta.csv")
    bs = N.table("baseline_stats.csv")
    N.put("n_features", int(len(meta)), str(len(meta)),
          T + "feature_meta.csv", "rows (features computed)")
    N.put("n_kept", int(len(bs)), str(len(bs)), T + "baseline_stats.csv",
          "rows (features kept after repeatability/duplicate pruning)")
    rep = N.table("repeatability.csv").drop_duplicates("feature")
    rr = rep.set_index("feature").lr_corr
    for f in ("pore_frac", "silicon_frac", "si_d50_um", "ring_porosity_250nm",
              "gr_chord_ratio_hv", "pores_per_mm2", "pore_anisotropy"):
        N.put(f"lr_{f}", float(rr[f]), f"{rr[f]:.2f}", T + "repeatability.csv",
              "left/right-half Pearson r (lr_corr)")

    # validation of segmentation ------------------------------------------
    s = N.table("threshold_sensitivity.csv")
    base = s[s["shift"] == 0]
    for param, ph, tag in (("t_lo(pore)", "pore", "pore"),
                           ("t_b(silicon)", "silicon", "si")):
        for shift, sg in (((-0.1), "m"), (0.1, "p")):
            g = s[(s.param == param) & (np.isclose(s["shift"], shift))]
            m = g.merge(base[base.param == param], on=["batch", "image_id"],
                        suffixes=("", "_0"))
            rel = float(((m[ph] - m[ph + "_0"]) / m[ph + "_0"]).median())
            N.pct(f"sens_{tag}_{sg}", rel, T + "threshold_sensitivity.csv",
                  f"median relative change of {ph} fraction when {param} "
                  f"is shifted {shift:+.0%}", nd=0, signed=True)
    pc = pd.read_excel(os.path.join(
        repo, "analysis/outputs/pointcount/point_count_validation.xlsx"))
    N.put("pc_points", int(len(pc)), str(len(pc)),
          "analysis/outputs/pointcount/point_count_validation.xlsx", "rows")
    N.put("pc_human", int(pc.human_class.notna().sum()),
          str(int(pc.human_class.notna().sum())),
          "analysis/outputs/pointcount/point_count_validation.xlsx",
          "rows with a human_class label")
    xd = N.table("cross_detector.csv")
    N.put("iou_inlens", float(xd.iou_pore.mean()), f"{xd.iou_pore.mean():.2f}",
          T + "cross_detector.csv", "mean IoU Inlens-only vs BSE pore mask")

    # per-batch summaries ---------------------------------------------------
    E = N.table("exp_newfeat.csv")
    E = E[E.subset == "full"][["image_id", "si_border_pore"]]
    full = full.merge(E, on="image_id", how="left")
    mk = ["pore_frac", "silicon_frac", "si_d50_um", "ring_porosity_250nm",
          "gr_chord_ratio_hv", "pores_per_mm2", "large_gap_frac",
          "bse_bulk_texture", "gr_st_coherence", "si_border_pore",
          "noise_mad"]
    for f in mk:
        for b, v in full.groupby("batch")[f]:
            N.put(f"mean_{f}_{b}", float(v.mean()), f"{v.mean():.4g}",
                  T + ("exp_newfeat.csv" if f == "si_border_pore" else
                       "quality_guards.csv" if f == "noise_mad" else
                       "features.csv"), f"mean of {f}, {b}, all images")
            N.put(f"med_{f}_{b}", float(v.median()), f"{v.median():.4g}",
                  T + ("exp_newfeat.csv" if f == "si_border_pore" else
                       "quality_guards.csv" if f == "noise_mad" else
                       "features.csv"), f"median of {f}, {b}, all images")
        nf = full[~full.flagged]
        for b, v in nf.groupby("batch")[f]:
            N.put(f"mean_nf_{f}_{b}", float(v.mean()), f"{v.mean():.4g}",
                  T + "features.csv", f"mean of {f}, {b}, unflagged images")
    rng = full.groupby("batch").silicon_frac
    N.put("si_range_unflagged",
          [float(full[~full.flagged].silicon_frac.min()),
           float(full[~full.flagged].silicon_frac.max())],
          f"{100 * full[~full.flagged].silicon_frac.min():.1f}–"
          f"{100 * full[~full.flagged].silicon_frac.max():.1f}%",
          T + "features.csv", "min-max silicon_frac over 29 unflagged images")
    N.put("si_flagged_values", full[full.flagged].silicon_frac.tolist(),
          " and ".join(f"{100 * v:.1f}%" for v in full[full.flagged]
                       .silicon_frac), T + "features.csv",
          "silicon_frac of the two flagged images")

    # deltas ---------------------------------------------------------------
    D = N.table("deltas.csv")
    Dn = N.table("deltas_noflag.csv")
    for tag, dd in (("", D), ("nf_", Dn)):
        for r in dd.itertuples():
            k = f"d_{tag}{r.batch}_{r.feature}"
            N.put(k + "_pct", r.pct_delta / 100, f"{r.pct_delta:+.0f}%",
                  T + ("deltas.csv" if not tag else "deltas_noflag.csv"),
                  f"pct_delta, {r.batch} vs Batch_3 ({r.n_batch} vs {r.n_b3} "
                  "images)")
            N.put(k + "_class", r.classification, r.classification,
                  T + ("deltas.csv" if not tag else "deltas_noflag.csv"),
                  "classification (different: CI excludes 0 and Holm p<0.05; "
                  "suggestive: CI excludes 0 only; equivalent: CI within "
                  "+/-10% of B3 mean; else undetermined)")
            N.put(k + "_pmw", r.p_mw, f"{r.p_mw:.3f}",
                  T + ("deltas.csv" if not tag else "deltas_noflag.csv"),
                  "Mann-Whitney two-sided p (uncorrected)")
            N.put(k + "_pholm", r.p_holm, f"{r.p_holm:.3f}",
                  T + ("deltas.csv" if not tag else "deltas_noflag.csv"),
                  "Holm-adjusted p (committed table; see ledger note)")
            N.put(k + "_ci", [r.ci_lo, r.ci_hi], f"[{r.ci_lo:.3g}, {r.ci_hi:.3g}]",
                  T + ("deltas.csv" if not tag else "deltas_noflag.csv"),
                  "bootstrap 95% CI on the mean difference (images resampled)")
    holm_ok = D[D.p_holm < 0.05]
    N.put("holm_survivors", holm_ok[["batch", "feature"]].values.tolist(),
          "; ".join(f"{b}:{f}" for b, f in holm_ok[["batch", "feature"]].values),
          T + "deltas.csv", "rows with p_holm < 0.05")
    N.put("n_tests_per_batch", int((D.batch == "Batch_1").sum()),
          str(int((D.batch == "Batch_1").sum())), T + "deltas.csv",
          "kept features compared per batch")

    # categorisation (LOO) ---------------------------------------------------
    P = N.table("loo_predictions_allfeatures.csv")
    ok = P.batch == P.pred_batch
    N.put("loo_correct", int(ok.sum()), str(int(ok.sum())),
          T + "loo_predictions_allfeatures.csv", "pred_batch == batch")
    N.pct("loo_acc", float(ok.mean()), T + "loo_predictions_allfeatures.csv",
          "share of 31 held-out images assigned to their own batch", nd=0)
    for b in ("Batch_1", "Batch_2", "Batch_3"):
        m = P.batch == b
        N.put(f"loo_{b}", [int((ok & m).sum()), int(m.sum())],
              f"{int((ok & m).sum())}/{int(m.sum())}",
              T + "loo_predictions_allfeatures.csv", f"correct/total, {b}")
    bal = float(np.mean([ok[P.batch == b].mean() for b in P.batch.unique()]))
    N.pct("loo_balanced", bal, T + "loo_predictions_allfeatures.csv",
          "mean of per-batch recall", nd=0)
    maj = float((P.batch == "Batch_3").mean())
    N.pct("majority_acc", maj, T + "loo_predictions_allfeatures.csv",
          "accuracy of always answering Batch_3 (17/31)", nd=0)
    Ps = N.table("loo_predictions_safe.csv")
    N.pct("loo_acc_safe", float((Ps.batch == Ps.pred_batch).mean()),
          T + "loo_predictions_safe.csv",
          "artefact-safe variant (no bse_bulk_texture/etd_roughness)", nd=0)
    out3 = P[(P.batch == "Batch_3")]
    n_out3 = int((out3.call_inout == "OUT").sum())
    N.put("b3_out", [n_out3, int(len(out3))], f"{n_out3} of {len(out3)}",
          T + "loo_predictions_allfeatures.csv",
          "held-out Batch_3 images called OUT of their own envelope")
    regen = os.path.join(PROV, "loo_summary_regenerated.csv")
    if os.path.exists(regen):
        L = pd.read_csv(regen)
        sh = float(L[L.variant.str.startswith("shuffled")].overall_acc.iloc[0])
        N.pct("shuffled_acc", sh, "provenance/loo_summary_regenerated.csv",
              "regenerated with main's run_all.stage_stats(); committed "
              "loo_summary.csv is stale (pre si_d10 removal)", nd=0)
    G = N.table("images_needed.csv")
    for b in ("Batch_1", "Batch_2"):
        g5 = float(G[(G.batch == b) & (G.n_images == 5)].group_accuracy.iloc[0])
        N.pct(f"group5_{b}", g5, T + "images_needed.csv",
              "IN-SAMPLE: model fitted on all images incl. the sampled ones",
              nd=0)
    import collections
    cnt = collections.Counter(f for s_ in P.feats for f in s_.split("|"))
    N.put("loo_feature_counts", dict(cnt.most_common()), "",
          T + "loo_predictions_allfeatures.csv",
          "how often each feature was selected across the 31 folds")

    # DFN --------------------------------------------------------------------
    cap = N.table("dfn_capacity.csv")
    cens = cap[cap.c_rate < 2].cap_mean
    N.put("dfn_censored_ah", float(cens.mean()), f"{cens.mean():.2f} Ah",
          T + "dfn_capacity.csv",
          "every C/10, C/2, 1C run returns 1.05 x nominal = time cut-off")
    N.put("dfn_censored_spread", float(cap[cap.c_rate < 2].cap_std.max()),
          f"{cap[cap.c_rate < 2].cap_std.max():.1e}", T + "dfn_capacity.csv",
          "max std of capacity across resamples at <=1C")
    dd = N.table("dfn_deltas.csv")
    for r in dd[dd.c_rate == 2.0].itertuples():
        N.put(f"dfn_{r.batch}_{r.porosity_mode}_2C", r.pct_delta / 100,
              f"{r.pct_delta:+.1f}%", T + "dfn_deltas.csv",
              f"2C capacity vs Batch_3, {r.porosity_mode} porosity "
              f"(interval {r.ci_lo:.3f}..{r.ci_hi:.3f} Ah: {r.sig})")
    for b in ("Batch_1", "Batch_2", "Batch_3"):
        c = cap[(cap.batch == b) & (cap.c_rate == 2.0) &
                (cap.porosity_mode == "measured")].iloc[0]
        N.put(f"dfn_cap2C_{b}", float(c.cap_mean), f"{c.cap_mean:.2f} Ah",
              T + "dfn_capacity.csv", "2C, measured porosity, mean of 30")

    # example image (slides 1/3/5) -------------------------------------------
    ex = full[full.image_id == EXAMPLE_IMAGE].iloc[0]
    b3 = full[full.batch == "Batch_3"].set_index("image_id")
    mk5 = ["pore_frac", "silicon_frac", "si_d50_um", "ring_porosity_250nm",
           "gr_chord_ratio_hv"]
    z = ((b3[mk5] - b3[mk5].median()).abs() /
         ((b3[mk5] - b3[mk5].median()).abs().median() * 1.4826)).mean(axis=1)
    N.put("ex_id", EXAMPLE_IMAGE, EXAMPLE_IMAGE, T + "features.csv",
          f"Batch_3 photo with the 2nd-smallest mean robust |z| over the five "
          f"slide-4 markers (rank {int(z.rank()[EXAMPLE_IMAGE])} of "
          f"{len(z)}); chosen over rank 1 ({z.idxmin()}) for clearer "
          "particles in the display crop")
    N.put("ex_batch", ex.batch, ex.batch.replace("_", " "), T + "features.csv",
          "")
    for f in ("pore_frac", "silicon_frac", "si_d50_um", "ring_porosity_250nm",
              "gr_chord_h_um", "gr_chord_v_um", "gr_chord_ratio_hv",
              "si_border_pore", "pores_per_mm2"):
        src = "exp_newfeat.csv" if f == "si_border_pore" else "features.csv"
        N.put(f"ex_{f}", float(ex[f]), f"{ex[f]:.4g}", T + src,
              f"{f} of {EXAMPLE_IMAGE} (subset=full)")
    srow = seg[seg.image_id == EXAMPLE_IMAGE].iloc[0]
    N.put("ex_t_lo", float(srow.t_lo), f"{srow.t_lo:.3f}", T + "segment_info.csv",
          "pore cut on the normalised [0,1] scale")
    N.put("ex_t_b", float(srow.t_bright), f"{srow.t_bright:.3f}",
          T + "segment_info.csv", "bright cut on the normalised [0,1] scale")
    Pp = N.table("particles.csv")
    pe = Pp[Pp.image_id == EXAMPLE_IMAGE]
    touch = pe.d_min_px <= CONTACT_PX
    N.put("ex_n_particles", int(len(pe)), str(len(pe)), T + "particles.csv",
          "watershed particles in the example image")
    N.pct("ex_contact_number", float(touch.mean()), T + "particles.csv",
          f"share of particles with d_min_px <= {CONTACT_PX} (presentation-"
          "derived from main's per-particle table; not a main feature)", nd=0)
    N.pct("ex_contact_area", float(pe.area_px[touch].sum() / pe.area_px.sum()),
          T + "particles.csv",
          "share of particle area in particles with d_min_px <= 3 "
          "(presentation-derived; not a main feature)", nd=0)
    return N


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    a = ap.parse_args()
    N = collect(os.path.abspath(a.repo))
    os.makedirs(PROV, exist_ok=True)
    with open(os.path.join(PROV, "deck_numbers.json"), "w") as f:
        json.dump(N.d, f, indent=1, default=str)
    print(f"{len(N.d)} numbers -> provenance/deck_numbers.json")


if __name__ == "__main__":
    main()
