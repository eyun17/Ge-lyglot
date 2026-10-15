# Experiment kg-llm-heldout40: with and without the concept graph

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

## Answers, heldout

| A | B | metric | n | A | B | B − A [95% CI] | better / worse / same | p |
|---|---|---|---|---|---|---|---|---|
| dense | dense+kg | recall@8 | 37 | 0.198 | 0.302 | +0.104 [+0.023, +0.198] | 8 / 1 / 28 | 0.0295 |
| dense | dense+kg | recall_ctx | 37 | 0.198 | 0.302 | +0.104 [+0.023, +0.198] | 8 / 1 / 28 | 0.0295 |
| dense | dense+kg | status_ok | 40 | 0.700 | 0.775 | +0.075 [-0.075, +0.225] | 7 / 4 / 29 | 0.549 |
| dense | dense+kg | invalid | 40 | 0.050 | 0.025 | -0.025 [-0.100, +0.050] | 2 / 1 / 37 | 1 |
| hybrid | hybrid+kg | recall@8 | 37 | 0.185 | 0.315 | +0.131 [+0.054, +0.221] | 9 / 0 / 28 | 0.0046 |
| hybrid | hybrid+kg | recall_ctx | 37 | 0.185 | 0.315 | +0.131 [+0.054, +0.221] | 9 / 0 / 28 | 0.0046 |
| hybrid | hybrid+kg | status_ok | 40 | 0.800 | 0.700 | -0.100 [-0.225, +0.000] | 1 / 5 / 34 | 0.219 |
| hybrid | hybrid+kg | invalid | 40 | 0.025 | 0.000 | -0.025 [-0.075, +0.000] | 1 / 0 / 39 | 1 |
| rewrite | rewrite+kg | recall@8 | 37 | 0.423 | 0.450 | +0.027 [-0.045, +0.108] | 4 / 3 / 30 | 0.609 |
| rewrite | rewrite+kg | recall_ctx | 37 | 0.423 | 0.450 | +0.027 [-0.045, +0.108] | 4 / 3 / 30 | 0.609 |
| rewrite | rewrite+kg | status_ok | 40 | 0.925 | 0.950 | +0.025 [-0.050, +0.125] | 2 / 1 / 37 | 1 |
| rewrite | rewrite+kg | invalid | 40 | 0.000 | 0.025 | +0.025 [+0.000, +0.075] | 0 / 1 / 39 | 1 |
| agent | agent+kg | recall@8 | 37 | 0.428 | 0.509 | +0.081 [-0.041, +0.207] | 11 / 6 / 20 | 0.243 |
| agent | agent+kg | recall_ctx | 37 | 0.446 | 0.554 | +0.108 [-0.014, +0.234] | 12 / 6 / 19 | 0.124 |
| agent | agent+kg | status_ok | 40 | 0.925 | 0.950 | +0.025 [-0.050, +0.100] | 2 / 1 / 37 | 1 |
| agent | agent+kg | invalid | 40 | 0.025 | 0.050 | +0.025 [-0.075, +0.150] | 1 / 1 / 38 | 1 |
