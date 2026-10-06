# Before / after — what changed and why

| earlier_claim | now | why |
|---|---|---|
| 'Zero false alarms' on baseline self-scores | 1/17 reference images exceed the flag threshold (LOO) | The generator asserted zero without counting |
| Batch_1 = REJECT (excess Si) | INVESTIGATE | REJECT depended on redundancy weights fitted on all batches; reference-only weights give INVESTIGATE on identical features |
| Silicon fractions treated as measured | Split into si_candidate + uncertain_bright; ambiguous material counted separately | An intensity filter cannot establish chemical identity |
| Permutation p-values with seed 0 | Exact permutation — all splits enumerated | B2's verdict was seed-sensitive; enumeration removes the seed |
| 'No significant difference' read as 'same' | Every non-significant test reports its minimum detectable difference | With n=7 only large effects are detectable |

