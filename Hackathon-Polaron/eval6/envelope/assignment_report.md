# New-image batch assignment — ALL CALLS: "CAN'T TELL"

**Status (acquisition analysis):** each new photo's frame height occurs in only one batch's acquisition group, and each call below followed that session — the assignments cannot separate batch-match from session-match. The protocol (predictions saved blind before any ground truth) is kept; the verdicts are relabelled "can't tell" until session-controlled data exists. Do not quote the assigned column as material evidence.

Method (v2): primary rule = envelope coverage — count of the 9 declared features inside each batch's observed min-max range (unbiased by batch spread). Exactly one batch containing 9/9 => that batch; several => inconclusive; none => best coverage wins unless median robust-z >2.5 => out-of-distribution. Median-z kept as a secondary score (it favours wide batches — see `medianz_winner` in assignments.csv). Recipe frozen on Batch_3 (`validated_comparison/recipe.json`).

| image | assigned | inside env. (B1/B2/B3) | median-z best | confidence |
|---|---|---|---|---|
| img_0eryguqq | Batch_3 | 6/6/7 | Batch_3 0.65 | best envelope coverage 7/9 (median-z 0.65) |
| img_4hq27w4c | Batch_1 | 9/8/6 | Batch_1 0.72 | envelope-consistent (9/9 features inside Batch_1; Batch_2 8/ |
| img_fhwrjtet | Batch_3 | 6/6/7 | Batch_1 0.75 | best envelope coverage 7/9 (median-z 0.92) |
| img_fspqbkxl | inconclusive_between_1_2 | 9/9/7 | Batch_1 0.15 | inside multiple batch envelopes — the batches overlap and th |
| img_soo2ax3r | inconclusive_between_1_3 | 9/7/9 | Batch_1 0.52 | inside multiple batch envelopes — the batches overlap and th |
| img_y59rxmxl | inconclusive_between_1_3 | 9/7/9 | Batch_1 0.47 | inside multiple batch envelopes — the batches overlap and th |

## Per-image notes

### img_0eryguqq → Batch_3 (best envelope coverage 7/9 (median-z 0.65))
- vs Batch_1: 6/9 features inside envelope; median-z 0.96
- vs Batch_2: 6/9 features inside envelope; median-z 1.07
- vs Batch_3: 7/9 features inside envelope; median-z 0.65
- largest deviations vs Batch_3: si_clustering_R z=2.2; pore_anisotropy z=1.2; pore_frac z=1.0
- key features: pore_frac=0.088, pores/mpx=114 (noise-adj 113), Si cand=0.052, uncertain=0.028, Si d50=2.62 um, R=0.79

### img_4hq27w4c → Batch_1 (envelope-consistent (9/9 features inside Batch_1; Batch_2 8/9; Batch_3 6/9))
- vs Batch_1: 9/9 features inside envelope; median-z 0.72
- vs Batch_2: 8/9 features inside envelope; median-z 1.66
- vs Batch_3: 6/9 features inside envelope; median-z 1.01
- largest deviations vs Batch_1: si_clustering_R z=6.0; pore_frac z=1.6; uncertain_bright_frac z=1.0
- key features: pore_frac=0.077, pores/mpx=160 (noise-adj 153), Si cand=0.074, uncertain=0.023, Si d50=2.84 um, R=0.64

### img_fhwrjtet → Batch_3 (best envelope coverage 7/9 (median-z 0.92))
- vs Batch_1: 6/9 features inside envelope; median-z 0.75
- vs Batch_2: 6/9 features inside envelope; median-z 0.82
- vs Batch_3: 7/9 features inside envelope; median-z 0.92
- largest deviations vs Batch_3: si_d50_um z=1.7; pore_anisotropy z=1.6; uncertain_bright_frac z=1.6
- key features: pore_frac=0.096, pores/mpx=121 (noise-adj 119), Si cand=0.061, uncertain=0.034, Si d50=3.04 um, R=0.74

### img_fspqbkxl → inconclusive_between_1_2 (inside multiple batch envelopes — the batches overlap and this image cannot be separated)
- vs Batch_1: 9/9 features inside envelope; median-z 0.15
- vs Batch_2: 9/9 features inside envelope; median-z 0.58
- vs Batch_3: 7/9 features inside envelope; median-z 0.22
- largest deviations vs Batch_1: si_clustering_R z=4.4; uncertain_bright_frac z=1.4; pores_per_mpx_noise_adj z=0.3
- key features: pore_frac=0.106, pores/mpx=150 (noise-adj 142), Si cand=0.061, uncertain=0.025, Si d50=2.53 um, R=0.65

### img_soo2ax3r → inconclusive_between_1_3 (inside multiple batch envelopes — the batches overlap and this image cannot be separated)
- vs Batch_1: 9/9 features inside envelope; median-z 0.52
- vs Batch_2: 7/9 features inside envelope; median-z 1.13
- vs Batch_3: 9/9 features inside envelope; median-z 0.56
- largest deviations vs Batch_1: si_clustering_R z=7.5; si_d90_um z=1.0; pore_anisotropy z=0.7
- key features: pore_frac=0.110, pores/mpx=128 (noise-adj 120), Si cand=0.056, uncertain=0.014, Si d50=2.37 um, R=0.63

### img_y59rxmxl → inconclusive_between_1_3 (inside multiple batch envelopes — the batches overlap and this image cannot be separated)
- vs Batch_1: 9/9 features inside envelope; median-z 0.47
- vs Batch_2: 7/9 features inside envelope; median-z 0.48
- vs Batch_3: 9/9 features inside envelope; median-z 0.50
- largest deviations vs Batch_1: si_d90_um z=0.9; si_candidate_frac z=0.9; pores_per_mpx_noise_adj z=0.6
- key features: pore_frac=0.108, pores/mpx=127 (noise-adj 120), Si cand=0.042, uncertain=0.019, Si d50=2.38 um, R=0.68

## Caveats

- Assignment is similarity, not provenance: batches overlap on every feature, so weak-confidence calls are expected for images near the overlap region.
- With 7 images in Batch_1/2 and 17 in Batch_3, envelope estimates are noisy; scores carry that uncertainty.
- The frozen recipe segments BSE only; InLens/ETD channels are recorded but not used (channel comparability not yet established).
- Session confound: the calls follow each photo's acquisition group; they measure similarity to that session's batch, not provenance. Verdicts are "can't tell" until controlled re-imaging exists.