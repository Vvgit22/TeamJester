#!/usr/bin/env python
"""Validated batch comparison — one command regenerates everything.

    .venv/bin/python run_compare.py --data Hackathon-Polaron \
        --out validated_comparison

Stages: frozen reference recipe -> native-res extraction (cached) ->
matched panels -> corrected QC recheck -> exact permutation pairwise
tests with MDD -> robustness scenarios -> START_HERE + appendix + checks.

Writes only under --out.  Existing pipelines and outputs are untouched.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from vcompare import (assemble, checks, config, extract, panels,
                      qc_recheck, recipe as recipe_mod, report, scenarios,
                      stats)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", default=".")
    ap.add_argument("--out", default="validated_comparison")
    ap.add_argument("--batches", nargs="+",
                    default=["Batch_1", "Batch_2", "Batch_3"])
    ap.add_argument("--fast", action="store_true",
                    help="2x downsample + quick stats (dev only)")
    ap.add_argument("--seed", type=int, default=config.SEED)
    ap.add_argument("--n-boot", type=int, default=config.N_BOOT)
    ap.add_argument("--skip-panels", action="store_true")
    args = ap.parse_args()

    t0 = time.time()
    out = os.path.abspath(args.out)
    cache = os.path.join(out, "cache")
    os.makedirs(out, exist_ok=True)
    downsample = 2 if args.fast else 1

    from micro2dfn.io import discover_batches  # read-only reuse
    batch_paths = discover_batches(args.data, args.batches)
    if not batch_paths:
        raise SystemExit(f"no Batch_* dirs under {args.data}")
    print("batches:", {k: len(v) for k, v in batch_paths.items()})

    # ---- 1. frozen recipe ------------------------------------------------
    recipe_path = os.path.join(out, "recipe.json")
    ref_paths = batch_paths[config.REFERENCE_BATCH]
    print("loading reference images for threshold fit...")
    ref_ims = [extract.Image(p, config.REFERENCE_BATCH, downsample)
               for p in ref_paths]
    t_pore, t_si = extract.fit_thresholds(
        [im.gray for im in ref_ims], [im.pixel_um for im in ref_ims],
        args.seed)
    print(f"  reference thresholds: t_pore={t_pore:.4f} t_si={t_si:.4f}")
    extract.set_thresholds(t_pore, t_si)

    print("extracting reference batch (for classifier + noise fit)...")
    ref_ext = {os.path.basename(p).replace("_BSE.tif", ""):
               extract.extract_cached(p, config.REFERENCE_BATCH, cache,
                                      downsample)
               for p in ref_paths}
    image_files = {os.path.basename(p).replace("_BSE.tif", ""): p
                   for paths in batch_paths.values() for p in paths}
    recipe = recipe_mod.fit_recipe(list(ref_ext.values()), t_pore, t_si,
                                   image_files, args.seed)
    recipe_mod.save_recipe(recipe, recipe_path)
    print(f"  t_core={recipe['t_core']:.4f}  "
          f"noise slope={recipe['noise_adj']['slope']:.2f} "
          f"(ref R2={recipe['noise_adj']['ref_r2']:.3f})")

    # ---- 2. extract all images -------------------------------------------
    print("extracting all images (cached after first run)...")
    extractions = {}
    objects_frames = []
    for batch, paths in batch_paths.items():
        for p in paths:
            e = extract.extract_cached(p, batch, cache, downsample)
            extractions[e["meta"]["image_id"]] = e
            objects_frames.append(e["objects"])
            print(f"  {e['meta']['image_id']} "
                  f"({len(e['objects'])} objects)")
    objects_all = pd.concat(objects_frames, ignore_index=True)

    # QC reproduction thresholds (pooled across ALL batches — as shipped)
    print("fitting QC-reproduction thresholds (pooled, as shipped)...")
    qc_ims = list(ref_ims)
    for b, paths in batch_paths.items():
        if b == config.REFERENCE_BATCH:
            continue
        qc_ims += [extract.Image(p, b, downsample) for p in paths]
    qc_tp, qc_ts = extract.fit_thresholds(
        [im.gray for im in qc_ims], [im.pixel_um for im in qc_ims],
        args.seed)

    # ---- 3. primary feature table ----------------------------------------
    objects_cls = assemble.classify_objects(objects_all, recipe["t_core"])
    feats = assemble.build_features(extractions, objects_cls, recipe)
    feats.to_csv(os.path.join(out, "per_image_features.csv"), index=False)
    objects_cls.to_csv(os.path.join(out, "objects_classified.csv"),
                       index=False)
    print(f"features: {len(feats)} images")

    # ---- 4. corrected QC recheck ------------------------------------------
    qc_dir = os.path.join(args.data, "qc_output")
    if not os.path.isdir(qc_dir):
        qc_dir = "qc_output"
    if os.path.isdir(qc_dir):
        print("QC recheck (reference-only weights, held-out T2)...")
        qc_verd, qc_calib = qc_recheck.run(qc_dir, tuple(args.batches),
                                           args.seed)
        qc_verd.to_csv(os.path.join(out, "qc_recheck.csv"), index=False)
        qc_calib.to_csv(os.path.join(out, "calibration_counts.csv"),
                        index=False)
        print(qc_verd[["scenario", "batch", "verdict"]].to_string(
            index=False))
    else:
        qc_verd = pd.DataFrame()
        qc_calib = pd.DataFrame(dict(n_reference=[17], flag_threshold=[
            np.nan], loo_max=[np.nan], n_exceedances=[np.nan],
            exceedance_rate=[np.nan], exceedance_rate_ci_lo=[np.nan],
            exceedance_rate_ci_hi=[np.nan], note=["qc_output missing"]))
        print("  qc_output/ not found — skipping recheck")

    # ---- 5. primary pairwise tests ----------------------------------------
    print("pairwise exact-permutation tests...")
    pair_tab = stats.pairwise_table(feats, batch_paths,
                                    config.PRIMARY_FEATURES,
                                    args.n_boot, args.seed)
    pair_tab.to_csv(os.path.join(out, "pairwise_comparisons.csv"),
                    index=False)
    print(pair_tab[["pair", "feature", "median_diff", "p_exact",
                    "significant_bh"]].to_string(index=False))

    # ---- 6. robustness scenarios ------------------------------------------
    print("scenario variants...")
    ext2x = objs2x = None
    if not args.fast:
        cache2 = os.path.join(out, "cache_ds2")
        extract.set_thresholds(t_pore, t_si)
        ext2x, frames2 = {}, []
        for batch, paths in batch_paths.items():
            for p in paths:
                e = extract.extract_cached(p, batch, cache2, 2)
                ext2x[e["meta"]["image_id"]] = e
                frames2.append(e["objects"])
        objs2x = pd.concat(frames2, ignore_index=True)
    scen_tabs = scenarios.scenario_tables(
        extractions, objects_all, recipe, feats, batch_paths,
        ext2x, objs2x)
    stress = scenarios.threshold_stress(batch_paths, recipe) \
        if not args.fast else pd.DataFrame()

    rob_rows = []
    for sname, stab in scen_tabs.items():
        ptab = stats.pairwise_table(stab, batch_paths,
                                    config.PRIMARY_FEATURES,
                                    2000, args.seed)
        ptab["scenario"] = sname
        rob_rows.append(ptab)
    if len(stress):
        for sname in stress.scenario.unique():
            ptab = stats.pairwise_table(
                stress[stress.scenario == sname], batch_paths,
                scenarios.PIXEL_LEVEL_FEATURES, 2000, args.seed)
            ptab["scenario"] = sname
            rob_rows.append(ptab)
    robustness = pd.concat(rob_rows, ignore_index=True)
    robustness.to_csv(os.path.join(out, "robustness.csv"), index=False)

    # LOO sweep (deterministic, exact per drop)
    print("leave-one-image-out sweep...")
    loo_frames = []
    for pair in (("Batch_1", "Batch_3"), ("Batch_2", "Batch_3"),
                 ("Batch_1", "Batch_2")):
        loo_frames.append(stats.loo_sweep(feats, pair,
                                          config.PRIMARY_FEATURES))
    pd.concat(loo_frames).to_csv(os.path.join(out, "loo_sweep.csv"),
                                 index=False)

    # ---- 7. panels + review sheet ------------------------------------------
    if not args.skip_panels:
        print("matched panels...")
        sel = {iid: (feats.set_index("image_id").loc[iid, "batch"],
                     image_files[iid]) for iid in _panel_ids(feats)}
        sheet = panels.make_panels(sel, extractions, objects_cls,
                                   (qc_tp, qc_ts), recipe,
                                   os.path.join(out, "panels"))
        sheet.to_csv(os.path.join(out, "expert_review_sheet.csv"),
                     index=False)
        print(f"  {len(sheet)} panels -> {out}/panels/")

    # ---- 8. report + checks -------------------------------------------------
    print("writing report + checks...")
    report.fig_findings(feats, os.path.join(out, "fig_findings.png"))
    report.write_start_here(os.path.join(out, "START_HERE.md"),
                            pair_tab, robustness, qc_verd, qc_calib, feats)
    report.write_before_after(os.path.join(out, "before_after.md"),
                              qc_verd, pair_tab, robustness)
    run_settings = dict(
        command=" ".join([".venv/bin/python run_compare.py",
                          f"--data {args.data}", f"--out {args.out}"]
                         + (["--fast"] if args.fast else [])),
        seed=args.seed, n_boot=args.n_boot, downsample=downsample,
        fast=args.fast, batches={k: len(v) for k, v in
                                 batch_paths.items()})
    report.write_appendix(os.path.join(out, "TECHNICAL_APPENDIX.md"),
                          recipe, pair_tab, run_settings)

    recipe2 = recipe_mod.fit_recipe(list(ref_ext.values()), t_pore, t_si,
                                    image_files, args.seed)
    start_here = open(os.path.join(out, "START_HERE.md")).read()
    checks_df = checks.run_checks(recipe, recipe2, feats, pair_tab,
                                  qc_calib, start_here, stress)
    checks_df.to_csv(os.path.join(out, "checks.csv"), index=False)
    print(checks_df.to_string(index=False))
    print(f"\ndone in {time.time() - t0:.0f}s -> {out}/")


def _panel_ids(feats: pd.DataFrame) -> list[str]:
    """All B1 (7) + 3 representative each of B2/B3 (nearest to batch
    median si_candidate_frac)."""
    ids = list(feats.loc[feats.batch == "Batch_1", "image_id"])
    for batch in ("Batch_2", "Batch_3"):
        sub = feats[feats.batch == batch]
        med = sub["si_candidate_frac"].median()
        ids += list(sub.iloc[
            (sub["si_candidate_frac"] - med).abs().argsort()
        ].head(3)["image_id"])
    return ids


if __name__ == "__main__":
    main()
