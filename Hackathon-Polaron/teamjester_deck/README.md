# TeamJester algorithm overview — 7-slide deck

An editable PowerPoint deck (and matching PDF) that explains the batch-comparison
algorithm on the **TeamJester GitHub main branch** to a non-specialist
audience, with every number traced to main's committed outputs.

| File | What it is |
|---|---|
| `TeamJester_Algorithm_Overview.pptx` | the deck (16:9, editable text, tables, flowchart, annotations and native charts; full speaker notes on every slide) |
| `TeamJester_Algorithm_Overview.pdf` | the same deck exported with LibreOffice (fonts embedded) |
| `PRESENTER_SCRIPT.md` | what to say per slide + the likely question and an honest answer |
| `CLAIM_LEDGER.csv` / `.md` | every number on the slides → source file @ commit, how it was obtained, how it was verified |
| `previews/slide-N.png` | rendered pages used for visual QA |
| `new_batch_results/` | how to drop the results of the batch that is still running into slide 7 |
| `src/` | the reproducible build (see below) |
| `assets/` | images generated from main's data + `annotations.json` (coordinates for the editable overlays) |
| `provenance/` | pinned-commit numbers, verification outputs, rebuild logs |

## Source of truth

* Repository: <https://github.com/Augustin-Briens/TeamJester> (private)
* Branch / commit: **main @ `7f0048ed46715ca63223f5d5be98b50f406ba490`**
  ("Clean repo: website, report, pipeline code only", 2026-10-04 13:18 UTC),
  fetched with `git fetch origin` and checked out as a clean detached worktree
  at `/Users/raduvadanici/Downloads/teamjester_main_7f0048e`.
* Only main's `analysis/` pipeline, its committed outputs
  (`analysis/outputs/tables`, `masks`) and its dataset
  (`Hackathon-Polaron/Batch_*`, 93 TIFFs) are used. No other branch, archived
  method or local experiment (e.g. the `micro2dfn` / `polaron_qc` work in the
  parent folder) feeds the deck.
* Footer on every slide: `TeamJester · GitHub main @ 7f0048e (2026-10-04)`.
  Speaker notes carry the full SHA, repo link and provenance.

## Rebuild

```bash
cd /Users/raduvadanici/Downloads/Hackathon-Polaron/teamjester_deck
./build.sh                       # numbers -> assets -> PPTX/PDF -> checks
./build.sh --verify              # first re-run main's own code (≈5 min)
```

`build.sh` runs, in order:

1. `src/deck_numbers.py` — computes every number shown from main's committed
   tables → `provenance/deck_numbers.json` (value, text, source file, method).
2. `src/make_assets.py` — images from main's TIFFs and committed masks
   (segmentation panels, close-up, marker examples, thumbnails, hero image) and
   `assets/annotations.json`.
3. `src/build_deck.py` — writes the PPTX with python-pptx, the ledger and the
   presenter script, exports the PDF with LibreOffice and renders previews.
4. `src/check_deck.py` — fails on: XML children out of schema order (what makes
   PowerPoint ask to "repair" a file), missing notes sections / SHA / footer,
   PPTX words missing from the PDF, fallback fonts, broken hyperlinks (DOIs are
   fetched; GitHub links are checked with `gh api` at the pinned SHA).

Environments:

* Deck build: the project venv `../.venv` (Python 3.13 with python-pptx 1.0.2,
  PyMuPDF, matplotlib, scikit-image, pandas) and LibreOffice (`soffice`).
  Headless LibreOffice does not see `~/Library/Fonts`, so the build uses a
  private profile `.lo_profile/` with the Latin Modern fonts copied into its
  `user/fonts/` (created automatically; your own LibreOffice profile is not
  touched).
* Verification of main (`--verify`): main's `.devin/blueprint.yaml` asks for
  system Python 3.10 with unpinned numpy/scipy/scikit-image/scikit-learn/
  pandas/matplotlib/openpyxl/reportlab/tifffile/imagecodecs. Recreate with
  `uv venv --python /Library/Frameworks/Python.framework/Versions/3.10/bin/python3.10 /tmp/tj_venv310`
  then `uv pip install --python /tmp/tj_venv310/bin/python numpy scipy==1.14.1 scikit-image scikit-learn pandas matplotlib openpyxl reportlab tifffile imagecodecs`.
  scipy is pinned to 1.14.1 only because the 1.15.3 wheel for Python 3.10
  fails to load on this macOS (`__thread_bss` dyld error). Versions used are in
  `provenance/verify_environment.json`.

