"""Physical-unit parameters for the validated comparison.

Every spatial length lives in micrometres so the identical recipe is
applied at any pixel pitch — the `px_params()` helper converts once per
image.  This is the single change that removes the 25 vs 50 nm/px
resolution drift that made earlier runs non-comparable.
"""
from __future__ import annotations

REFERENCE_BATCH = "Batch_3"
# low-contrast photos where the pipelines disagree most; kept in the
# primary analysis — omission is a reported diagnostic, not a cleanup
DISPUTED_IMAGES = ("img_4ih2ggld", "img_5n1q8atc")
# stays Si-rich under both object calibrations; needs human review
REVIEW_IMAGE = "img_f1vzngrs"

PIXEL_NM_FALLBACK = 25.0

# ---- preprocessing (physical units) -----------------------------------
FLATFIELD_SIGMA_UM = 5.0        # ~200 px at 25 nm/px
SEG_SMOOTH_SIGMA_UM = 0.0375    # ~1.5 px at 25 nm/px
OBJECT_ERODE_UM = 0.05          # interior readout erosion ~2 px at 25 nm
CONTACT_DILATION_UM = 0.075     # Si<->pore contact band ~3 px at 25 nm
WATERSHED_MIN_DIST_UM = 0.20    # peak separation ~8 px at 25 nm

# ---- resolution floors -------------------------------------------------
# MIN_BRIGHT 150 px * (0.025 um)^2 = 0.09375 um^2  (~0.35 um equiv. diam.)
# MIN_PORE    20 px * (0.025 um)^2 = 0.0125  um^2  (~0.13 um equiv. diam.)
MIN_BRIGHT_AREA_UM2 = 0.09375
MIN_PORE_AREA_UM2 = 0.0125

# ---- object classifier --------------------------------------------------
SI_CALIB_MIN_DIAM_UM = 2.0      # calibration objects: clearly particles
SI_CALIB_MIN_SOLIDITY = 0.85
SI_CORE_PERCENTILE = 5.0        # t_core = p5 of calibration interiors
SI_MIN_SOLIDITY = 0.75

# ---- spatial stats ------------------------------------------------------
N_PATCH_STRIPS = 6

SEG_SUBSAMPLE = 2_000_000       # pooled pixels for multi-Otsu

# 4-class label map
PORE, BULK, SI_CAND, UNCERTAIN = 0, 1, 2, 3

# declared primary feature set (frozen before analysis)
PRIMARY_FEATURES = (
    "si_candidate_frac",
    "uncertain_bright_frac",
    "si_d50_um",
    "si_d90_um",
    "si_clustering_R",
    "pore_frac",
    "pores_per_mpx",
    "pores_per_mpx_noise_adj",
    "pore_anisotropy",
)

FEATURE_DESCRIPTIONS = {
    "si_candidate_frac":   "area fraction classified as Si particles",
    "uncertain_bright_frac": "area fraction bright but not classifiable "
                            "as Si (ambiguous bright material)",
    "si_d50_um":           "area-weighted median Si particle diameter (um)",
    "si_d90_um":           "area-weighted 90th-pct Si diameter (um)",
    "si_clustering_R":     "Clark-Evans R; <1 = clustered, ~1 = random",
    "pore_frac":           "resolved pore area fraction",
    "pores_per_mpx":       "resolved pore objects per million pixels",
    "pores_per_mpx_noise_adj": "pore count with the reference-fitted "
                               "noise contribution removed",
    "pore_anisotropy":     "horizontal/vertical pore chord ratio",
}

N_BOOT = 10_000
FDR_ALPHA = 0.10
PERM_ALPHA = 0.05
MDD_POWER = 0.80
SEED = 0

RECIPE_VERSION = "vcompare-1.0"
