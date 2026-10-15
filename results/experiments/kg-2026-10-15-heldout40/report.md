# Experiment kg-2026-10-15-heldout40: with and without the concept graph

See manifest.json for the commit, prompt version, model, index and concept graph version.

## Retrieval, heldout (37 questions with gold sections)

The concept graph links to 33 of the 68 gold sections of these questions (49%). A share near 100% means the graph was probably written with these questions in mind: read the result as an upper bound.

Mean recall@8 per language set:

| mode | all | ko |
|---|---|---|
| dense | 0.198 | 0.198 |
| dense+kg | 0.302 | 0.302 |
| hybrid | 0.185 | 0.185 |
| hybrid+kg | 0.315 | 0.315 |

Paired differences (bootstrap 95% interval; p from McNemar or a sign-flip permutation test):

| A | B | metric | n | A | B | B − A [95% CI] | better / worse / same | p |
|---|---|---|---|---|---|---|---|---|
| dense | dense+kg | recall | 37 | 0.198 | 0.302 | +0.104 [+0.023, +0.198] | 8 / 1 / 28 | 0.0295 |
| dense | dense+kg | all_found | 37 | 0.162 | 0.189 | +0.027 [-0.054, +0.108] | 2 / 1 / 34 | 1 |
| hybrid | hybrid+kg | recall | 37 | 0.185 | 0.315 | +0.131 [+0.054, +0.221] | 9 / 0 / 28 | 0.0046 |
| hybrid | hybrid+kg | all_found | 37 | 0.135 | 0.216 | +0.081 [+0.000, +0.189] | 3 / 0 / 34 | 0.25 |