Fonts: titles Latin Modern Roman 17 (`LMRoman17`), body Latin Modern Sans 10
(`LMSans10`), code names Latin Modern Mono — installed in `~/Library/Fonts`.
On a machine without them PowerPoint substitutes a default font; install the
free GUST Latin Modern OTFs to keep the look.

## Inserting the running batch's results

See `new_batch_results/README.md`. Short version:

```bash
./build.sh --new-batch /path/to/categorise_results.csv --new-batch-name "Batch 4"
```

Accepted inputs: main's `categorise.py` output CSV, main's web-app JSON, or a
hand-filled `new_batch_results/new_batch_TEMPLATE.json`. The slide-7 row fills
in, the per-photo calls go to the notes and the ledger; nothing else changes.
Use `--out <name>` to keep the default deck untouched.

## What was verified on main (and what was found)

Re-running main's own code (`src/verify_main.py`, outputs in `provenance/`):

* **Segmentation:** all 31 photos re-segment pixel-for-pixel identical to the
  committed masks (pore and bright masks, watershed particle labels).
* **Measurements:** all 54 columns of the committed `features.csv` recompute
  identically from the committed masks.
* **Statistics:** baseline, every leave-one-out prediction/confusion table and
  the group-size tables regenerate identically. `deltas.csv` regenerates with
  identical shifts, % changes, Mann–Whitney p and classes; its bootstrap
  intervals and Holm p differ slightly because the committed table was computed
  when 21 features were kept (`si_d10_um` was later removed by editing tables).
* **From scratch** (main's `run_all.py --fast` on an emptied `outputs/`): every
  segmentation/QC table and every committed feature column is identical, and
  all % shifts and classes of the 20 committed markers are unchanged. But main's
  current `features.py` also computes 12 newer columns absent from the committed
  `features.csv`; 8 pass the gates, so a fresh build keeps 28 markers and the
  classifier numbers move (artefact-safe leave-one-out 13/31 → 20/31; held-out
  Batch 3 OUT 7/17 → 8/17; a new Holm-significant Inlens texture marker). The
  deck reports the committed run (the tables main's web app loads) and labels
  classifier accuracy as unresolved.

Issues found in main (documented in the notes/ledger; the algorithm itself was
not changed):

* `analysis/outputs/tables/loo_summary.csv` is stale (pre-`si_d10_um` removal):
  it says 42% all-features accuracy, the current predictions give 15/31 = 48%;
  its `false_alarm` column divides by all 31 photos instead of the 17 Batch 3
  photos. The README/report's "~45% LOO vs 37% shuffled" comes from it.
  `loo_confusion.csv` (no suffix) is likewise not produced by `run_all.py`.
* "Groups of 5+ photos reach ~97–100%" (`images_needed.csv`) is measured
  in-sample: the batch centroids are fitted on the same photos that are sampled.
* PyBaMM branch: every C/10, C/2 and 1C run returns exactly 5.25 Ah because the
  simulation stops at its time limit (`t_end = 1.05 × 3600 s / C-rate`), so only
  2C carries a comparison.
* `run_all.py --clean` crashes (deletes `outputs/` after the folders were
  created); `stage_dfn` only re-runs when its output already exists.
* The report says the green channel is used; the code uses the RGB median
  (channels are equal apart from marker stripes, so values agree).
* `point_count_validation.xlsx` (300 points) has no human labels yet, so
  segmentation accuracy against an expert is unavailable.

Presentation-derived numbers (not main features) are marked as such on slide 5
and in the ledger: the share of particles, and of particle area, within 3 px of
a pore — computed from main's committed `particles.csv` (`d_min_px`).

## Design notes

* LaTeX-like look: white background, navy text, one restrained teal accent,
  main's own Okabe–Ito batch colours (B1 orange, B2 green, B3 blue) in every
  chart; segmentation overlays use crimson = pore, gold = bright particle.
* Charts on slide 6 are native PowerPoint charts (right-click → Edit Data).
  They are built as line charts with markers and gaps because LibreOffice drops
  all but one series of multi-series XY scatter charts written by python-pptx.
  Flagged photos are light diamonds (LibreOffice draws hollow markers without
  an outline).
* Latin Modern Sans has no µ (micro sign), ≤, ≥ or ≈; the deck uses Greek μ and
  plain words instead so no glyph falls back to another font.
* Dense tables and image annotations use 11–14 pt; titles 34 pt; lead lines and
  the main text blocks 17–20 pt.
