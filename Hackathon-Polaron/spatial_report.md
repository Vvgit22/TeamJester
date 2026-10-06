# Spatial heterogeneity — the defect-risk signals

All values from the frozen vcompare recipe — **diagnostic/exploratory layer**: these markers depend on where object boundaries land and none survive acquisition blocking, so they are not batch markers (see `marker_session_partition.csv`). `top`/`bottom` are frame edges; the foil is not in frame and the direction-to-physical-axis mapping is unconfirmed (the earlier FFT-based orientation claim was withdrawn — see `archive/ARCHIVE.md`).

Two bright populations are reported separately (v2): `bright_*` = ALL segmented bright material; `si_*` = classified si_particle objects only, rasterized at exact watershed identity. `cracklike_frac` now tests the skimage row-axis convention correctly (within 30 deg of frame-vertical — the v1 test selected near-horizontal objects while calling them vertical). Batch medians [min-max]:

| signal | Batch_1 | Batch_2 | Batch_3 | New |
|---|---|---|---|---|
| bright_topbot_ratio | 0.903 [0.433,1.323] | 1.099 [0.580,2.377] | 0.945 [0.657,2.238] | 1.256 [0.958,1.460] |
| bright_depth_slope | -0.002 [-0.006,0.015] | -0.001 [-0.015,0.005] | -0.000 [-0.015,0.007] | -0.005 [-0.008,-0.002] |
| bright_hotspot_ratio | 2.723 [2.310,4.920] | 2.907 [2.457,4.260] | 3.119 [2.241,5.428] | 2.509 [1.992,4.522] |
| bright_maxpatch_frac | 0.236 [0.177,0.283] | 0.237 [0.184,0.281] | 0.205 [0.147,0.431] | 0.204 [0.185,0.244] |
| bright_lr_asym | 0.004 [0.001,0.035] | 0.008 [0.003,0.024] | 0.009 [0.001,0.047] | 0.014 [0.007,0.023] |
| pore_topbot_ratio | 1.032 [0.774,1.294] | 0.970 [0.659,1.360] | 0.899 [0.515,1.829] | 1.333 [0.520,1.728] |
| pore_depth_slope | -0.002 [-0.006,0.005] | -0.002 [-0.006,0.008] | 0.001 [-0.010,0.013] | -0.003 [-0.007,0.014] |
| pore_hotspot_ratio | 1.792 [1.657,2.288] | 2.151 [1.594,2.296] | 2.029 [1.576,2.663] | 1.814 [1.602,1.838] |
| unc_share_of_bright | 0.165 [0.118,0.684] | 0.171 [0.131,0.203] | 0.170 [0.077,0.446] | 0.278 [0.157,0.584] |
| si_topbot_ratio | 0.945 [0.408,1.613] | 0.942 [0.708,2.142] | 1.077 [0.611,2.614] | 1.192 [1.032,1.371] |
| si_depth_slope | -0.001 [-0.007,0.012] | -0.000 [-0.009,0.001] | -0.002 [-0.012,0.008] | -0.001 [-0.007,-0.001] |
| si_hotspot_ratio | 3.747 [2.464,8.978] | 3.779 [3.063,7.569] | 4.290 [2.400,9.077] | 3.305 [2.613,4.030] |
| si_maxpatch_frac | 0.160 [0.116,0.275] | 0.200 [0.152,0.281] | 0.164 [0.113,0.429] | 0.119 [0.087,0.199] |
| si_lr_asym | 0.010 [0.004,0.037] | 0.014 [0.009,0.035] | 0.011 [0.001,0.048] | 0.012 [0.010,0.019] |
| largest_si_cluster_frac | 0.058 [0.048,0.197] | 0.064 [0.051,0.084] | 0.069 [0.053,0.120] | 0.063 [0.047,0.071] |
| cracklike_frac | 0.019 [0.010,0.030] | 0.013 [0.007,0.027] | 0.014 [0.004,0.034] | 0.017 [0.011,0.021] |
| si_near_pore_frac | 0.015 [0.008,0.061] | 0.013 [0.009,0.030] | 0.012 [0.003,0.022] | 0.011 [0.008,0.059] |

## Reading the signals

- `*_hotspot_ratio` high = one patch carries much more of that phase than typical -> uneven loading, local swelling stress. `bright_*` includes uncertain material; `si_*` is the classified population.
- `largest_si_cluster_frac` = share of classified Si that is ONE connected region — the 'enormous continuous cluster' case.
- `*_topbot_ratio` != 1 = phase segregated top-to-bottom in the frame (drying/calendering hypothesis only — physical direction unconfirmed).
- `cracklike_frac` = share of pore area in thin objects whose major axis sits within 30 deg of frame-vertical — crack-like rather than round voids. Caveat: streaking can also be a sectioning artefact, it is session-sensitive, and the earlier version of this metric measured the perpendicular population.
- `si_near_pore_frac` = classified Si within 0.15 µm of a resolved pore in this 2-D slice — a measured blind spot (sub-resolution pores dominate real porosity), not a batch marker.
- `unc_share_of_bright` = uncertain-bright share of the bright area — the abstention category's footprint.