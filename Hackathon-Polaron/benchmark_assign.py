"""benchmark_assign.py — predeclared classifier benchmark on the 31
labelled crops. No tuning, no model search: nearest-batch-centroid on
robust z-scores fit inside each training fold.

Feature sets (predeclared):
  envelope      : the frozen 9-feature envelope coverage rule (historical
                  baseline — reproduced from assign_new_images.py)
  fractions     : area fractions only
  +clustering   : fractions + Clark-Evans R + patchiness
  +correlation  : + corrected contact/corr markers
  +orientation  : + pore orientation S
  majority      : always Batch_3
  acq_signature : acquisition signature only (session detector — the
                  control that must be beaten to claim material signal)

Protocols: leave-one-image-out and leave-inferred-group-out.
Outputs: benchmark_results.csv + printed summary (accuracy, balanced
accuracy = mean per-class recall, confusion, coverage).
"""
import os
import sys

import numpy as np
import pandas as pd

ENVELOPE_9 = ["si_candidate_frac", "uncertain_bright_frac", "si_d50_um",
              "si_d90_um", "si_clustering_R", "pore_frac",
              "pores_per_mpx", "pores_per_mpx_noise_adj", "pore_anisotropy"]
FRACTIONS = ["pore_frac", "si_candidate_frac", "uncertain_bright_frac",
             "bright_frac_raw"]
CLUSTER = ["si_clustering_R"]
CORR = ["si_contact_area_frac", "si_enclosed_share", "si_patchiness",
        "si_sv_um_inv", "pore_largest_region_frac"]
ORIENT = ["obj_pore_aw_s_dir_2d", "obj_pore_aw_s_x_2d", "tex_all_s_dir_2d"]
ACQ = ["noise_mad", "sharpness_lapvar", "img_p50", "img_p1"]
BATCHES = ["Batch_1", "Batch_2", "Batch_3"]


def load_table() -> pd.DataFrame:
    f = pd.read_csv("validated_comparison/per_image_features.csv")
    m = pd.read_csv("dfn_output_v2/markers_all.csv")[
        ["image_id", "si_contact_area_frac", "si_enclosed_share",
         "si_patchiness", "si_sv_um_inv", "pore_largest_region_frac"]]
    o = pd.read_csv("orientation_analysis/orientation_features.csv")[
        ["image_id", "obj_pore_aw_s_dir_2d", "obj_pore_aw_s_x_2d",
         "tex_all_s_dir_2d"]]
    a = pd.read_csv("image_acquisition.csv")
    a = a.rename(columns={a.columns[0]: "image_id"}) if "image_id" \
        not in a.columns else a
    f = (f.merge(m, on="image_id", how="left")
          .merge(o, on="image_id", how="left")
          .merge(a[["image_id", "group_id"]], on="image_id", how="left"))
    return f[f.batch.isin(BATCHES)].reset_index(drop=True)


def pred_centroid(train: pd.DataFrame, row: pd.Series,
                  feats: list) -> str:
    """Nearest batch median in robust-z space (train-only scales)."""
    scores = {}
    for b in BATCHES:
        tb = train[train.batch == b][feats]
        med = tb.median()
        mad = (tb - med).abs().median().replace(0, np.nan)
        z = ((row[feats] - med) / (1.4826 * mad)).abs()
        scores[b] = float(np.nanmean(z))
    return min(scores, key=scores.get)


def pred_envelope(train: pd.DataFrame, row: pd.Series) -> tuple:
    """9-feature min-max coverage rule (train refits batch envelopes)."""
    cov = {}
    for b in BATCHES:
        tb = train[train.batch == b][ENVELOPE_9]
        inside = ((row[ENVELOPE_9] >= tb.min()) &
                  (row[ENVELOPE_9] <= tb.max())).sum()
        cov[b] = int(inside)
    best = max(cov.values())
    winners = [b for b, c in cov.items() if c == best]
    return (winners[0] if len(winners) == 1 else "ABSTAIN", best)


def run_protocol(df: pd.DataFrame, folds: list) -> dict:
    rows = []
    sets = {"fractions": FRACTIONS,
            "frac+cluster": FRACTIONS + CLUSTER,
            "frac+cl+corr": FRACTIONS + CLUSTER + CORR,
            "frac+cl+c+orient": FRACTIONS + CLUSTER + CORR + ORIENT,
            "acq_signature": ACQ}
    for name, test_idx in folds:
        train = df.drop(index=test_idx)
        for i in test_idx:
            row = df.loc[i]
            rec = {"fold": name, "image_id": row.image_id,
                   "truth": row.batch}
            for sname, feats in sets.items():
                rec[sname] = pred_centroid(train, row, feats)
            rec["envelope"], rec["env_cov"] = pred_envelope(train, row)
            rec["majority"] = max(
                BATCHES, key=lambda b: (train.batch == b).sum())
            rows.append(rec)
    return {"rows": rows}


def summarize(res: dict, proto: str) -> pd.DataFrame:
    df = pd.DataFrame(res["rows"])
    out = []
    for col in ["envelope", "fractions", "frac+cluster", "frac+cl+corr",
                "frac+cl+c+orient", "acq_signature", "majority"]:
        pred = df[col]
        called = pred != "ABSTAIN"
        n = len(df)
        acc = float((pred[called] == df.truth[called]).mean()) \
            if called.any() else np.nan
        recalls = [float((pred[df.truth == b] == b).mean())
                   for b in BATCHES if (df.truth == b).any()]
        out.append(dict(protocol=proto, method=col, n=n,
                        coverage=round(float(called.mean()), 3),
                        accuracy=round(acc, 3),
                        balanced_acc=round(float(np.mean(recalls)), 3)))
    return pd.DataFrame(out)


def main() -> None:
    df = load_table()
    print(f"{len(df)} labelled images, "
          f"{df.group_id.nunique()} inferred groups")
    loo = [("loo", [i]) for i in df.index]
    logo = [(f"group_{g}", df.index[df.group_id == g].tolist())
            for g in df.group_id.unique()]
    tables = [summarize(run_protocol(df, loo), "LOO"),
              summarize(run_protocol(df, logo), "LOGO-inferred")]
    res = pd.concat(tables)
    res.to_csv("benchmark_results.csv", index=False)
    print(res.to_string(index=False))
    # confusion for the strongest honest set under LOO
    loo_rows = pd.DataFrame(run_protocol(df, loo)["rows"])
    print("\nLOO confusion (envelope rule, incl. ABSTAIN):")
    print(pd.crosstab(loo_rows.truth, loo_rows.envelope).to_string())


if __name__ == "__main__":
    main()
