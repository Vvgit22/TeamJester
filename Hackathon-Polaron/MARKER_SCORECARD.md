# Marker scorecard — which measurements matter, and how we can prove it

Batch medians from corrected outputs: `dfn_output_v2/` (micro2dfn),
`validated_comparison/` (vcompare), `spatial_features_v2.csv`,
`orientation_analysis/`, `channel_features.csv`. Stat tables regenerated
with corrected BH/NaN handling. Batch medians [B1 / B2 / B3]; n = 7 / 7 / 17.

**Headline:** no marker clears the declared minimum-detectable-difference
threshold for batch discrimination (`dfn_output_v2/batch_differences.csv`:
0 markers `clear=True`; unblocked BH q=0.10: 0 survivors; blocked
within-session test underpowered — B1-vs-B3 shares only 1 inferred group).
What we can stand behind: **validated shared morphology + corrected
contact-structure ordering + one session-entangled pore-count candidate.**

## Tier A — validated descriptors (highest confidence; describe, don't discriminate)

| marker | B1 / B2 / B3 | finding | proof |
|---|---|---|---|
| pore orientation `S_dir` (obj_pore_aw) | 0.585 / 0.563 / 0.573 | elongated pores near-horizontal (θ≈−3°) in ALL batches — shared morphology, not a discriminator | synthetic known-answer tests + isotropic null p95≈0.25 (`tests/test_orientation.py`) |
| `si_candidate_frac` | 0.0595 / 0.0614 / 0.0603 | same Si loading ~6% everywhere; kills 'B1 excess Si' alarm | two independent pipelines agree to 4 decimals (frozen ruler) |
| `si_contact_area_frac` (= `si_accessible_frac`) | 0.483 / 0.378 / 0.354 | B1's Si has MOST resolved-pore contact — ordering changed vs pre-correction (was 0.59/0.60/0.58) | identity-preserving fix, reproduced to 6 decimals, `tests/test_si_contact.py` |
| `si_enclosed_share` | 0.720 / 0.778 / 0.781 | B1's Si least enclosed — consistent with more/smaller pores | same fix |
| `si_lowcoverage_share` | 0.867 / 0.882 / 0.906 | ~87–91% of Si-area has little pore coverage — sub-resolution porosity is a measured blind spot everywhere | corrected contact population |
| shared patchiness | `si_hotspot_ratio` 3.75 / 3.78 / 4.29; `largest_si_cluster_frac` 0.058 / 0.064 / 0.069 | equally patchy, no mega-cluster, no batch signature | corrected classified-Si rasterization |
| `pore_frac_resolved` | 0.104 / 0.108 / 0.109 | same resolved porosity | frozen recipe |
| `pore_largest_region_frac` | 0.045 / 0.041 / 0.058 | B1/B2 pore networks less dominated by one region than B3's | corrected `label()` fix |
| swelling deficit | all batches negative | local pores can't buffer nominal Si expansion — real, quantified constraint | unchanged marker |

## Tier B — batch candidates (real differences in crops, unprovable as material)

| marker | B1 / B2 / B3 | evidence | why not conclusive |
|---|---|---|---|
| `pores_per_mpx` | 142.8 / 127.8 / 108.3 (noise-adj 134.9 / 120.3 / 116.1) | **only BH-survivor anywhere**: B1>B3 +34.5 (p=0.0005), B2>B3 +19.5 (p=0.010), noise-adj B1>B3 (p=0.0019) | least group-contaminated marker (4% group-variance share) BUT blocked test n=1 shared group B1-B3 — session confound untestable |
| `pore_d50_um` | 0.233 / 0.244 / 0.260 | B1 smallest pores — 'more, smaller pores' holds | same session entanglement (6% group share) |
| `si_clustering_R` | 0.677 / 0.693 / 0.665 | B1 Si marginally more clumped than B2 (R<1 = clustered); `si_patchiness` agrees (0.354 / 0.315 / 0.283) | ~2% effect, below MDD |
| `inl_pore_darkness` (InLens) | 0.50 / 0.66 / 0.69 | p=0.0004 unblocked | InLens gain batch-correlated; ETD null; n=3 sessions — candidate only |

## Benchmark — do these markers classify? (`benchmark_results.csv`)

Predeclared, nearest-batch-centroid, train-fold scalings; 31 images.

| protocol | best honest set | envelope | acq_signature | majority |
|---|---|---|---|---|
| LOO | frac+cluster 51.6% | 59.3% (bal 39.8) | **61.3% (bal 48.5)** | 54.8% |
| LOGO-inferred | frac+cl+corr 41.9% | 54.2% (bal 28.3) | 38.7% (bal 34.7) | 54.8% |

Read: **the acquisition signature alone beats the material envelope
under LOO** — the pipeline sees session more than material. Under
leave-inferred-group-out, nothing beats majority class. Fractions alone
(12.9%) carry no class signal — consistent with ~6% Si everywhere.
Orientation hurts classification — correct for a shared-morphology
feature. Classification is a test of the markers, not the point of them.

## Tier C — correlation scale + model-derived (fresh, corrected markers)

**S2 directional (`corr_analysis/s2_summary.csv`):** pore correlation
length is **1.5× longer along image-x than image-y in every batch**
(len_x≈0.38-0.40 µm vs len_y≈0.25 µm, anisotropy=1.5) — an independent
correlation-domain confirmation of the near-horizontal pore orientation.
Bright-phase anisotropy weaker (1.18-1.30), shared. Batch medians
identical — shared structure, not a discriminator.

**PCF g(r) vs CSR envelope:** Si centroids cluster at ~0.75 µm scale in
all images (g_peak 5.4-7.2, all above the CSR envelope) — expected for
packed finite-size particles; the CSR null is naive under packing and
the envelope is reported, not hidden. No batch signature in peak
position.

**DFN, corrected markers (`dfn_output_v2/dfn_paired_differences.csv`):**
peak Si surface stress during discharge, B1−B3 paired diff **−3.0 MPa**
(CI −6.02, −0.02, verdict meaningful_difference) — direction consistent
with B1's higher corrected pore-contact share spreading lithiation over
more particles. BUT the diff sits **inside the model's assumption-only
spread (IQR 3.9 MPa, exceeds=False)** — a model-derived indicator, not a
measurement. Capacity and swelling: below declared thresholds everywhere.

## Tier X — demoted (kept for record, not evidence)

- `si_d10_num_um` / minimum-size claims — 2-D profile diagnostic only (stereology: grazing cuts fake small particles).
- 'vertical calendering texture' — FFT test withdrawn (measured frame aspect ratio); corrected result is near-horizontal pores.
- `cracklike_frac` — definition-sensitive: micro2dfn `crack_frac_v` (0.011/0.016/0.013) vs spatial thin-vertical (0.019/0.013/0.014) disagree on ordering — report per-definition or drop.
- 'uncertain-bright at or above Si brightness' — false in B1 (InLens 1.395 < 1.459; ETD 1.410 < 1.536); true only in B3.
- tile-'jackknife' — renamed tile standard error; understates uncertainty (correlated tiles).
- DFN `si_accessible`-linked indicators from `dfn_output/` (v1) — superseded by v2.

## What we cannot test

Parent-level generalization (no crop→parent map; sibling crops
non-independent), chemistry (BSE = brightness, not Si), 3-D connectivity
from 2-D sections, manufacturing causality. The three new images:
predictions 3e→B1 (truth B2), fn→B2 (truth B1) = **0/2 confirmed**; our
own `cant_tell_session_matched` flag predicted this failure mode.
xrv→B3 unconfirmed.
