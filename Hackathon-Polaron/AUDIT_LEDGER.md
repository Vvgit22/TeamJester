# Audit ledger — staged correctness pass, 2026-10

Independent reproductions, repairs, and evidence. Deliverables required by
the staged-audit brief live here in one place.

## Provenance hierarchy (what is and is not known)

```
physical specimens/electrodes          <- UNKNOWN count (organizer: "around
    -> parent microscopy images        <- ~15 parent images per organizer;
    -> crops with paired detector views     complete mapping NOT known)
    -> artificial batches              <- deliberately constructed
```

- `image_acquisition.csv` / `image_acquisition_groups.csv`: 13 inferred
  frame-height/appearance strata (`group_id` = h_px). Inferred strata only —
  NOT confirmed parents, sessions, or specimens.
- Crop coordinates, overlap, transforms (rotate/flip/resize), parent
  mapping, and acquisition-session metadata: UNRESOLVED — required from
  the organizer for any parent-held-out analysis.
- Consequence: crop-level statistics cannot be treated as independent-
  specimen statistics. All reported numbers are **curated-batch
  associations** (spec level A), not level B generalization or level C
  manufacturing/electrochemical inference.

## Acquisition audit (`image_acquisition.csv`)

| item | finding |
|---|---|
| `pixel_nm` column | **mislabeled** — holds µm/px (0.025 = 25 nm/px). TIFF `XResolution` tags verified directly: ~25.0005 nm/px. `io._pixel_size_um` reads tags correctly. |
| detector identity | TWO pairings mixed: 30 `Inlens+ETD`, 4 `Inlens+SE` — SE vs ETD are different detectors; pooled channel comparisons must respect this. |
| clipping | 21/34 images have `raw_p1 == 0` (black clipping); 27/34 `black_share > 1%`. No top-end saturation (`raw_p99 < 250` all). Flat-field cannot restore clipped blacks. |
| inferred groups | 13 frame-height groups, sizes 1–4. Dependence units for blocked analyses — inferred only. |
| channels present | all 34 have Inlens; 30 have ETD; 4 have SE instead. |

## Reproduction ledger

| # | reported issue | reproduced? | evidence | disposition |
|---|---|---|---|---|
| A | accessible-Si mixes connected-component numerator with watershed denominator | **YES, exact** | `reproduce_si_accessible.py`: hawkfj64 shipped 0.523952 (bit-exact vs saved CSV); corrected number-frac 0.245509, area-weighted 0.371440 — all match reported values | FIXED in `markers.py` + `objects.py::particle_mask` (watershed label image preserved); regression `tests/test_si_contact.py` |
| B | channel-mask centroid matching loses ~70% of bright area | **YES** | img_hawkfj64: buggy coverage 27.4% (reported 27-31%); exact-raster coverage 91.9%, dropped 8.1% = sub-threshold watershed objects | FIXED in `analyze_channels.py::bright_kind_masks` — exact watershed rasterization, disjoint masks, `dropped_px`/`mask_coverage` declared |
| C | vcompare "si" spatial metrics measure ALL bright | **YES** | `analyze_spatial.py` used `seg == SI_CAND` (classified + uncertain); hawkfj64 si_hotspot 3.98 vs bright 2.40 — materially different | FIXED — `bright_*` (all bright) and `si_*` (classified, exact raster) reported separately; `unc_share_of_bright` added |
| D | `abs(orientation)>60` picks HORIZONTAL objects called vertical | **YES** | skimage `orientation` measured FROM row axis: vertical bar → 0°, horizontal bar → 90° (tested) | FIXED — test now `abs(deg) < 30` (within 30° of frame-vertical); report documents the reversed v1 |
| E1 | `BH([0.03,0.04], 0.05)` → `[False,True]` | **YES** | elementwise gate blocked step-up | FIXED in `vcompare/stats.py::benjamini_hochberg`; `tests/test_stats.py` |
| E2 | NaN feature → p = 0 (false maximal significance) | **YES** | `median_diff_null` propagates NaN via `np.median`; `exact_pvalues` returned 0 | FIXED — per-feature finite filtering, `insufficient` flag, NaN→NaN p |
| E3 | scorecard weights fitted on pooled ref+incoming | **YES** | `build_scorecard(baseline, pooled)` — pooled included judged batches, contradicting docstring | FIXED — redundancy now on `baseline.table` only (`pipeline.py`) |
| F | open-domain FDM tau ≠ 1 (0.9375/1.0625) | n/a — path archived | `tau_fdm_*` removed in cleanup; unresolved numerical issue documented | ARCHIVED, documented, not restored |
| TJ1 | TeamJester phase-mask overlap after fusion | **YES** | `inlens_refine` adds pore px inside bright mask without re-exclusion → pore∩silicon overlap; `graphite_frac` can go negative (segment.py) | recorded — benchmark-only assessment |
| TJ2 | TeamJester FFT frequency-grid mismatch | NOT in snapshot | available snapshot (commit `96a9fec`, ≠ cited `57921d2`) uses only autocorrelation `corr_len` (self-consistent) | unverified — other commit needed |
| TJ3 | TeamJester mislabeled LBP flat bin | NOT in snapshot | no LBP code in snapshot source | unverified |
| TJ4 | TeamJester circular detector validation | partial | `load_detector` only loads Inlens; ETD validation logic not in snapshot | unverified |

