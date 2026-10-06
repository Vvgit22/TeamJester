"""Assign New_Images_Batch photos to existing batches.

Method (interpretable, declared up front — v2 after envelope-coverage
fix):
  1. Extract the same 9 primary features + diagnostics as the frozen
     vcompare recipe (thresholds/classifier fitted on Batch_3 only).
  2. PRIMARY RULE — envelope coverage: for each batch, count how many
     of the 9 features fall inside that batch's observed min-max range.
     - exactly one batch contains the image fully (9/9) -> that batch
     - more than one batch contains it fully -> inconclusive_between
     - no batch contains it fully -> the batch with most features
       inside wins, provided its median robust-z stays below the OOD
       threshold; otherwise out_of_distribution.
  3. Secondary scores kept for transparency: median robust z
     |x - median| / (1.4826·MAD) per batch (biased toward wide batches —
     coverage is the fairer primary rule), and per-feature z table.
  4. No image is forced into a batch on weak evidence.

Outputs: new_image_assignment/{assignments.csv, feature_table.csv,
assignment_report.md, fig_assignment.png}
"""
from __future__ import annotations

import glob
import json
import os

import numpy as np
import pandas as pd

from vcompare import assemble, config, extract, recipe as recipe_mod

RECIPE = "validated_comparison/recipe.json"
FEATURES = list(config.PRIMARY_FEATURES)
# feature direction note for the report
Z_THRESH = 2.5          # median-z above this => no batch contains the point
EPS = 1e-9


def load_existing_features() -> pd.DataFrame:
    df = pd.read_csv("validated_comparison/per_image_features.csv")
    return df[df["batch"].isin(("Batch_1", "Batch_2", "Batch_3"))]


def extract_new(folder: str, recipe: dict, cache: str) -> pd.DataFrame:
    paths = sorted(glob.glob(os.path.join(folder, "*_BSE.tif")))
    assert paths, f"no *_BSE.tif under {folder}"
    extract.set_thresholds(recipe["t_pore"], recipe["t_si"])
    extractions, objects = {}, []
    for p in paths:
        print(f"  extracting {os.path.basename(p)}", flush=True)
        ext = extract.extract_cached(p, "New_Images_Batch", cache)
        extractions[ext["meta"]["image_id"]] = ext
        objects.append(ext["objects"])
    ob = pd.concat(objects, ignore_index=True)
    ob = assemble.classify_objects(ob, recipe["t_core"])
    feats = assemble.build_features(extractions, ob, recipe)
    return feats


def batch_stats(existing: pd.DataFrame) -> dict:
    stats = {}
    for b, sub in existing.groupby("batch"):
        stats[b] = {
            f: {"med": float(sub[f].median()),
                "mad": float(1.4826 * np.median(
                    np.abs(sub[f] - sub[f].median()))),
                "lo": float(sub[f].min()),
                "hi": float(sub[f].max())}
            for f in FEATURES
        }
    return stats


def assign(row: pd.Series, stats: dict) -> dict:
    out = {"image_id": row["image_id"]}
    z_per_batch, inside = {}, {}
    for b, bs in stats.items():
        zs = []
        for f in FEATURES:
            mad = max(bs[f]["mad"], EPS)
            zs.append(abs(row[f] - bs[f]["med"]) / mad)
            out[f"z_{b}_{f}"] = zs[-1]
        z_per_batch[b] = float(np.median(zs))
        out[f"score_{b}"] = z_per_batch[b]
        inside[b] = int(sum(bs[f]["lo"] <= row[f] <= bs[f]["hi"]
                            for f in FEATURES))
        out[f"inside_env_{b}"] = inside[b]
        out[f"outside_env_{b}"] = len(FEATURES) - inside[b]

    # primary rule: envelope coverage (unbiased by batch spread)
    full = [b for b, n in inside.items() if n == len(FEATURES)]
    if len(full) == 1:
        out["assigned_batch"] = full[0]
        out["confidence"] = ("envelope-consistent "
                             f"(9/9 features inside {full[0]}; "
                             + "; ".join(f"{b} {n}/9" for b, n
                                         in inside.items()
                                         if b != full[0]) + ")")
    elif len(full) > 1:
        out["assigned_batch"] = "inconclusive_between_" + \
            "_".join(b[-1] for b in full)
        out["confidence"] = "inside multiple batch envelopes — " \
            "the batches overlap and this image cannot be separated"
    else:
        best = max(inside, key=inside.get)
        tied = [b for b, n in inside.items() if n == inside[best]]
        if len(tied) > 1:
            order = sorted(z_per_batch, key=z_per_batch.get)
            best = order[0]
            tied_note = f"coverage tie {tied} -> lowest median-z"
        else:
            tied_note = ""
        if z_per_batch[best] > Z_THRESH:
            out["assigned_batch"] = "out_of_distribution"
            out["confidence"] = "none — outside every batch envelope"
        else:
            out["assigned_batch"] = best
            out["confidence"] = (
                f"best envelope coverage {inside[best]}/9 "
                f"(median-z {z_per_batch[best]:.2f}) {tied_note}").strip()
    order = sorted(z_per_batch, key=z_per_batch.get)
    out["best_score"] = z_per_batch[order[0]]
    out["second_best"] = order[1]
    out["score_margin"] = (z_per_batch[order[1]]
                           - z_per_batch[order[0]]) / max(
                               z_per_batch[order[0]], EPS)
    out["medianz_winner"] = order[0]   # kept for bias transparency
    return out


