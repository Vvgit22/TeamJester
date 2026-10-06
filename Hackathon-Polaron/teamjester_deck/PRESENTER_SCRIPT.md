# Presenter script — TeamJester algorithm overview

Deck: `TeamJester_Algorithm_Overview.pptx` · source: GitHub main @ `7f0048ed46715ca63223f5d5be98b50f406ba490` (2026-10-04). Read the WHAT TO SAY part of each slide; the full speaker notes (definitions, number provenance, limits, Q&A) are in the deck.

## 1. Do new anode batches match the approved one?

This project asks a practical quality question: when a supplier delivers a new batch of anode coating for lithium-ion cells, does it look like the batch we already approved (Batch 3)? Today that judgement is made by eye from microscope photos. The TeamJester pipeline on GitHub main turns those photos into measured, explainable numbers and compares them with Batch 3. The photo is a real cross-section from Batch 3: dark-grey flakes, bright particles and black gaps. Be clear about what works today: comparing structure with uncertainty works; calling a batch from a single photo does not; the battery simulation is an optional illustration.

**If asked:**

Q: "So can it tell me whether a batch is good?"

A: Not on its own. It can tell you, with stated uncertainty, how a batch's measured structure differs from Batch 3, and it flags photos too poor to trust. It does not measure chemistry or performance, and its batch classifier is not yet reliable on single photos.

## 2. How the algorithm works

Walk left to right. (1) Each location is photographed by three detectors. (2) Every pixel is labelled pore, grey bulk or bright particle with one fixed recipe; the brightness cut-offs are read from each photo's own histogram. (3) Quality guards check contrast, noise, sharpness and shading; 2 photos fail (4ih2ggld, 5n1q8atc, both Batch 1). (4) The label map becomes 53 measurements; only those that agree between the left and right half of the same photo, and are not duplicates, are kept (20). (5) Batch 1 and Batch 2 are compared with Batch 3, asking whether a shift is bigger than normal photo-to-photo scatter. (6) A simple classifier says which batch a new sample is closest to. The dashed branch is a battery simulation that uses a few image numbers plus many assumptions. Steps 1-4 (teal bracket) are measurement; steps 5-6 add statistics on those measurements; in the dashed branch, assumptions dominate.

**If asked:**

Q: "Is this machine learning?"

A: No black box. Every step is a fixed, inspectable rule (thresholds, morphology, distances). The only fitted parts are averages and spreads of the measurements, and the classifier is a nearest-average rule. That makes it explainable, but it also means it can only be as good as the brightness labels and the small number of photos.

## 3. How we segment the images

Same patch of a Batch 3 photo, three times. Left: the photo as the BSE detector sees it. Middle: the two brightness cut-offs applied directly — red is darker than the pore cut, gold brighter than the bright cut. You can see why clean-up is needed: thin bright rims on flake edges and tiny specks would be counted as particles. Right: the final labels after removing specks, filling holes and splitting touching particles (dark outlines). The close-up shows an honest ambiguous case: a textured light-grey object is only partly called bright and gets cut into 4 pieces. The main limitation is that brightness is not chemistry.

**If asked:**

Q: "How do you know the labels are right?"

A: We know they are stable — re-running main's code reproduces every mask exactly, left and right halves agree, and +/-10% threshold changes move fractions by about 10-25% in relative terms. We do not yet know they are correct: the 300-point expert check sheet in the repo is still empty, and nobody has confirmed with chemical analysis that bright means silicon.

## 4. The markers that matter — and what we can conclude

