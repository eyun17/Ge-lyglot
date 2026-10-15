# Experiment kg-2026-10-14: with and without the concept graph

See manifest.json for the commit, prompt version, model, index and concept graph version.

## Retrieval, main (336 questions with gold sections)

The concept graph links to 95 of the 98 gold sections of these questions (97%). A share near 100% means the graph was probably written with these questions in mind: read the result as an upper bound.

Mean recall@8 per language set:

| mode | all | ko | en | de | ar | ar-SY | it |
|---|---|---|---|---|---|---|---|
| dense | 0.353 | 0.330 | 0.375 | 0.432 | 0.339 | 0.256 | 0.384 |
| dense+kg | 0.792 | 0.807 | 0.812 | 0.792 | 0.807 | 0.732 | 0.801 |
| hybrid | 0.299 | 0.330 | 0.304 | 0.265 | 0.339 | 0.256 | 0.301 |
| hybrid+kg | 0.789 | 0.807 | 0.804 | 0.804 | 0.807 | 0.732 | 0.783 |

Paired differences (bootstrap 95% interval; p from McNemar or a sign-flip permutation test):

| A | B | metric | n | A | B | B − A [95% CI] | better / worse / same | p |
|---|---|---|---|---|---|---|---|---|
| dense | dense+kg | recall | 336 | 0.353 | 0.792 | +0.439 [+0.395, +0.486] | 205 / 2 / 129 | 0.0001 |
| dense | dense+kg | all_found | 336 | 0.262 | 0.667 | +0.405 [+0.354, +0.458] | 136 / 0 / 200 | 2.3e-41 |
| hybrid | hybrid+kg | recall | 336 | 0.299 | 0.789 | +0.490 [+0.445, +0.537] | 221 / 0 / 115 | 0.0001 |
| hybrid | hybrid+kg | all_found | 336 | 0.223 | 0.655 | +0.432 [+0.381, +0.485] | 145 / 0 / 191 | 4.48e-44 |

## Retrieval, heldout (20 questions with gold sections)

The concept graph links to 15 of the 38 gold sections of these questions (39%). A share near 100% means the graph was probably written with these questions in mind: read the result as an upper bound.

Mean recall@8 per language set:

| mode | all | ko |
|---|---|---|
| dense | 0.233 | 0.233 |
| dense+kg | 0.300 | 0.300 |
| hybrid | 0.208 | 0.208 |
| hybrid+kg | 0.325 | 0.325 |

Paired differences (bootstrap 95% interval; p from McNemar or a sign-flip permutation test):

| A | B | metric | n | A | B | B − A [95% CI] | better / worse / same | p |
|---|---|---|---|---|---|---|---|---|
| dense | dense+kg | recall | 20 | 0.233 | 0.300 | +0.067 [-0.050, +0.200] | 3 / 1 / 16 | 0.5 |
| dense | dense+kg | all_found | 20 | 0.200 | 0.200 | +0.000 [-0.150, +0.150] | 1 / 1 / 18 | 1 |
| hybrid | hybrid+kg | recall | 20 | 0.208 | 0.325 | +0.117 [+0.017, +0.242] | 4 / 0 / 16 | 0.124 |
| hybrid | hybrid+kg | all_found | 20 | 0.150 | 0.250 | +0.100 [+0.000, +0.250] | 2 / 0 / 18 | 0.5 |