def main(folder: str = "New_Images_Batch",
         recipe_path: str = RECIPE,
         out_dir: str = "new_image_assignment",
         cache: str = "new_image_assignment/cache"):
    os.makedirs(out_dir, exist_ok=True)
    recipe = recipe_mod.load_recipe(recipe_path)
    print(f"recipe: fitted on {recipe['fitted_on']} "
          f"(t_pore={recipe['t_pore']:.4f}, t_si={recipe['t_si']:.4f}, "
          f"t_core={recipe['t_core']:.4f})")

    existing = load_existing_features()
    new = extract_new(folder, recipe, cache)
    new.to_csv(os.path.join(out_dir, "feature_table.csv"), index=False)

    stats = batch_stats(existing)
    rows = [assign(r, stats) for _, r in new.iterrows()]
    res = pd.DataFrame(rows)
    res.to_csv(os.path.join(out_dir, "assignments.csv"), index=False)

    # ---- report ------------------------------------------------------
    L = ["# New-image batch assignment — ALL CALLS: \"CAN'T TELL\"\n",
         "**Status (acquisition analysis):** each new photo's frame "
         "height occurs in only one batch's acquisition group, and "
         "each call below followed that session — the assignments "
         "cannot separate batch-match from session-match. The "
         "protocol (predictions saved blind before any ground truth) "
         "is kept; the verdicts are relabelled \"can't tell\" until "
         "session-controlled data exists. Do not quote the assigned "
         "column as material evidence.\n",
         f"Method (v2): primary rule = envelope coverage — count of the "
         f"{len(FEATURES)} declared features inside each batch's "
         "observed min-max range (unbiased by batch spread). Exactly "
         "one batch containing 9/9 => that batch; several => "
         "inconclusive; none => best coverage wins unless median "
         f"robust-z >{Z_THRESH} => out-of-distribution. Median-z kept "
         "as a secondary score (it favours wide batches — see "
         "`medianz_winner` in assignments.csv). "
         f"Recipe frozen on Batch_3 (`{recipe_path}`).\n",
         "| image | assigned | inside env. (B1/B2/B3) | median-z best "
         "| confidence |",
         "|---|---|---|---|---|"]
    for _, r in res.iterrows():
        L.append(f"| {r['image_id']} | {r['assigned_batch']} | "
                 f"{r['inside_env_Batch_1']}/{r['inside_env_Batch_2']}"
                 f"/{r['inside_env_Batch_3']} | {r['medianz_winner']} "
                 f"{r['best_score']:.2f} | {r['confidence'][:60]} |")
    L.append("\n## Per-image notes\n")
    for _, r in res.iterrows():
        nr = new[new.image_id == r["image_id"]].iloc[0]
        L.append(f"### {r['image_id']} → {r['assigned_batch']} "
                 f"({r['confidence']})")
        for b in ("Batch_1", "Batch_2", "Batch_3"):
            L.append(f"- vs {b}: {r[f'inside_env_{b}']}/9 features "
                     f"inside envelope; median-z "
                     f"{r[f'score_{b}']:.2f}")
        ref_batch = r["assigned_batch"] if r["assigned_batch"] in stats \
            else r["medianz_winner"]
        drv = sorted(((f, r[f"z_{ref_batch}_{f}"]) for f in FEATURES),
                     key=lambda t: -t[1])[:3]
        L.append("- largest deviations vs " + ref_batch + ": " +
                 "; ".join(f"{f} z={z:.1f}" for f, z in drv))
        L.append(f"- key features: pore_frac={nr['pore_frac']:.3f}, "
                 f"pores/mpx={nr['pores_per_mpx']:.0f} "
                 f"(noise-adj {nr['pores_per_mpx_noise_adj']:.0f}), "
                 f"Si cand={nr['si_candidate_frac']:.3f}, "
                 f"uncertain={nr['uncertain_bright_frac']:.3f}, "
                 f"Si d50={nr['si_d50_um']:.2f} um, "
                 f"R={nr['si_clustering_R']:.2f}\n")
    L.append("## Caveats\n")
    L.append("- Assignment is similarity, not provenance: batches "
             "overlap on every feature, so weak-confidence calls are "
             "expected for images near the overlap region.")
    L.append("- With 7 images in Batch_1/2 and 17 in Batch_3, envelope "
             "estimates are noisy; scores carry that uncertainty.")
    L.append("- The frozen recipe segments BSE only; InLens/ETD "
             "channels are recorded but not used (channel comparability "
             "not yet established).")
    L.append("- Session confound: the calls follow each photo's "
             "acquisition group; they measure similarity to that "
             "session's batch, not provenance. Verdicts are \"can't "
             "tell\" until controlled re-imaging exists.")
    # ---- figure: z-heatmap of new images vs batch envelopes ---------
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(figsize=(10, 2.4))
        mat = np.array([[r[f"z_{b}_{f}"] for f in FEATURES]
                        for _, r in res.iterrows()
                        for b in ("Batch_1", "Batch_2", "Batch_3")])
        ylab = [f"{r['image_id']} vs {b}"
                for _, r in res.iterrows()
                for b in ("Batch_1", "Batch_2", "Batch_3")]
        im_ = ax.imshow(np.clip(mat, 0, 5), aspect="auto",
                        cmap="magma_r", vmin=0, vmax=5)
        ax.set_yticks(range(len(ylab)), ylab, fontsize=7)
        ax.set_xticks(range(len(FEATURES)),
                      [f.replace("pores_per_mpx_noise_adj", "pore/mpx·nadj")
                       for f in FEATURES], rotation=45, ha="right",
                      fontsize=7)
        ax.set_title("|z| vs each batch envelope (clipped at 5)")
        fig.colorbar(im_, ax=ax, label="robust |z|")
        fig.tight_layout()
        fig.savefig(os.path.join(out_dir, "fig_assignment.png"),
                    dpi=160)
        plt.close(fig)
    except Exception as e:
        print(f"  (figure skipped: {e})")

    path = os.path.join(out_dir, "assignment_report.md")
    with open(path, "w") as fh:
        fh.write("\n".join(L))
    print("\n".join(L[:20]))
    print(f"\n-> {path}")