These five are the markers I would show anyone first. They were picked because they are repeatable on main, have a clear physical meaning, and together describe composition, size, contact and arrangement — not because they show the biggest batch differences. Read the last column carefully: only one is even tentatively different (Batch 1's lower visible pore space), two show no detected difference, one is undetermined, and one is a solid shared feature. Every battery effect in the third column is conditional: "might matter", with trade-offs in both directions.

**If asked:**

Q: "Is more pore space good or bad?"

A: Neither by itself. More pore space usually helps ions move (better fast charging and discharging) but leaves less room for active material, so the cell stores less energy per volume. The right amount depends on the cell design — which is why we report the shift and its uncertainty, not a verdict.

## 5. What these markers look like

Here is what four of the markers literally measure, on one ordinary Batch 3 photo. Top left: one particle outlined, with the circle of equal area — its diameter is the size number; the photo's median is smaller because there are many tiny particles. Top right: everything red is "visible pore"; 10.8% of this photo. Bottom left: contact. I show four different numbers from the same photo on purpose — share of particles that touch a pore, share of area in those particles, share of particle edge next to a pore, and the pore share of a thin shell around particles. They answer different questions, so we should never say "contact" without saying which one. Bottom right: lines through the grey flakes are longer sideways than up-and-down, so the flakes lie flat. All of this is algorithm output; nobody has hand-checked these outlines yet.

**If asked:**

Q: "Only 1.7% of the edge touches a pore, but 23% of particles touch one — which is right?"

A: Both. Most particles that touch a pore do so along a tiny part of their edge, so the share of edge is small while the share of particles is larger. That is exactly why we never report "contact" without saying which quantity it is.

## 6. The key measurements, photo by photo

Three panels, one dot per photo. A: visible pore space — Batch 1 is a little lower on average, but its dots overlap Batch 3's, which is why we call it tentative. B: bright-particle share — the two light diamonds are the photos the quality guard flagged; they alone create Batch 1's apparent +45%; the other 29 photos all sit in the same range. C: image noise — every Batch 1 and Batch 2 photo is at the upper noise levels, while most Batch 3 photos are cleaner. The one marker that survives the strict test, grey-level texture, rises with exactly this noise. That is the most important caveat on this dataset: some batch differences may be microscope-settings differences.

**If asked:**

Q: "So is Batch 1 different or not?"

A: Not established. Its pore space is slightly lower on average, but that does not survive the correction for testing 20 markers, the photos overlap, and Batch 1 was photographed under noisier conditions. The honest call is "tentative — re-image under matched settings".

## 7. Results by batch — and the next decision

Batch by batch. Batch 1 shows the most movement — less visible pore space and fewer large gaps — but nothing material survives the correction for testing 20 markers, its bright-particle "excess" comes from two poor photos, and its texture shift follows image noise. So: tentative, re-image under matched settings. Batch 2 shows no established structural shift; its only significant change is again the noise-linked texture. Batch 3 is the reference, and one honest finding is that its own envelope is too tight for single photos: hold one Batch 3 photo out and it is called "out of spec" 7 of 17 times. The last row is the new delivery we are running now. Take-home: the measurement part works and is reproducible; the decision part needs a blind test on new, properly matched photos.

**If asked:**

Q: "Should we reject Batch 1?"

A: The evidence does not support a rejection. It supports re-imaging: two of its seven photos are unreliable, its remaining shifts are tentative, and it was photographed under noisier conditions than Batch 3. A matched, blind re-test is cheap and would settle it.

## Background for questions on reproducibility

*BUILD-STATE CAVEAT (from-scratch rebuild of main's code, provenance/clean_rebuild_summary.json)*

Re-running run_all.py at this commit on an empty outputs/ folder reproduces every segmentation table and all committed feature columns exactly, and every % shift and class of the 20 committed markers. However, the current features.py also computes 12 newer columns that the committed features.csv lacks; 8 of them pass main's gates, so a fresh build keeps 28 markers instead of 20. The classifier numbers then change: all-features 15/31 correct (committed 15/31), artefact-safe 20/31 (committed 13/31), held-out Batch 3 called OUT 8/17, shuffled-label control 38%; Holm survivors become: Batch 1 bse_bulk_texture; Batch 1 inl_lbp_flat; Batch 2 bse_bulk_texture. The deck reports the committed run (the tables main's webapp loads); treat classifier accuracy as UNRESOLVED — it depends on the build state — while the structural markers are robust to it.
