# micro2dfn — microstructure markers & DFN consequence report

**What this is.** SEM cross-section photos of a silicon–graphite battery anode were colour-coded into three materials — pores (black), graphite (grey), silicon (bright) — using **one shared set of brightness cutoffs** for every photo, so no batch can re-calibrate itself into looking normal. From those maps we measured ~30 structural markers per image, then fed them into the standard PyBaMM Doyle–Fuller–Newman battery model as consequence *indicators*.

**Honesty rules.** Numbers are reported as batch *differences* with 95% CIs — the defensible signal. Absolute DFN outputs carry stated assumptions and are illustrative. Nothing here predicts cycle life or guarantees failure. Every value traces back to a marker, a formula, and an overlay image.

## Photo-quality check

**1 low-contrast photos flagged** — silicon may be over-counted in them (the object classifier separates classified Si particles from uncertain-bright material; check the overlays):

- `Batch_eval/img_y59rxmxl` (si_bulk_contrast=2.17, bright_fine_frac=0.014)

## Segmentation settings (frozen)

- Shared thresholds: `t_pore=0.7109`, `t_si=1.3354` — fitted on the baseline batch **Batch_3** only, saved in `recipe.json`, and reused verbatim on later runs. A newly added batch can never change how existing batches are measured; `run_manifest.json` records the recipe md5, code md5s and every input image md5 for this exact run.
- Si/bright-fine classifier cutoff: `t_core=1.550` (5th percentile interior brightness of large, compact particles, calibrated on baseline objects only).
- Resolution floor: Si objects < 150 px and pores < 20 px (~0.35 um) are merged into bulk — same rule for every image.
- **Cached measurements reused** (`--reuse`): markers and objects loaded from `markers_all.csv`/`objects_all.csv` written by the run recorded in `run_manifest.json`.

## Marker summary per batch

Median [IQR] per batch. Full per-image values in `markers_<batch>.csv`; column meanings in `data_dictionary.csv`.

| Marker | Batch_eval |
|---|---|
| Resolved porosity (image-visible pores) | 0.1007 [0.09,0.108] |
| Silicon fraction (of coating) | 0.05857 [0.0534,0.0612] |
| Ambiguous bright-material fraction | 0.01514 [0.014,0.019] |
| Si particle diameter, median (area-weighted) | 2.573 [2.43,2.79] |
| Si particle diameter, 90th pct (area-weighted) | 5.083 [4.48,5.23] |
| Si particle radius (3D estimate) | 1.725 [1.61,1.83] |
| Si surface area per volume | 0.604 [0.436,0.64] |
| Si clustering index (Clark-Evans R) | 0.6643 [0.649,0.725] |
| Graphite effective particle radius | 3.328 [3.13,3.45] |
| Graphite flake alignment (h/v) | 1.215 [1.2,1.26] |
| Pore anisotropy (flat vs upright) | 1.217 [1.21,1.24] |
| Vertical crack fraction | 0.01028 [0.00934,0.0118] |
| Pore connectivity (2D reach) | 0.02858 [0.0217,0.071] |
| Largest connected pore region | 0.05487 [0.0464,0.0638] |
| Effective Bruggeman exponent | 1.268 [1.2,1.37] |
| Si-to-pore distance, mean | 0.5465 [0.514,0.556] |
| Low-coverage Si share | 0.8466 [0.833,0.873] |

## Batch differences

No pair–marker difference survives Benjamini–Hochberg correction (FDR 0.10).

Nominal (uncorrected) p<0.05 count: 0 of 0 tests — compare against ~0.0 expected by chance. `mdd` is the smallest median difference detectable at ~5%: smaller observed gaps are under-powered, not proven absent. These are UNBLOCKED tests — acquisition session can organise them; the stratified within-session test is in `build_report.py` (`blocked_permutation.csv`).

All pairwise differences are in `batch_differences.csv`.

## Assumed (not measured) parameters

| Parameter | Value | Why assumed |
|---|---|---|
| Electrode thickness | 75 um [65-85 swept] | foil & coating top not in frame |
| Sub-resolution porosity | +0.15-0.30 | pores below ~0.35 um are invisible |
| Si active share | classified Si x accessible share -> all uncertain bright counted | label uncertainty treated as an explicit bracket; 'all-Si-active' variant run separately |
| Si Young's modulus / Poisson ratio | 50 GPa [35-90] / 0.25 [0.22-0.28] | Bonkile2024 cited values, swept over range |
| Si mechanics block | Bonkile2024 | swappable — if EDS shows the bright phase is SiOx, refit (`_si_block` in simulate.py) |
| Bruggeman default | 1.5 | literature value when tau proxy degenerates |
| Cathode thickness | rescaled per run to hold reference N/P | keeps min-anode-potential meaningful under assumed geometry |
| Degradation constants | OKane2022 published (LAM 2.7778e-7 s-1, SEI k 1e-12 m/s) | audit table in `dfn_validation.md` |
| Other material constants | Chen2020_composite | diffusivities, kinetics, densities not image-measurable |

## Not measurable from these images

Binder distribution (no BSE contrast), SEI layer, lithium inventory, 3-D pore connectivity / electrolyte wetting (2-D sections only — see the optional reconstruction branch), foil corrosion.

**Note on tortuosity.** In every image the resolved pore network does not form a connected path across the section, so a diffusion-solve tortuosity cannot be measured on 2-D cuts — the through-plane network lives largely in sub-resolution pores. Directional markers (pore anisotropy, geodesic proxy, Bruggeman-equivalent exponent) carry the usable signal.

## How every number was produced

```
BSE TIFF -> flat-field (Gaussian background)
  -> shared multi-Otsu thresholds (frozen to thresholds.json)
  -> watershed split + Si/bright-fine object classification
  -> per-image stereological markers (this report)
  -> per-batch median/IQR + bootstrap CIs
  -> PyBaMM DFN sweep over marker bands -> indicators
```

Files: `markers_*.csv` (per image), `objects_*.csv` (per Si object), `data_dictionary.csv` (every column explained), `dfn_params_*.json` (exact simulator inputs), `dfn_results.csv` (every sweep run), `figs/` (distributions, overlays, bands, tornado), `micro2dfn_results.xlsx` (all tables).