_VALIDATION_BATCHES = ("Batch_1", "Batch_2", "Batch_3")


def validate_assignments(features: pd.DataFrame, groups: pd.DataFrame,
                         group_column: str = "group_id"
                         ) -> tuple[pd.DataFrame, pd.DataFrame]:
    required = ["image_id", "batch", *FEATURES]
    missing = set(required) - set(features.columns)
    if missing:
        raise ValueError(f"Missing feature columns: {sorted(missing)}")
    if group_column == "image_id":
        raise ValueError("Use a separate parent/specimen/group column, not image_id")
    if not {"image_id", group_column}.issubset(groups.columns):
        raise ValueError(f"Group mapping needs image_id and {group_column}")
    data = features[required].copy()
    data[FEATURES] = data[FEATURES].astype(float)
    mapping = groups[["image_id", group_column]].copy()
    for table in (data, mapping):
        if table.image_id.isna().any() or table.image_id.duplicated().any():
            raise ValueError("Image IDs must be present and unique")
        table["image_id"] = table.image_id.astype(str)
        if table.image_id.str.strip().eq("").any() or \
                table.image_id.duplicated().any():
            raise ValueError("Image IDs must be nonempty and unique")
    if data.batch.isna().any() or set(data.batch) != set(_VALIDATION_BATCHES):
        raise ValueError("Validation requires labeled Batch_1, Batch_2 and Batch_3 only")
    if not np.isfinite(data[FEATURES].to_numpy(dtype=float)).all():
        raise ValueError("Validation features must all be finite; no silent imputation")
    mapping = mapping.rename(columns={group_column: "validation_group"})
    data = data.merge(mapping, on="image_id", how="left", validate="one_to_one")
    if data.validation_group.isna().any():
        raise ValueError("Every labeled image needs a group assignment")
    data["validation_group"] = data.validation_group.astype(str)
    if data.validation_group.str.strip().eq("").any():
        raise ValueError("Group IDs must be nonempty")
    data = data.sort_values("image_id").reset_index(drop=True)
    rows, folds = [], []
    for protocol, key in (("leave_one_image_out", "image_id"),
                          ("leave_one_group_out", "validation_group")):
        for fold_id, test in data.groupby(key, sort=True):
            train = data[data[key] != fold_id]
            counts = train.batch.value_counts().reindex(_VALIDATION_BATCHES,
                                                        fill_value=0)
            if (counts < 2).any():
                raise ValueError(
                    f"{protocol} fold {fold_id}: fewer than two training examples "
                    f"for {counts[counts < 2].index.tolist()}")
            stats = batch_stats(train)
            majority = counts.sort_index().idxmax()
            folds.append(dict(
                protocol=protocol, fold_id=str(fold_id),
                n_train=len(train), n_test=len(test),
                train_ids=json.dumps(train.image_id.tolist()),
                test_ids=json.dumps(test.image_id.tolist()),
                train_groups=json.dumps(sorted(train.validation_group.unique())),
                test_groups=json.dumps(sorted(test.validation_group.unique())),
                **{f"n_train_{b}": int(counts[b]) for b in _VALIDATION_BATCHES}))
            for _, row in test.iterrows():
                result = assign(row[["image_id", *FEATURES]], stats)
                decision = result["assigned_batch"]
                predicted = decision if decision in _VALIDATION_BATCHES else "ABSTAIN"
                rows.append(dict(
                    protocol=protocol, fold_id=str(fold_id),
                    image_id=row.image_id, validation_group=row.validation_group,
                    true_batch=row.batch, predicted_batch=predicted,
                    raw_decision=decision, correct=bool(predicted == row.batch),
                    majority_prediction=majority,
                    **{f"inside_env_{b}": result[f"inside_env_{b}"]
                       for b in _VALIDATION_BATCHES},
                    **{f"score_{b}": result[f"score_{b}"]
                       for b in _VALIDATION_BATCHES}))
    return pd.DataFrame(rows), pd.DataFrame(folds)