## What changed (code → measurement)

| change | before | after | downstream |
|---|---|---|---|
| `si_accessible_frac` | 1 − enclosed_CC/n_watershed (mixed populations) | = `si_contact_area_frac` (area-weighted contacted share, watershed identity) | hawkfj64 0.524 → **0.371**; batch medians B1 0.592→0.483, B2 0.598→0.378, B3 0.578→0.354; **B1-vs-B3 contrast widened** (+0.014 → +0.130); DFN `si_act_*` bracket drops ~29-41% → saved DFN outputs stale (rerun deferred) |
| `si_enclosed_share` | component/particle mixed | watershed-consistent | batch medians 0.40-0.42 → **0.72-0.78**; `si_contact_num_frac` 0.22-0.28 — ~1 in 4 classified particles touches a resolved pore |
| non-contact markers | — | — | unchanged except `si_lowcoverage_share` (contact family) and `pore_largest_region_frac` (the repaired `label()` unpack); `si_bulk_contrast` moved 1e-7 (float noise) |
| new markers | — | `si_contact_num_frac`, `si_contact_area_frac`, `si_area_near_pore_frac`, `contact_population` | distinct quantities now named, not conflated |
| channel masks | 27-31% painted coverage, non-disjoint CC painting | 91.9% coverage, disjoint, `dropped_px` declared | `channel_features.csv` regenerated |
| spatial metrics | `si_*` = all bright; crack selector measured horizontal objects | `bright_*`/`si_*` split; `cracklike_frac` = true frame-vertical | `spatial_features_v2.csv` (v1 preserved) |
| BH + permutation | BH([.03,.04]) wrong; NaN→p=0 | standard step-up; NaN→NaN + insufficient flag | `pairwise_table`/`loo_sweep` per-feature filtering |
| scorecard weights | redundancy on pooled (incl. judged) | redundancy on baseline only | prior weights change → re-run QC to re-baseline |
| label() unpack | `lab_p, _ = label(pore)` crashed (skimage returns 1 array) | `lab_p = label(pore)` | `pore_largest_region_frac` now computes |

## Orientation (S) — validated deliverable

Module `micro2dfn/orientation.py`, driver `analyze_orientation.py`,
tests `tests/test_orientation.py` (all spec §8H cases pass, including
the FFT failure mode: isotropic noise on the real 1034×3500 frame gives
S_x ≈ 0 and S_dir < 0.1 — the old FFT scored +0.70 on the same input).

Conventions: θ from image-horizontal (+x), axial mod 180°;
θ0 = 0° horizontal reference; populations never mixed
(tex_all / tex_si / obj_si eq+aw / obj_pore eq+aw); weights declared
(coherence for texture; equal and area for objects);
σ_coher = 4 px ≈ 0.10 µm local-order window; coher ≥ 0.3 eligibility;
coverage (valid-area fraction) reported per image; axial histograms
(18 bins) per image per population; isotropic nulls resampled
empirically per weight vector (pixel-permutation caveat flagged for
texture); object bootstrap CI on objects; quadrant spread = within-
image spatial resampling (labeled, not a batch CI); group-stratified
summaries for dependence.

Batch medians (all 34 images): **obj_pore_aw S_dir ≈ 0.56-0.59 in
every batch** (null p95 ≈ 0.25), θ_dir ≈ −3° → large elongated pores
prefer near-horizontal orientation consistently across batches —
the strongest, best-validated morphological signal, and it does NOT
separate batches. obj_pore_eq ≈ 0.19-0.26 (null ~0.06). tex_all
S_dir ≈ 0.18-0.21 (null ~0.001), θ ≈ −4° to −11° — weak consistent
near-horizontal texture alignment. tex_si ≈ 0.10-0.12 (weak).
obj_si sits at/near its null (eq 0.28-0.35 vs null 0.20-0.25;
aw ≈ null) — Si-object orientation is at most a "possible" weak
preference. Group-stratified tex_all varies within batches
(0.175-0.316 in B1) — dependence flagged, not hidden. Histograms:
obj_pore is near-horizontal with weak bimodal shoulders (±15-25°);
the per-image axial histograms are in
`orientation_analysis/orientation_histograms.csv` — read with S,
never instead of it. Figures: `fig_orientation.png` (S_dir vs S_x
per image), `fig_orientation_overlay.png` (hue=angle overlay +
coherence map + histogram, exemplar).

