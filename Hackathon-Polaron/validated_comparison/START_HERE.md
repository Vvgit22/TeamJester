# Validated batch comparison — start here

**What this is:** a re-measurement of the 31 BSE cross-sections under one
recipe frozen on the reference batch (Batch_3, shipment-approved
*selected reference* — not proven defect-free). It answers whether
batch differences survive measurement uncertainty; it does not measure
quality, safety, or cell performance.

## 1. What differences did we measure?

Across 9 declared measurements (Si candidate fraction, uncertain-bright
fraction, Si sizes D50/D90, Si clustering, pore fraction, pore count —
raw and noise-adjusted — and pore anisotropy), comparing all batch pairs
with exact permutation tests (every possible split enumerated — no
random seeds) and Benjamini–Hochberg correction.

## 2. Which survive the image and statistical checks?

**Differences supported under the checked assumptions:**
  - Batch_1-Batch_3: pores_per_mpx (median diff +34.5, exact p=0.0005)
  - Batch_1-Batch_3: pores_per_mpx_noise_adj (median diff +18.77, exact p=0.0019)

## 3. Which depend on uncertain pictures or labels?

**Possible difference — image check needed:**
  - Batch_2-Batch_3: pores_per_mpx (median diff +19.48, exact p=0.0101)

(A raw pore-count excess marked "possible" means it did not survive
noise adjustment: the photos in that batch are noisier, and pore count
rises with noise. The adjusted version is the one to trust.)

2 Batch_1 photos are unusually low-contrast; the two existing
pipelines disagree by up to ~11 percentage points on how much of their
bright material is silicon. The review sheet in `panels/` lists crops for
human labelling — without independent chemistry (e.g. EDS), the Si
fraction in those regions stays *uncertain bright material*, counted
separately above.

**No clear difference detected** (does NOT prove equivalence — with 7
photos per batch, differences below the listed threshold are simply
invisible to these tests):
  - Batch_1-Batch_3 si_candidate_frac: undetectable below ~0.0236
  - Batch_1-Batch_3 uncertain_bright_frac: undetectable below ~0.0153
  - Batch_1-Batch_3 si_d50_um: undetectable below ~0.548
  - Batch_1-Batch_3 si_d90_um: undetectable below ~1.04
  - Batch_1-Batch_3 si_clustering_R: undetectable below ~0.0752
  - Batch_1-Batch_3 pore_frac: undetectable below ~0.0312
  - Batch_1-Batch_3 pore_anisotropy: undetectable below ~0.0839
  - Batch_2-Batch_3 si_candidate_frac: undetectable below ~0.0148
  - Batch_2-Batch_3 uncertain_bright_frac: undetectable below ~0.00973
  - Batch_2-Batch_3 si_d50_um: undetectable below ~0.469
  - Batch_2-Batch_3 si_d90_um: undetectable below ~1.46
  - Batch_2-Batch_3 si_clustering_R: undetectable below ~0.0975
  - Batch_2-Batch_3 pore_frac: undetectable below ~0.0267
  - Batch_2-Batch_3 pores_per_mpx_noise_adj: undetectable below ~12
  - Batch_2-Batch_3 pore_anisotropy: undetectable below ~0.0778
  - Batch_1-Batch_2 si_candidate_frac: undetectable below ~0.0126
  - Batch_1-Batch_2 uncertain_bright_frac: undetectable below ~0.0116
  - Batch_1-Batch_2 si_d50_um: undetectable below ~0.59
  - Batch_1-Batch_2 si_d90_um: undetectable below ~1.83
  - Batch_1-Batch_2 si_clustering_R: undetectable below ~0.0464
  - Batch_1-Batch_2 pore_frac: undetectable below ~0.0288
  - Batch_1-Batch_2 pores_per_mpx: undetectable below ~65.3
  - Batch_1-Batch_2 pores_per_mpx_noise_adj: undetectable below ~64.5
  - Batch_1-Batch_2 pore_anisotropy: undetectable below ~0.083

## 4. What single extra measurement would most help?

- *Si identity:* an EDS map on any disputed region → resolves the
  bright-material label outright.
- *Pore-count noise:* one low-dose/low-noise repeat image per batch →
  tests whether the noise-adjusted ordering holds.
- *Independent quality verdict:* any measurement independent of these
  images (e.g. electrochemical half-cell capacity) → calibrates what the
  image markers actually predict.

## QC recheck (corrected reproduction of the original pipeline)

With reference-fitted weights and held-out baseline calibration:
Batch_1: INVESTIGATE ; Batch_2: INVESTIGATE. The original "zero false alarms" claim is wrong: 1/17
reference images exceed the flag threshold under leave-one-out scoring.

*All comparisons are indicators about these images under the stated
recipe — not predictions of cell behaviour.*
