"""vcompare — validated batch comparison.

Standalone analysis that re-measures all 31 BSE cross-sections under ONE
recipe frozen on the reference batch only, then tests batch differences
with exact permutation tests and declares what survives measurement
uncertainty.  Reuses polaron_qc's detection machinery for the corrected
QC recheck but edits nothing outside this package.
"""