def accuracy_tables(predictions: pd.DataFrame, n_boot: int = 10_000,
                    seed: int = 0) -> tuple[pd.DataFrame, pd.DataFrame]:
    if n_boot < 1:
        raise ValueError("n_boot must be positive")
    rng = np.random.default_rng(seed)
    summaries, confusions = [], []
    for protocol, data in predictions.groupby("protocol", sort=True):
        if not data.image_id.is_unique:
            raise ValueError("Each protocol must predict every image exactly once")
        clusters = data.groupby("validation_group", sort=True).size()
        n_groups = len(clusters)
        draws = rng.integers(0, n_groups, size=(n_boot, n_groups))
        denominators = clusters.to_numpy()[draws].sum(axis=1)
        for model, column in (("envelope_rule", "predicted_batch"),
                              ("majority_baseline", "majority_prediction")):
            correct = data[column].eq(data.true_batch)
            answered = data[column].isin(_VALIDATION_BATCHES)
            by_class = correct.groupby(data.true_batch).mean()
            cluster_hits = correct.groupby(data.validation_group).sum()
            samples = cluster_hits.reindex(clusters.index).to_numpy()[draws].sum(
                axis=1) / denominators
            lo, hi = np.quantile(samples, [0.025, 0.975]) if n_groups > 1 \
                else (None, None)
            summaries.append(dict(
                protocol=protocol, model=model, n_images=len(data),
                n_groups=n_groups, n_correct=int(correct.sum()),
                accuracy=float(correct.mean()),
                balanced_accuracy=float(by_class.mean()),
                n_answered=int(answered.sum()), n_abstained=int((~answered).sum()),
                coverage=float(answered.mean()),
                selective_accuracy=float(correct[answered].mean())
                if answered.any() else None,
                conditional_group_bootstrap_lo=lo,
                conditional_group_bootstrap_hi=hi,
                **{f"recall_{b}": float(by_class.get(b, np.nan))
                   for b in _VALIDATION_BATCHES}))
            matrix = pd.crosstab(data.true_batch, data[column]).reindex(
                index=_VALIDATION_BATCHES,
                columns=[*_VALIDATION_BATCHES, "ABSTAIN"], fill_value=0)
            matrix = matrix.rename_axis(index="true_batch", columns=None).reset_index()
            matrix.insert(0, "model", model)
            matrix.insert(0, "protocol", protocol)
            confusions.append(matrix)
    return pd.DataFrame(summaries), pd.concat(confusions, ignore_index=True)


