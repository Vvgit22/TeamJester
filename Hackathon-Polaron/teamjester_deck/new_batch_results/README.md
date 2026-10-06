# Inserting the new batch's results into slide 7

Slide 7 has a **"New batch"** row that shows *Pending* until results are
supplied. The rest of the deck does not change. Three ways to fill it:

## A. Directly from main's categoriser (recommended)

Main's `analysis/categorise.py <folder>` classifies a folder of
`img_*_BSE.tif` (+ optional `_Inlens` / `_ETD` / `_SE`) photos as one sample
and writes `categorise_results.csv` into that folder (one `sample` row and
one row per photo).

`categorise.py` writes `unseen_*` mask files into `analysis/outputs/masks/`,
so run it in a **scratch copy**, not in the pinned worktree. It also needs
pandas < 3, so use the Python 3.10 environment from the deck README.

```bash
MAIN=/Users/raduvadanici/Downloads/teamjester_main_7f0048e
# one-time scratch copy of main's analysis code + a link to its dataset
mkdir -p /tmp/tj_cat && cp -R "$MAIN/analysis" /tmp/tj_cat/analysis \
    && ln -s "$MAIN/Hackathon-Polaron" /tmp/tj_cat/Hackathon-Polaron

cd /tmp/tj_cat/analysis
/tmp/tj_venv310/bin/python categorise.py /path/to/new_batch_folder

cd /Users/raduvadanici/Downloads/Hackathon-Polaron/teamjester_deck
../.venv/bin/python src/build_deck.py --repo "$MAIN" \
    --new-batch /path/to/new_batch_folder/categorise_results.csv \
    --new-batch-name "Batch 4"
```

## B. From main's web app

Save the JSON returned by the web app's `POST /api/analyze` (the object that
has `group` and `images`) and pass that file to `--new-batch`.

## C. Written by hand

Copy `new_batch_TEMPLATE.json` to `new_batch.json`, fill `observations`,
`status` and `follow_up` (and optionally point `categorise_csv` /
`webapp_json` to main's output), then pass it to `--new-batch`.

## What gets written where

* The row text: group call (IN/OUT of the Batch 3 envelope with distance vs
  threshold), most-like batch and its share, how many photos agree, and the
  top drivers in main's plain words. Very long text is shortened on the slide
  and kept in full in the speaker notes.
* Default status: *Indicative — group calls are not yet independently
  validated* (main's group-of-photos accuracy is measured in-sample). Override
  it with `status` in a manual JSON once you have an independent check.
* The per-photo calls and the source file path go into slide 7's speaker
  notes and into `CLAIM_LEDGER.csv`, marked as not verified by the deck.
* If the row is tall, the one-line simulation note at the bottom of slide 7
  moves to the speaker notes so nothing overlaps.
* By default the build overwrites `TeamJester_Algorithm_Overview.pptx/.pdf`.
  Add `--out TeamJester_Algorithm_Overview_with_results` to keep both.
