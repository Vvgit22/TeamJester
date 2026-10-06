# Multi-detector channel analysis (InLens + ETD) — EXPLORATORY

Not part of the frozen QC recipe. BSE is atomic-number contrast; InLens/ETD are secondary-electron (surface-sensitive) channels. Registration verified (0 px phase-correlation shift on every image).

**Session caveat (primary):** InLens gain differs by batch, so every channel feature inherits the acquisition confound. Masks are now rasterized at exact watershed identity (mask_coverage ~0.92-0.95; was ~27-31% under centroid matching). These are exploratory follow-up signals, not batch markers.

## Batch medians

| feature | Batch_1 | Batch_2 | Batch_3 | New_Images_Batch |
|---|---|---|---|---|
| mask_coverage | 0.939 | 0.916 | 0.947 | 0.943 |
| inl_pore_mean | 0.528 | 0.684 | 0.840 | 0.662 |
| inl_bulk_mean | 1.046 | 1.059 | 1.223 | 1.065 |
| inl_si_mean | 1.459 | 1.497 | 1.789 | 1.544 |
| inl_unc_mean | 1.395 | 1.859 | 2.010 | 1.484 |
| inl_pore_darkness | 0.495 | 0.656 | 0.689 | 0.621 |
| inl_unc_si_like | 0.804 | 1.333 | 1.844 | 1.020 |
| inl_edge_density | 0.100 | 0.108 | 0.125 | 0.105 |
| etd_pore_mean | 0.204 | 0.211 | 0.195 | 0.202 |
| etd_bulk_mean | 1.026 | 1.030 | 1.026 | 1.030 |
| etd_si_mean | 1.536 | 1.570 | 1.554 | 1.562 |
| etd_unc_mean | 1.410 | 1.487 | 1.580 | 1.428 |
| etd_pore_darkness | 0.198 | 0.204 | 0.188 | 0.192 |
| etd_unc_si_like | 0.737 | 0.844 | 1.027 | 0.736 |
| etd_edge_density | 0.107 | 0.107 | 0.098 | 0.103 |
| inl_std_si | 0.156 | 0.173 | 0.185 | 0.159 |
| inl_std_unc | 0.193 | 0.298 | 0.277 | 0.258 |
| inl_std_bulk | 0.151 | 0.173 | 0.219 | 0.169 |

## What the channels say

1. **InLens pore-contrast — possible, n=3.** Batch_1's pores read darkest in InLens in the sessions it shares with another batch (`inl_pore_darkness` ~0.50 vs ~0.66-0.69). A candidate follow-up signal only: InLens gain is batch-correlated, ETD shows no batch trend, and this is NOT a measured pore depth or 'more open voids'.
2. **Uncertain-bright material is bright material, not bulk misread** — in surface channels it sits at or above classified-Si brightness, with ~2x the local texture. Consistent with thin/edge-rich bright material rather than solid grains. Validates the separate uncertain label; does NOT establish silicon identity (edges/topography also read bright) — the all-bright upper bracket stays a bracket.
3. **Removed:** the FFT 'vertical texture'/curtaining test measured frame aspect ratio, not texture (see archive/ARCHIVE.md; replaced by the validated S-parameter analysis in orientation_analysis/).

## What the channels still cannot do

- chemical identity (still needs EDS)

- absolute calibration across sessions without acquisition metadata (gain/brightness settings not in TIFF tags we checked)

- they corroborate the frozen-ruler labels but do not replace them
