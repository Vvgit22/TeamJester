# Blind-test protocol — 6 new images (pre-registration)

Purpose: independent validation after the 0/2 confirmed-label result.
Any method change informed by the disclosed labels requires an untouched
test set — these 6 images are it.

## Rules (commit to these BEFORE looking at labels)

1. Images go in a NEW folder (not inside Batch_*). Record arrival hash.
2. Extract features with the frozen recipe only — no refitting, no
   parameter changes informed by the disclosed 3 images.
3. Predict with TWO methods and record both:
   a. the frozen 9-feature envelope (unchanged historical method);
   b. the acquisition-signature baseline (frame height, noise, contrast)
      — the control. If it matches the envelope's picks, the assignment
      may be session recognition, not material.
4. Save `new6_predictions.csv` with: image_id, envelope pick, envelope
   coverage, median-z pick, acq-baseline pick, confidence,
   session-confound flag, timestamp + file hash. Commit BEFORE labels.
5. Pre-declare the confound: if a new image's frame-height group appears
   in exactly one batch, say so in the predictions file — a correct
   label then cannot distinguish material from session.
6. Score honestly: report N/N correct, per-class recall, coverage,
   abstentions. No retroactive tuning.

## Commands

```bash
# 1. extract (frozen recipe, corrected pipeline)
.venv/bin/python -B run_dfn.py --data <NEW_DIR> --out new6_extract \
    --recipe dfn_output/recipe.json --no-sim
# 2. predict (envelope + acq baseline, timestamped)
.venv/bin/python -B benchmark_assign.py --predict-new <NEW_DIR> \
    --out new6_predictions.csv
```

(step 2 flag to be implemented when the images land.)

## What a good outcome looks like

Not "6/6 correct" — but *predictions committed blind, confound declared
in advance, and a classifier that demonstrably beats its own
acquisition-signature baseline*. If it doesn't, the honest result is
"cannot separate material from session at this sample size."
