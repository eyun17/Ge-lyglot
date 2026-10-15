# Experiment kg-2026-10-15-fixes: with and without the concept graph

See manifest.json for the commit, prompt version, model, index and concept graph version.

## Retrieval, main (336 questions with gold sections)

The concept graph links to 95 of the 98 gold sections of these questions (97%). A share near 100% means the graph was probably written with these questions in mind: read the result as an upper bound.

Mean recall@8 per language set:

| mode | all | ko | en | de | ar | ar-SY | it |
|---|---|---|---|---|---|---|---|
| dense | 0.353 | 0.330 | 0.375 | 0.432 | 0.339 | 0.256 | 0.384 |
| dense+kg | 0.818 | 0.830 | 0.839 | 0.818 | 0.833 | 0.759 | 0.827 |
| hybrid | 0.299 | 0.330 | 0.304 | 0.265 | 0.339 | 0.256 | 0.301 |
| hybrid+kg | 0.816 | 0.830 | 0.830 | 0.836 | 0.833 | 0.759 | 0.810 |

Paired differences (bootstrap 95% interval; p from McNemar or a sign-flip permutation test):

| A | B | metric | n | A | B | B − A [95% CI] | better / worse / same | p |
|---|---|---|---|---|---|---|---|---|
| dense | dense+kg | recall | 336 | 0.353 | 0.818 | +0.465 [+0.419, +0.512] | 207 / 2 / 127 | 0.0001 |
| dense | dense+kg | all_found | 336 | 0.262 | 0.708 | +0.446 [+0.393, +0.500] | 150 / 0 / 186 | 1.4e-45 |
| hybrid | hybrid+kg | recall | 336 | 0.299 | 0.816 | +0.517 [+0.471, +0.564] | 220 / 0 / 116 | 0.0001 |
| hybrid | hybrid+kg | all_found | 336 | 0.223 | 0.702 | +0.479 [+0.426, +0.533] | 161 / 0 / 175 | 6.84e-49 |

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
