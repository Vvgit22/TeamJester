# Results — what the measurements support

We measured every photo the same way and asked three questions: do the batches hold the same amounts, do they differ in structure, and can we prove it's the material — not the imaging — that differs? The amounts match; the imaging sessions don't. Today the honest answer for every batch is CAN'T TELL YET — not because nothing differs, but because session and batch can't be separated in this dataset.

## 1. All three batches contain the same amounts of pore space and silicon. [SOLID]

- found: Pore space is about 10%-11% of each photo and candidate silicon about 6%, in all three batches. Every batch's middle value sits inside Batch 3's normal range.
- sure: Solid for differences bigger than about 1.4 percentage points of silicon or 2 points of pore space. Those are the smallest gaps 7, 7 and 17 photos can reveal (exact test).
- doesn't mean: It doesn't prove the batches are identical. Smaller differences, or material too fine to resolve at 25 nm per pixel, would not show up.
- source: validated_comparison/per_image_features.csv, pairwise_comparisons.csv

## 2. Two Batch 1 photos contain unusual bright material whose identity we can't tell. [POSSIBLE]

- found: In those two photos, uncertain-bright material covers 9% and 9.3% of the area — more than double the most seen anywhere in Batch 3 (4.1%). It is genuinely bright material, not grey bulk we misread.
- sure: The amount is measured and solid. What the material is made of is not established: brightness is not chemistry, so this is labelled uncertain rather than called silicon.
- doesn't mean: It doesn't prove a defect. It is a photo-level anomaly that could be imaging, preparation or real material — the next step is an EDS elemental scan on that material.
- source: image_acquisition.csv, objects_classified.csv

## 3. The photos were taken under different imaging conditions that line up with the batches. [SOLID (as an observation)]

- found: Inside a shared session, photos from different batches look alike; between sessions, values jump. A classifier using only acquisition signature (frame shape, noise, contrast) matches batch labels 61% of the time — as well as the 59% achieved using the measured structure.
- sure: Solid as an observation: the session pattern is in the images themselves (13 inferred sessions; 21/34 photos have the darkest pixels clipped to pure black).
- doesn't mean: It doesn't prove the batch labels are wrong — it proves we can't yet separate material from how the photos were taken.
- source: image_acquisition.csv, benchmark_results.csv

## 4. So batch differences can't be confirmed yet. [CAN'T TELL YET]

- found: The decisive test is comparing batches inside the same session, where imaging conditions match. Batch 1 and Batch 3 share only one session — that is too few photos to call a difference.
- sure: With 13 sessions spread unevenly over 31 photos, the controlled comparison lacks the numbers it needs. This is an absence of evidence, not evidence of absence.
- doesn't mean: It doesn't say the batches are the same. It says this dataset cannot currently separate material differences from session effects.
- source: blocked_permutation.csv, image_acquisition.csv

## 5. The new photos: what our blind calls taught us. [CAN'T TELL YET]

- found: We matched each photo to the closest batch before any answers were known, and saved the calls. Confirmed corrections make it 0 correct out of 2 (the third is unconfirmed). Both wrong calls matched the photo's imaging session — the exact confound in finding 3, flagged on the calls themselves.
- sure: The labels are externally confirmed by the organizer; our calls were timestamped before disclosure. The score is honestly 0/2.
- doesn't mean: It doesn't prove the pipeline sees nothing — it proves that on these three photos, session signature and batch pointed the same way, so a correct call wouldn't have meant material was recognised either.
- source: new_batch_ground_truth.csv, assignments.csv

## Not used, and why

- pore counts, sizes and shapes: pore count is the only value that passes the many-test correction, but the session check can't run (one shared group); sizes carry the section-cut caveat
- clustering and connectivity: sensitive to where boundaries land; nothing survives the session check
- silicon–pore contact: corrected and real, but not separable from session effects
- battery-model (DFN) indicators: model-derived; the differences sit inside the model's own assumption spread
- extra detector channels (InLens/ETD): exploratory; detector gain varies with session
- orientation strength (S): real shared structure — pores lie near-horizontal in all batches — but it describes the electrode rather than separating batches
