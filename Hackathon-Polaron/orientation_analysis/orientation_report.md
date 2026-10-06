# 2-D orientational order (S) — morphology, not crystallography

S_x_2d = <w cos 2(theta-0deg)>/<w>: +1 all horizontal, -1 all vertical, 0 = no net preference at the horizontal axis (NOT isotropy). S_dir_2d = sqrt(C2^2+D2^2): alignment strength irrespective of direction; null_med/null_p95 are the permutation-null values for the same sample. theta_dir is unstable when S_dir ~ null. theta measured from image-x (horizontal), axial mod 180 deg. Populations: tex_all (structure tensor, coherence-weighted, sigma_coher=4.0px ~0.10 um, coher>=0.3), tex_si (same inside classified Si), obj_si/obj_pore (elongated objects, aspect>=2.5; eq=equal weight, aw=area weight).

## Batch medians

| population | batch | S_x_2d | S_dir_2d | null_p95 | theta_dir | n |
|---|---|---|---|---|---|---|
| tex_all | Batch_1 | +0.171 | 0.184 | 0.001 | -10.9 | 4429587 |
| tex_all | Batch_2 | +0.191 | 0.191 | 0.001 | 0.2 | 4533413 |
| tex_all | Batch_3 | +0.200 | 0.207 | 0.001 | -4.0 | 4516153 |
| tex_all | New_Images_Batch | +0.142 | 0.146 | 0.001 | 6.3 | 4654571 |
| tex_si | Batch_1 | +0.097 | 0.124 | 0.003 | -12.4 | 308604 |
| tex_si | Batch_2 | +0.117 | 0.117 | 0.003 | -0.5 | 380026 |
| tex_si | Batch_3 | +0.097 | 0.117 | 0.003 | -8.8 | 310666 |
| tex_si | New_Images_Batch | +0.074 | 0.105 | 0.003 | 10.4 | 309941 |
| obj_si_eq | Batch_1 | +0.288 | 0.347 | 0.210 | -5.2 | 74 |
| obj_si_eq | Batch_2 | +0.280 | 0.280 | 0.200 | nan | 68 |
| obj_si_eq | Batch_3 | +0.307 | 0.351 | 0.248 | -11.6 | 50 |
| obj_si_eq | New_Images_Batch | +0.245 | 0.296 | 0.183 | -4.0 | 74 |
| obj_si_aw | Batch_1 | +0.421 | 0.425 | 0.459 | nan | 74 |
| obj_si_aw | Batch_2 | +0.459 | 0.472 | 0.414 | nan | 68 |
| obj_si_aw | Batch_3 | +0.324 | 0.344 | 0.472 | nan | 50 |
| obj_si_aw | New_Images_Batch | +0.360 | 0.398 | 0.419 | nan | 74 |
| obj_pore_eq | Batch_1 | +0.219 | 0.257 | 0.059 | -3.9 | 822 |
| obj_pore_eq | Batch_2 | +0.189 | 0.189 | 0.063 | -0.1 | 771 |
| obj_pore_eq | Batch_3 | +0.246 | 0.253 | 0.068 | -3.9 | 644 |
| obj_pore_eq | New_Images_Batch | +0.150 | 0.155 | 0.061 | -2.3 | 751 |
| obj_pore_aw | Batch_1 | +0.584 | 0.585 | 0.253 | -3.1 | 822 |
| obj_pore_aw | Batch_2 | +0.562 | 0.563 | 0.257 | 0.6 | 771 |
| obj_pore_aw | Batch_3 | +0.561 | 0.573 | 0.253 | -1.8 | 644 |
| obj_pore_aw | New_Images_Batch | +0.506 | 0.565 | 0.225 | -1.7 | 751 |

## By inferred acquisition group (dependence check)

Groups are inferred frame/appearance strata — not confirmed parents or sessions. Within-batch between-group spread indicates dependence, not physics.