## Metric-family decisions (retain / exploratory / appendix / exclude)

| family | decision | why |
|---|---|---|
| frozen recipe + thresholds + manifest | **retain** | reproducible; provenance now enforced on --reuse |
| area fractions (pore, si_candidate, uncertain-bright, bright_raw) | **retain** | least boundary/session-sensitive |
| si_contact_num_frac / si_contact_area_frac / si_area_near_pore_frac / si_pore_contact / coverage dist | **retain (corrected)** | now population-consistent; each names a distinct quantity; all carry "2-D resolved contact ≠ activity" caveats |
| contact_population flag | **retain (new)** | makes silent population mixing impossible |
| count densities (pores/mpx, Si/mpx, fines/mpx) | **exploratory** | inferred-group-organized (4% residual) |
| boundary-landing markers (D-stats, S_V, chord ratios, Clark–Evans, hotspots, cluster share, cracklike) | **exploratory** | session-sensitive; cracklike now true frame-vertical |
| tex_all/tex_si/obj_si/obj_pore S family | **retain (new, validated)** | synthetic-validated S; histograms + nulls + coverage reported with it |
| channel (InLens/ETD/SE) features | **exploratory** | batch-correlated gain + mixed SE/ETD detector pairing |
| tile SE (`*_tile_err`) | **demote → heterogeneity diagnostic** | not a jackknife, understates true uncertainty |
| DFN consequence indicators | **appendix** | assumption-dominated; stale vs corrected markers until rerun |
| fft_vh / tau_fdm / swelling_budget / recon3d | **exclude (archived)** | artefact / unmeasurable / tautological / optional |

## TeamJester — adopt / benchmark / reject

**Assessment: benchmark only — adopt nothing without re-verification.**

- Verified in available snapshot: phase-mask overlap after Inlens
  fusion (masks not disjoint — same class of defect fixed in our own
  `bright_kind_masks`).
- Prior review (`review_followup/teamjester_96a9fec/REVIEW.md`):
  "97–100% group accuracy" = train-on-all leakage (centroids fitted on
  complete dataset); false-alarm denominator wrong (35.5% claimed vs
  64.7% actual); "unseen Batch 2" contained B1 images; capacity
  censored by simulation clock (5.25 Ah ceiling); 30 draws treated as
  independent though only 27 distinct images.
- Adoptable *ideas* (leads, not code): annotation-border detection,
  pore rings/thickness, structure-tensor descriptors, blinded
  point-count review, frozen-embedding baseline.
- Rejected: their classifier accuracy claims, capacity numbers, and
  detector-fusion masks as produced.

## Deferred / blocked (visible, not dropped)

- **DFN rerun** against corrected `si_accessible_frac` + valid radius
  keys — requires explicit approval; saved outputs flagged stale.
- **Parent-held-out generalization** — blocked on crop→parent mapping.
- **TeamJester items 2-4** — need commit `57921d2` source.
- **`--fast` physical-scale check** — floors scale by downsample²
  (verified in code); full-res output is authoritative.
- **GAM/GAN reconstruction** — stays archived.

## Phase-2 addendum (CTO-feedback incorporation)

- `benchmark_results.csv` — predeclared centroid benchmark: acq_signature
  (61.3%) beats envelope (59.3%) under LOO; under leave-inferred-group-out
  nothing beats majority (54.8%). Quantifies the session confound rather
  than hiding it.
- `MARKER_SCORECARD.md` — tiered marker list: A validated descriptors,
  B unprovable batch candidates, C model-derived, X demoted.
- `build_report.py` — `exact_perm_median` NaN-guard + NaN-safe `bh()`
  (same bug class as vcompare/stats.py fixes; no NaN present in current
  feature table, so existing p-values were valid).
- `pairwise_comparisons.csv` / `loo_sweep.csv` regenerated via fixed
  stats.py (run_compare.py rerun, cached extraction).
- Corrected labels recorded in `new_image_assignment/assignment_report.md`:
  0/2 confirmed; external 76.4/79.6/97.8% scores documented as not ours.
- `si_d10_num_um` demoted to 2-D profile diagnostic (stereology caveat).
- DFN rerun on corrected markers launched (`--reuse`, same frozen recipe)
  → fresh `dfn_output_v2/dfn_*.csv`; v1 DFN outputs superseded.
