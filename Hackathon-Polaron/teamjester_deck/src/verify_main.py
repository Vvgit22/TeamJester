"""Verify TeamJester main's saved outputs against main's own code.

Run with an environment matching main's .devin/blueprint.yaml (Python 3.10;
see README.md). Nothing in the main worktree is modified: the analysis
package is copied to a scratch directory and the dataset is symlinked.

    python src/verify_main.py --repo /path/to/teamjester_main_<sha> \
                              --scratch /tmp/tj_repro --out provenance

Checks
  1. segmentation: re-segment every BSE image (full frame) with
     segment.segment() and compare pore/silicon masks + particle labels with
     the committed outputs/masks/*.npz.
  2. features: recompute features.compute(rec, "full") from the committed
     masks and compare every column of the committed features.csv.
  3. statistics: run run_all.stage_stats() on the committed features.csv and
     compare every regenerated table with the committed one.
"""
import argparse
import json
import os
import shutil
import subprocess
import sys
from multiprocessing import Pool

import numpy as np
import pandas as pd

STATS_TABLES = [
    "repeatability.csv", "dropped_features.csv", "baseline_stats.csv",
    "baseline_stats_noflag.csv", "deltas.csv", "deltas_noflag.csv",
    "deltas_dropped.csv", "loo_predictions.csv",
    "loo_predictions_allfeatures.csv", "loo_predictions_safe.csv",
    "loo_predictions_safe_noflag.csv", "loo_confusion_allfeatures.csv",
    "loo_confusion_safe.csv", "loo_confusion_safe_noflag.csv",
    "images_needed.csv", "images_needed_safe.csv", "loo_summary.csv"]


def prepare(repo, scratch):
    ana = os.path.join(scratch, "analysis")
    if os.path.isdir(ana):
        shutil.rmtree(ana)
    os.makedirs(scratch, exist_ok=True)
    shutil.copytree(os.path.join(repo, "analysis"), ana)
    link = os.path.join(scratch, "Hackathon-Polaron")
    if not os.path.exists(link):
        os.symlink(os.path.join(repo, "Hackathon-Polaron"), link)
    committed = os.path.join(scratch, "committed_tables")
    if os.path.isdir(committed):
        shutil.rmtree(committed)
    shutil.copytree(os.path.join(ana, "outputs", "tables"), committed)
    return ana, committed


def _seg_one(rec):
    import common as C
    import segment as S
    g, _ = C.load_gray(rec["bse"])
    r = S.segment(g, S.load_detector(rec))
    z = C.load_masks(rec["batch"], rec["image_id"])
    row = dict(batch=rec["batch"], image_id=rec["image_id"])
    for k in ("pore", "silicon"):
        a, b = r[k], z[k]
        row[f"{k}_same_shape"] = a.shape == b.shape
        row[f"{k}_pixel_agreement"] = float((a == b).mean()) \
            if a.shape == b.shape else np.nan
        row[f"{k}_frac_new"] = float(a.mean())
        row[f"{k}_frac_committed"] = float(b.mean())
    row["n_particles_new"] = int(r["labels"].max())
    row["n_particles_committed"] = int(z["labels"].max())
    row["labels_identical"] = bool(np.array_equal(r["labels"], z["labels"]))
    return row


def _feat_one(rec):
    import features as FT
    fe, _, _ = FT.compute(rec, "full")
    fe.update(batch=rec["batch"], image_id=rec["image_id"])
    return fe