| population | group | batch | S_x_2d | S_dir_2d | n_img |
|---|---|---|---|---|---|
| tex_all | 1612 | Batch_3 | +0.215 | 0.216 | 2 |
| tex_all | 1780 | Batch_1 | +0.224 | 0.245 | 1 |
| tex_all | 1880 | Batch_1 | +0.171 | 0.184 | 1 |
| tex_all | 1904 | Batch_3 | +0.211 | 0.226 | 3 |
| tex_all | 2048 | Batch_2 | +0.119 | 0.160 | 2 |
| tex_all | 2060 | Batch_3 | +0.202 | 0.208 | 4 |
| tex_all | 2068 | Batch_2 | +0.178 | 0.182 | 1 |
| tex_all | 2068 | Batch_3 | +0.150 | 0.160 | 3 |
| tex_all | 2080 | Batch_1 | +0.225 | 0.235 | 1 |
| tex_all | 2080 | Batch_2 | +0.218 | 0.218 | 1 |
| tex_all | 2080 | Batch_3 | +0.201 | 0.202 | 1 |
| tex_all | 2088 | Batch_3 | +0.141 | 0.155 | 3 |
| tex_all | 2148 | Batch_1 | +0.164 | 0.316 | 1 |
| tex_all | 2148 | Batch_2 | +0.191 | 0.207 | 1 |
| tex_all | 2156 | Batch_1 | +0.175 | 0.175 | 1 |
| tex_all | 2156 | Batch_2 | +0.191 | 0.191 | 1 |
| tex_all | 2272 | Batch_2 | +0.220 | 0.223 | 1 |
| tex_all | 2272 | Batch_3 | +0.134 | 0.135 | 1 |
| tex_all | 2316 | Batch_1 | +0.093 | 0.113 | 2 |
| tex_si | 1612 | Batch_3 | +0.136 | 0.141 | 2 |
| tex_si | 1780 | Batch_1 | +0.133 | 0.139 | 1 |
| tex_si | 1880 | Batch_1 | +0.070 | 0.143 | 1 |
| tex_si | 1904 | Batch_3 | +0.086 | 0.116 | 3 |
| tex_si | 2048 | Batch_2 | +0.083 | 0.100 | 2 |
| tex_si | 2060 | Batch_3 | +0.096 | 0.121 | 4 |
| tex_si | 2068 | Batch_2 | +0.053 | 0.083 | 1 |
| tex_si | 2068 | Batch_3 | +0.097 | 0.105 | 3 |
| tex_si | 2080 | Batch_1 | +0.105 | 0.115 | 1 |
| tex_si | 2080 | Batch_2 | +0.165 | 0.166 | 1 |
| tex_si | 2080 | Batch_3 | +0.160 | 0.161 | 1 |
| tex_si | 2088 | Batch_3 | +0.071 | 0.135 | 3 |
| tex_si | 2148 | Batch_1 | +0.101 | 0.247 | 1 |
| tex_si | 2148 | Batch_2 | +0.215 | 0.220 | 1 |
| tex_si | 2156 | Batch_1 | +0.088 | 0.120 | 1 |
| tex_si | 2156 | Batch_2 | +0.117 | 0.117 | 1 |
| tex_si | 2272 | Batch_2 | +0.186 | 0.186 | 1 |
| tex_si | 2272 | Batch_3 | +0.083 | 0.083 | 1 |
| tex_si | 2316 | Batch_1 | +0.093 | 0.114 | 2 |
| obj_si_eq | 1612 | Batch_3 | +0.303 | 0.317 | 2 |
| obj_si_eq | 1780 | Batch_1 | +0.508 | 0.509 | 1 |
| obj_si_eq | 1880 | Batch_1 | +0.157 | 0.417 | 1 |
| obj_si_eq | 1904 | Batch_3 | +0.329 | 0.355 | 3 |
| obj_si_eq | 2048 | Batch_2 | +0.266 | 0.288 | 2 |
| obj_si_eq | 2060 | Batch_3 | +0.328 | 0.356 | 4 |
| obj_si_eq | 2068 | Batch_2 | +0.280 | 0.280 | 1 |
| obj_si_eq | 2068 | Batch_3 | +0.179 | 0.196 | 3 |
| obj_si_eq | 2080 | Batch_1 | +0.347 | 0.347 | 1 |
| obj_si_eq | 2080 | Batch_2 | +0.164 | 0.169 | 1 |
| obj_si_eq | 2080 | Batch_3 | +0.386 | 0.390 | 1 |
| obj_si_eq | 2088 | Batch_3 | +0.274 | 0.316 | 3 |
| obj_si_eq | 2148 | Batch_1 | +0.405 | 0.429 | 1 |
| obj_si_eq | 2148 | Batch_2 | +0.323 | 0.324 | 1 |
| obj_si_eq | 2156 | Batch_1 | +0.075 | 0.164 | 1 |
| obj_si_eq | 2156 | Batch_2 | +0.033 | 0.253 | 1 |
| obj_si_eq | 2272 | Batch_2 | +0.380 | 0.383 | 1 |
| obj_si_eq | 2272 | Batch_3 | +0.306 | 0.307 | 1 |
| obj_si_eq | 2316 | Batch_1 | +0.246 | 0.269 | 2 |
| obj_si_aw | 1612 | Batch_3 | +0.478 | 0.495 | 2 |
| obj_si_aw | 1780 | Batch_1 | +0.532 | 0.551 | 1 |
| obj_si_aw | 1880 | Batch_1 | +0.348 | 0.463 | 1 |
| obj_si_aw | 1904 | Batch_3 | +0.384 | 0.458 | 3 |
| obj_si_aw | 2048 | Batch_2 | +0.433 | 0.469 | 2 |
| obj_si_aw | 2060 | Batch_3 | +0.179 | 0.339 | 4 |
| obj_si_aw | 2068 | Batch_2 | +0.386 | 0.388 | 1 |
| obj_si_aw | 2068 | Batch_3 | +0.293 | 0.304 | 3 |
| obj_si_aw | 2080 | Batch_1 | +0.421 | 0.425 | 1 |
| obj_si_aw | 2080 | Batch_2 | +0.459 | 0.472 | 1 |
| obj_si_aw | 2080 | Batch_3 | +0.101 | 0.190 | 1 |
| obj_si_aw | 2088 | Batch_3 | +0.249 | 0.449 | 3 |
| obj_si_aw | 2148 | Batch_1 | +0.422 | 0.424 | 1 |
| obj_si_aw | 2148 | Batch_2 | +0.368 | 0.395 | 1 |
| obj_si_aw | 2156 | Batch_1 | +0.134 | 0.252 | 1 |
| obj_si_aw | 2156 | Batch_2 | +0.550 | 0.551 | 1 |
| obj_si_aw | 2272 | Batch_2 | +0.591 | 0.617 | 1 |
| obj_si_aw | 2272 | Batch_3 | +0.465 | 0.466 | 1 |
| obj_si_aw | 2316 | Batch_1 | +0.310 | 0.381 | 2 |
| obj_pore_eq | 1612 | Batch_3 | +0.254 | 0.255 | 2 |
| obj_pore_eq | 1780 | Batch_1 | +0.288 | 0.302 | 1 |
| obj_pore_eq | 1880 | Batch_1 | +0.219 | 0.220 | 1 |
| obj_pore_eq | 1904 | Batch_3 | +0.290 | 0.299 | 3 |
| obj_pore_eq | 2048 | Batch_2 | +0.182 | 0.192 | 2 |
| obj_pore_eq | 2060 | Batch_3 | +0.248 | 0.258 | 4 |
| obj_pore_eq | 2068 | Batch_2 | +0.155 | 0.155 | 1 |
| obj_pore_eq | 2068 | Batch_3 | +0.185 | 0.188 | 3 |
| obj_pore_eq | 2080 | Batch_1 | +0.285 | 0.286 | 1 |
| obj_pore_eq | 2080 | Batch_2 | +0.291 | 0.291 | 1 |
| obj_pore_eq | 2080 | Batch_3 | +0.233 | 0.235 | 1 |
| obj_pore_eq | 2088 | Batch_3 | +0.223 | 0.238 | 3 |
| obj_pore_eq | 2148 | Batch_1 | +0.171 | 0.263 | 1 |
| obj_pore_eq | 2148 | Batch_2 | +0.129 | 0.150 | 1 |
| obj_pore_eq | 2156 | Batch_1 | +0.257 | 0.257 | 1 |
| obj_pore_eq | 2156 | Batch_2 | +0.209 | 0.226 | 1 |
| obj_pore_eq | 2272 | Batch_2 | +0.189 | 0.189 | 1 |
| obj_pore_eq | 2272 | Batch_3 | +0.193 | 0.194 | 1 |
| obj_pore_eq | 2316 | Batch_1 | +0.079 | 0.090 | 2 |
| obj_pore_aw | 1612 | Batch_3 | +0.585 | 0.588 | 2 |
| obj_pore_aw | 1780 | Batch_1 | +0.663 | 0.686 | 1 |
| obj_pore_aw | 1880 | Batch_1 | +0.475 | 0.478 | 1 |
| obj_pore_aw | 1904 | Batch_3 | +0.604 | 0.615 | 3 |
| obj_pore_aw | 2048 | Batch_2 | +0.572 | 0.597 | 2 |
| obj_pore_aw | 2060 | Batch_3 | +0.487 | 0.514 | 4 |
| obj_pore_aw | 2068 | Batch_2 | +0.562 | 0.563 | 1 |
| obj_pore_aw | 2068 | Batch_3 | +0.589 | 0.590 | 3 |
| obj_pore_aw | 2080 | Batch_1 | +0.584 | 0.585 | 1 |
| obj_pore_aw | 2080 | Batch_2 | +0.730 | 0.730 | 1 |
| obj_pore_aw | 2080 | Batch_3 | +0.536 | 0.537 | 1 |
| obj_pore_aw | 2088 | Batch_3 | +0.628 | 0.678 | 3 |
| obj_pore_aw | 2148 | Batch_1 | +0.521 | 0.554 | 1 |
| obj_pore_aw | 2148 | Batch_2 | +0.504 | 0.505 | 1 |
| obj_pore_aw | 2156 | Batch_1 | +0.633 | 0.637 | 1 |
| obj_pore_aw | 2156 | Batch_2 | +0.635 | 0.635 | 1 |
| obj_pore_aw | 2272 | Batch_2 | +0.367 | 0.367 | 1 |
| obj_pore_aw | 2272 | Batch_3 | +0.579 | 0.580 | 1 |
| obj_pore_aw | 2316 | Batch_1 | +0.543 | 0.547 | 2 |

## Reading

- Histograms per image are in `orientation_histograms.csv` — S=0 with a bimodal histogram is orthogonal-mixture order, not isotropy; always read them together.
- `tex_quadrant_sdir_spread` is within-image spatial resampling spread (quadrants), NOT a batch-level uncertainty.
- obj_si_eq_sdir_boot lo/hi is an OBJECT bootstrap CI (objects are the sampling unit).
- A nonzero S says structures align under this definition. It does not establish calendering, grinding, curtaining, damage, transport, or electrochemical consequence.