def validation_main(argv: list[str]) -> None:
    import argparse
    from datetime import datetime, timezone

    parser = argparse.ArgumentParser(
        description="Classifier-only held-out accuracy on fixed saved measurements.")
    parser.add_argument("--features", default="validated_comparison/per_image_features.csv")
    parser.add_argument("--groups", default="image_acquisition.csv")
    parser.add_argument("--group-column", default="group_id")
    parser.add_argument("--group-kind", default="inferred",
                        choices=("inferred", "confirmed_parent", "confirmed_specimen"))
    parser.add_argument("--recipe", default=RECIPE)
    parser.add_argument("--out", default="new_image_assignment/accuracy")
    parser.add_argument("--n-boot", type=int, default=10_000)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args(argv)
    if os.path.exists(args.out):
        parser.error("Output path already exists; choose a new --out to preserve results")
    if args.n_boot < 1:
        parser.error("--n-boot must be positive")
    features = pd.read_csv(args.features)
    groups = pd.read_csv(args.groups)
    predictions, folds = validate_assignments(features, groups, args.group_column)
    summary, confusion = accuracy_tables(predictions, args.n_boot, args.seed)
    caveats = [
        "Empirical classifier-only cross-validation, not an independent end-to-end test.",
        "The tentative envelope rule is evaluated as implemented, before any blanket "
        "provenance-based abstention. No feature, rule or threshold was tuned here.",
        "Every fold refits batch ranges, medians and MAD scales using training rows only.",
        "Saved segmentation, object classification and noise adjustment were already "
        "calibrated on all Batch_3 images, including held-out reference images.",
        "The feature set and assignment rule were previously explored on this dataset; "
        "these labels are curated challenge categories, not independently sampled lots.",
        "The group bootstrap resamples clusters of already-held-out predictions. It is "
        "conditional on this feature table, grouping and fitted CV predictions; it does "
        "not refit the pipeline or cover uncertainty in source identity or calibration.",
        "Accuracy counts abstentions as unsuccessful classifications. Selective accuracy "
        "excludes abstentions and must be read together with coverage.",
        "Overall accuracy weights crops equally; balanced accuracy averages class recalls.",
        "The three new images have no confirmed labels here. Their accuracy and individual "
        "probabilities of correctness cannot be inferred from feature coverage or this score."]
    if args.group_kind == "inferred":
        caveats.append(
            "Groups are inferred source/acquisition/export strata, not confirmed parents "
            "or sessions. Holding them out does not guarantee independent specimens.")
    input_paths = {"features": args.features, "groups": args.groups, "recipe": args.recipe}
    manifest = dict(
        created_utc=datetime.now(timezone.utc).isoformat(),
        evaluation_scope="conditional_classifier_only",
        end_to_end_validation=False,
        group_kind=args.group_kind, group_column=args.group_column,
        features=FEATURES, z_threshold=Z_THRESH,
        n_boot=args.n_boot, seed=args.seed,
        new_image_accuracy=None, caveats=caveats,
        inputs={k: dict(path=os.path.abspath(p), md5=extract.file_md5(p))
                for k, p in input_paths.items()},
        code_md5={os.path.abspath(p): extract.file_md5(p)
                  for p in (__file__, config.__file__, extract.__file__,
                            assemble.__file__, recipe_mod.__file__)},
        numpy_version=np.__version__, pandas_version=pd.__version__,
        metrics=json.loads(summary.to_json(orient="records", double_precision=15)))
    os.makedirs(args.out, exist_ok=False)
    predictions.to_csv(os.path.join(args.out, "predictions.csv"), index=False)
    folds.to_csv(os.path.join(args.out, "folds.csv"), index=False)
    summary.to_csv(os.path.join(args.out, "summary.csv"), index=False)
    confusion.to_csv(os.path.join(args.out, "confusion.csv"), index=False)
    with open(os.path.join(args.out, "validation.json"), "w") as fh:
        json.dump(manifest, fh, indent=2, allow_nan=False)
    print("Measured classifier-only held-out accuracy (saved preprocessing fixed):")
    for row in summary.itertuples():
        print(f"{row.protocol} / {row.model}: {row.n_correct}/{row.n_images} "
              f"= {row.accuracy:.1%}; balanced accuracy {row.balanced_accuracy:.1%}; "
              f"abstentions {row.n_abstained}")
    print("\nLimits:")
    for caveat in caveats:
        print(f"- {caveat}")
    print(f"\nResults and provenance: {args.out}")


if __name__ == "__main__":
    import sys
    if sys.argv[1:2] == ["--validate"]:
        validation_main(sys.argv[2:])
    else:
        main(*sys.argv[1:])
