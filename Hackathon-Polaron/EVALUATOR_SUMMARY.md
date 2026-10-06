# Evaluator summary — what the pipeline found, and what it can prove

Real electrode micrographs were cropped from ~15 parent images and
deliberately organized into artificial batches. Our pipeline measures
four structural dimensions — **how much** material (area fractions),
**how it's distributed** (clustering), **its characteristic scales**
(two-point correlation), **its directions** (orientation S) — and
separates what those measurements prove from what they can't.

## Evidence table

| claim | kind | status |
|---|---|---|
| Elongated pores run near-horizontal in every batch (S_dir≈0.56-0.58 vs null 0.25; S2 x/y anisotropy=1.5 independently agrees) | **shared morphology** | validated — synthetic tests + isotropic null |
| Si loading ~6% identical in all batches | shared composition | two pipelines agree to 4 decimals |
| Si equally patchy (hotspot ~3.7-4.3×, largest cluster ~6%) | shared morphology | corrected classified-Si masks |
| ~87-91% of Si has little resolved-pore contact; ~0.1% sits within 0.15µm of a pore | shared constraint / measured blind spot | corrected identity-consistent contacts |
| B1's Si has MOST resolved-pore contact (0.48 vs 0.38/0.35) and is least enclosed (0.72 vs 0.78) | curated-batch association | corrected measurement; session-entangled |
| Pore count B1>B2>B3 (142.8/127.8/108.3 per Mpx); noise-adj B1>B3 | **curated-batch association — the only BH survivor** | p=0.0005 unblocked; n=1 shared group blocks the session test |
| B1 pores smallest (d50 0.233 vs 0.260 µm) | curated-batch association | consistent with count excess |
| InLens pore darkness B1 0.50 vs ~0.67 | source-candidate | gain-correlated, ETD null, n=3 |
| DFN: B1−B3 Si stress −3.0 MPa during discharge | **model-derived** | inside assumption spread (IQR 3.9) |
| Batch identity from markers | unresolved | acq-signature baseline (61%) BEATS the envelope (59%) LOO; under group-holdout nothing beats majority |

## The honest classification answer

The 9-feature envelope scored **0/2 on confirmed label corrections**
(3e→B1 was B2; fn→B2 was B1; xrv→B3 unconfirmed). We flagged each
prediction `cant_tell_session_matched` before ground truth — the
confound was pre-declared, not discovered afterward. The quantitative
benchmark (`benchmark_results.csv`) shows why: the acquisition
signature alone outperforms the material envelope; under
leave-inferred-group-out nothing beats majority class. **The pipeline
measures structure reliably; it cannot prove material provenance from
these curated, session-entangled crops.**

## What was fixed to get here (evidence, not vibes)

9 reproduced-and-repaired defects incl.: contact-fraction denominator
mixing (0.524→0.371 on exemplar), 70% channel-mask area loss,
perpendicular crack population, elementwise BH, NaN→p=0, session
signature leakage, stale DFN inputs. Fresh DFN rerun on corrected
markers: B1−B3 Si stress −3.0 MPa (within assumption spread). See
`AUDIT_LEDGER.md` and `MARKER_SCORECARD.md`.

## Remaining gaps (named, not hidden)

- No crop→parent mapping → generalization untestable; inferred groups
  are strata, not confirmed sessions.
- No EDS → 'silicon' is a brightness label.
- 2-D sections → no 3-D connectivity claims; D10-type profile sizes are
  diagnostics, not particle diameters.
- Blind-test protocol staged for the 6 incoming images
  (`new_image_assignment/BLIND_TEST_PROTOCOL.md`): predictions committed
  before labels, with the acquisition-signature control alongside.