def run_checks(ana, committed, out, nproc):
    sys.path.insert(0, ana)
    os.chdir(ana)
    import common as C
    locs = C.find_locations()
    with Pool(nproc) as pool:
        seg = pd.DataFrame(pool.map(_seg_one, locs))
        feats = pd.DataFrame(pool.map(_feat_one, locs))
    seg.to_csv(os.path.join(out, "verify_segmentation.csv"), index=False)

    F0 = pd.read_csv(os.path.join(committed, "features.csv"))
    F0 = F0[F0.subset == "full"].set_index("image_id")
    F1 = feats.set_index("image_id").loc[F0.index]
    rows = []
    for c in F0.columns:
        if c in ("batch", "subset"):
            continue
        a = pd.to_numeric(F0[c], errors="coerce").astype(float)
        b = pd.to_numeric(F1[c], errors="coerce").astype(float) \
            if c in F1 else pd.Series(np.nan, index=F0.index)
        both = a.notna() & b.notna()
        rel = ((a - b).abs() / a.abs().clip(lower=1e-12))[both]
        rows.append(dict(feature=c, n_compared=int(both.sum()),
                         nan_pattern_equal=bool((a.isna() == b.isna()).all()),
                         max_abs_diff=float((a - b).abs()[both].max())
                         if both.any() else np.nan,
                         max_rel_diff=float(rel.max()) if both.any() else np.nan))
    fv = pd.DataFrame(rows)
    fv["match_1e-6"] = fv.nan_pattern_equal & (fv.max_rel_diff.fillna(0) < 1e-6)
    fv.to_csv(os.path.join(out, "verify_features.csv"), index=False)
    extra = [c for c in F1.columns if c not in F0.columns
             and c not in ("batch", "image_id")]

    import run_all
    run_all.stage_stats()
    trows = []
    for t in STATS_TABLES:
        a = pd.read_csv(os.path.join(C.TABLE_DIR, t))
        b = pd.read_csv(os.path.join(committed, t))
        if a.shape != b.shape:
            trows.append(dict(table=t, status="shape differs",
                              columns_differing=f"{a.shape} vs {b.shape}"))
            continue
        bad = []
        for c in a.columns:
            if pd.api.types.is_numeric_dtype(a[c]) and \
                    pd.api.types.is_numeric_dtype(b[c]):
                if not np.allclose(a[c].astype(float), b[c].astype(float),
                                   rtol=1e-9, atol=1e-12, equal_nan=True):
                    bad.append(c)
            elif not (a[c].astype(str) == b[c].astype(str)).all():
                bad.append(c)
        trows.append(dict(table=t, status="identical" if not bad else
                          "differs", columns_differing="|".join(bad)))
    tv = pd.DataFrame(trows)
    tv.to_csv(os.path.join(out, "verify_stats_tables.csv"), index=False)
    shutil.copy(os.path.join(C.TABLE_DIR, "loo_summary.csv"),
                os.path.join(out, "loo_summary_regenerated.csv"))
    shutil.copy(os.path.join(C.TABLE_DIR, "deltas.csv"),
                os.path.join(out, "deltas_regenerated.csv"))

    summary = dict(
        n_images=len(locs),
        segmentation_pore_identical=int((seg.pore_pixel_agreement == 1).sum()),
        segmentation_silicon_identical=int(
            (seg.silicon_pixel_agreement == 1).sum()),
        segmentation_labels_identical=int(seg.labels_identical.sum()),
        min_pore_agreement=float(seg.pore_pixel_agreement.min()),
        min_silicon_agreement=float(seg.silicon_pixel_agreement.min()),
        features_compared=int(len(fv)),
        features_matching=int(fv["match_1e-6"].sum()),
        features_not_matching=fv.loc[~fv["match_1e-6"], "feature"].tolist(),
        extra_feature_columns_from_current_code=extra,
        stats_tables=tv.set_index("table")["status"].to_dict())
    with open(os.path.join(out, "verify_summary.json"), "w") as f:
        json.dump(summary, f, indent=2)
    return summary


def environment(repo):
    def sh(cmd):
        return subprocess.run(cmd, cwd=repo, capture_output=True,
                              text=True).stdout.strip()
    import numpy, scipy, skimage, pandas, sklearn, tifffile
    return dict(
        repo=repo, head=sh(["git", "rev-parse", "HEAD"]),
        head_date=sh(["git", "log", "-1", "--format=%cI"]),
        status_clean=sh(["git", "status", "--porcelain"]) == "",
        python=sys.version.split()[0], numpy=numpy.__version__,
        scipy=scipy.__version__, skimage=skimage.__version__,
        pandas=pandas.__version__, sklearn=sklearn.__version__,
        tifffile=tifffile.__version__)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--repo", required=True)
    ap.add_argument("--scratch", default="/tmp/tj_repro")
    ap.add_argument("--out", default="provenance")
    ap.add_argument("--nproc", type=int, default=6)
    a = ap.parse_args()
    out = os.path.abspath(a.out)
    os.makedirs(out, exist_ok=True)
    env = environment(os.path.abspath(a.repo))
    with open(os.path.join(out, "verify_environment.json"), "w") as f:
        json.dump(env, f, indent=2)
    ana, committed = prepare(os.path.abspath(a.repo), os.path.abspath(a.scratch))
    print(json.dumps(run_checks(ana, committed, out, a.nproc), indent=2))
