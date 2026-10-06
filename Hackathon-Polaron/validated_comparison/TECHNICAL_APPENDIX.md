# Technical appendix — validated comparison

## Reproduce

```bash
.venv/bin/python run_compare.py --data . --out validated_comparison
```

## Software versions

{
  "numpy": "2.5.3",
  "pandas": "3.0.6",
  "scipy": "1.18.1",
  "skimage": "0.26.0",
  "python": "3.13.5"
}

## Run settings

{
  "command": ".venv/bin/python run_compare.py --data . --out validated_comparison",
  "seed": 0,
  "n_boot": 10000,
  "downsample": 1,
  "fast": false,
  "batches": {
    "Batch_1": 7,
    "Batch_2": 7,
    "Batch_3": 17
  }
}

## Frozen recipe (reference batch only)

{
  "recipe_version": "vcompare-1.0",
  "fitted_on": "Batch_3",
  "n_reference_images": 17,
  "seed": 0,
  "pixel_um_expected": 0.0250001448827294,
  "t_pore": 0.7108650803565979,
  "t_si": 1.3353633880615234,
  "t_core": 1.549543023109436,
  "noise_adj": {
    "slope": 6.18361171070412,
    "intercept": 54.60159874041463,
    "ref_noise_median": 9.784263610839844,
    "n_used": 17,
    "ref_r2": 0.5094117232186292
  },
  "params_um": {
    "flatfield_sigma_um": 5.0,
    "seg_smooth_sigma_um": 0.0375,
    "object_erode_um": 0.05,
    "contact_dilation_um": 0.075,
    "watershed_min_dist_um": 0.2,
    "min_bright_area_um2": 0.09375,
    "min_pore_area_um2": 0.0125,
    "si_calib_min_diam_um": 2.0,
    "si_calib_min_solidity": 0.85,
    "si_core_percentile": 5.0,
    "si_min_solidity": 0.75
  },
  "file_md5": {
    "img_4ih2ggld": "39cebab883e9aa4489533f32815b7b57",
    "img_5n1q8atc": "49a70e91ea0a033cfcdec62a2de5c7e9",
    "img_f1vzngrs": "344c79fe829625e82fdaf59fd7a000df",
    "img_ffwubibz": "4b80325c2675e1d8200219d2a7d04e39",
    "img_fzrt2k6r": "c238a35420540be48d5779441fda187a",
    "img_iv6g2oq0": "b320522c422f4899b8706f2362021818",
    "img_uhdslk0o": "2dead843d6758b740191a3fcbb585ad0",
    "img_3806gxp0": "e5e0af2480e7379386b12861d3df034d",
    "img_avn74qx1": "91d0c0fa56d8c994006cebfa83c6fc3a",
    "img_b3esycq1": "4dc2030d3069e7fcce603aa92e00b500",
    "img_epqdaau9": "dd143765200b19260bfc89bf85aff48d",
    "img_i9jiqjwl": "4782035bb0ef6c26f46a56e5ed6e633d",
    "img_r17byphk": "f89f76efaa71f1e582d953b2662d2c04",
    "img_rxax5ozo": "84c1386553adbdacccd1c66c844241ca",
    "img_0grcilhi": "e8e1e5b1aa4c45b1a372a3a408123035",
    "img_71vgq3fw": "f13ed14a1518fe4a28797cceb1c4882e",
    "img_9luzk4jm": "3626824ab77389656e22b21f8bbcd85e",
    "img_cfe5vt7s": "28ef5bbda268a2119d60f0cb6b39ba59",
    "img_hawkfj64": "26d424a93434be852c0f05476448c2a8",
    "img_hzumfsms": "86ea0c28449297d232160fbac978169b",
    "img_kbdh4tri": "2cdf6ed31f28762dd4a993d1accc697c",
    "img_mgxahqnk": "96750997baeaa622bbc389a84e67f7d4",
    "img_pl8uabbv": "3c882606558650593c0a2edb38a16b91",
    "img_ptg8lmto": "eb577d7a97cb45e9870086b2243357b5",
    "img_tuy3zymq": "8209265f4aebf0d460d3c3c6c951c328",
    "img_ufdvpb81": "7e3ca25d9cf7525b1260e40ca266d72c",
    "img_utfgcjfa": "acd7a13528b3688ab6e86af4f6e2094b",
    "img_vc2whyaq": "a63c40730289601bd9b7bd7b70d6a925",
    "img_x77cy643": "b3dcde4cc74a433295bc3e565c41ae0d",
    "img_x7u69zsw": "eaf7a957df4a4ea16ad606fd375238c6",
    "img_xgj4xftb": "2d3cf9f47d91dc7898c884b40fc347e9"
  }
}

## Statistics

- Test statistic: difference of **medians** (the same statistic for the
  estimate and its interval).
- p-values: **exact permutation** — all assignments enumerated
  (C(24,7)=346,104 for 7-vs-17; C(14,7)=3,432 for 7-vs-7). No seed
  dependence.
- Multiplicity: Benjamini–Hochberg at FDR 0.1 within each
  batch pair across the 9 declared features.
- CIs: percentile bootstrap over images (10000 resamples,
  seed 0). Images are the independent sampling unit —
  pixels/particles are not.
- MDD: `mdd_critical` is the smallest |median diff| rejected at
  alpha=0.05; `mdd_80pct` is the smallest location shift
  giving >=80% power under a pure-shift model.

## Exclusions / unknowns

- No specimen/location metadata in the TIFFs — image-level is the only
  known sampling unit; locations within a batch may not be independent.
- `Batch_3` = shipment-approved **selected reference**; not verified
  defect-free. All differences are relative to it.
- `Batch_1/*_segmentation.npy` (7 files): leftover 4-class colour
  clustering from an early `segment_images.py`; known to mislabel
  graphite — **unused**, kept for provenance only.
- InLens fine-line/crack measures are secondary: acquisition
  comparability across images is unresolved.

## DFN outputs — known defects, not used here

`dfn_output/` model numbers are **not trustworthy** pending repair
(separate task): the OKane2022 parameter merge overwrites silicon OCP/
exchange/mechanics with graphite values; the LAM constant is 3600x too
fast (1e-3 vs 2.7778e-7 s-1); the capacity readout differences full
cycle endpoints of a running counter; `--fast` runs were reported as
full-res 5-cycle. Treat all DFN indicators as requiring correction.

## Remaining limitations

- "No clear difference" does not prove equivalence (see MDD column).
- The uncertain-bright category is conditional on the frozen recipe;
  alternative thresholds shift membership (stress test reported in
  robustness.csv).
- No independent labels: expert review sheet is produced, not filled.
