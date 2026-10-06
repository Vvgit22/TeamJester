# Hackathon-Polaron eval — blind batch-assignment report

Source: `~/Downloads/Hackathon_Context/Hackathon-Polaron-eval` — 6 fields
× 3 channels (BSE/ETD/Inlens), 25 nm/px, staged read-only via
`eval6/input/Batch_eval/` symlinks. Arrival hashes in
`arrival_hashes.txt` (18 files, recorded before processing).

Run per `new_image_assignment/BLIND_TEST_PROTOCOL.md`: frozen recipe
(`validated_comparison/recipe.json` = `dfn_output/recipe.json`,
t_pore=0.7109, t_si=1.3354, t_core=1.5495, fitted on Batch_3 only).
Predictions committed **before any labels** —
`new6_predictions.csv`, md5 `55afc7271e8c69944d13a026be34bf4f`,
manifest in `prediction_manifest.json`.

## Predictions (committed blind)

| image | envelope pick | coverage B1/B2/B3 | median-z | acq baseline | frame group | confounded? |
|---|---|---|---|---|---|---|
| img_0eryguqq | Batch_3 | 6/6/7 | B3 | B3 | B3 only | **yes — call may be session-matched** |
| img_4hq27w4c | **Batch_1 (9/9)** | 9/8/6 | B1 | B1 | B1+B2 | no — partially separable |
| img_fhwrjtet | Batch_3 (7/9) | 6/6/7 | **B1** | B3 | B3 only | **yes — and methods disagree** |
| img_fspqbkxl | inconclusive 1_2 | 9/9/7 | B1 | B1 | B1+B2 | no — honestly inconclusive |
| img_soo2ax3r | inconclusive 1_3 | 9/7/9 | B1 | B1 | B1+B2 | no — honestly inconclusive |
| img_y59rxmxl | inconclusive 1_3 | 9/7/9 | B1 | B1 | B1 only | **yes — group is B1-only** |

Session flags: `0eryguqq`, `fhwrjtet` (1612 px — only Batch_3 has this
frame), `y59rxmxl` (1880 px — only Batch_1). A correct label on those
three cannot separate material from session — declared in advance.
`4hq27w4c`, `fspqbkxl`, `soo2ax3r` sit in mixed B1/B2 frame groups where
the two can partially disagree.

Envelope and acq baseline **agree on every conclusive call** — so even
the correct-looking picks are consistent with session recognition. The
only disagreement between methods: `fhwrjtet` (envelope B3 at 7/9 vs
median-z B1) — treat as weak.

## Where the eval images sit vs the labelled batches

| metric | eval range | B1 / B2 / B3 medians |
|---|---|---|
| pore_frac | 0.077–0.110 | 0.104 / 0.108 / 0.109 |
| si_candidate_frac | 0.042–0.074 | 0.060 / 0.061 / 0.060 |
| pores_per_mpx | 114–160 | 142.8 / 127.8 / 108.3 |
| pore_d50_um | 0.219–0.265 | 0.233 / 0.244 / 0.260 |
| si_clustering_R | 0.635–0.786 | 0.677 / 0.693 / 0.665 |
| noise_mad | 9.9–11.0 | 11.1 / 10.6 / 9.8 |

Notable: `y59rxmxl` has the lowest Si fraction (0.042) and is flagged
`is_problem_photo` (low si_bulk_contrast 2.17) — Si undercount risk;
its "inconclusive" is the honest label. `4hq27w4c` has the most
extreme pores/mpx (160) and highest Si frac (0.074) — it reads
B1-like on both counts; it is also the only 9/9 envelope hit.

## What this run fixed

`micro2dfn/report.py` crashed on single-batch runs (empty `deltas` →
`KeyError: 'clear'`). Patched: `clear` guarded when no pairwise
comparisons exist. Re-run via `--reuse` produced the report.

## Outputs

- `eval6/new6_predictions.csv` + `prediction_manifest.json` — committed blind
- `eval6/arrival_hashes.txt` — 18 file md5s
- `eval6/envelope/` — feature_table, assignments, report, cache
- `eval6/markers/` — corrected micro2dfn markers/objects/report/figs
- `eval6/input/Batch_eval/` — symlinks (not copies) into the source dir

## To score when labels land

Compare `envelope_pick` (and `acq_baseline_pick`) vs truth; report
N/6, per-class recall, and whether envelope beat its own acq baseline.
On the confounded three, a correct call is not evidence of material
matching — that was declared before prediction. No retroactive tuning.
