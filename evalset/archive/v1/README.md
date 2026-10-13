# Evaluation set

One file per language set. Each file holds the same 62 questions in three modules:

| Module | Questions | Topic |
|---|---|---|
| `core` | q01–q30 | residence and work |
| `refugee` | r01–r17 | refugee status, protection, Duldung, asylum procedure |
| `tax` | t01–t15 | income tax and pension insurance |

| File | Set | Asker | Written by | Reviewed |
|---|---|---|---|---|
| [ko.jsonl](ko.jsonl) | `ko` | Korean | project owner (original) | yes |
| [en.jsonl](en.jsonl) | `en` | Korean | project owner (translation of `ko`) | yes |
| [ar.jsonl](ar.jsonl) | `ar` | Syrian citizen, Modern Standard Arabic | Claude Opus 5.5, translated from `ko` / `en` | not yet |
| [ar_sy.jsonl](ar_sy.jsonl) | `ar-SY` | Syrian citizen, Syrian (Levantine) dialect | Claude Opus 5.5, written from `ar` | not yet |
| [ar_eg.jsonl](ar_eg.jsonl) | `ar-EG` | Egyptian citizen, Egyptian dialect | Claude Opus 5.5, written from `ar` (Egyptian asker) | not yet |
| [it.jsonl](it.jsonl) | `it-IT` | Italian citizen (EU) | Claude Opus 5.5, translated from `ko` / `en` | not yet |

The Arabic and Italian questions are AI drafts (Claude Opus 5.5, model id `claude-opus-5-5`), written in the
same working session as the rest of the project; no machine-translation system was used for them. They stay drafts
until a native speaker has reviewed them. (NLLB-200 appears only in the retrieval experiment, `query_translate.py`.)

## Fields

| Field | Meaning |
|---|---|
| `id` | question id, the same across sets (`q15` is the same question in every file) |
| `module` | `core`, `refugee` or `tax` |
| `set` | language set, used to group results |
| `lang` | language code used by the app (`ko`, `en`, `ar`, `it`) |
| `type` | `single` (one section answers it), `multi` (several sections), `refusal` (refuse or explain without judging) |
| `question` | the question as a user would type it |
| `expected_behavior` | `answer`, `refuse_out_of_scope` or `explain_without_judgment` |
| `gold_sections` | the statute sections that answer it, e.g. `AufenthG § 16b Abs. 3`; empty for refusals outside the corpus |
| `notes` | why the gold sections and expected behavior are what they are (Korean) |
| `localized` | `true` if the question names the asker's nationality and was rewritten for this set |
| `question_en` | English version of a localized question |
| `question_msa` | dialect sets only: the Modern Standard Arabic version |
| `translated_from` / `translated_by` | source set and who wrote the translation (`project owner` or `claude-opus-5-5`) |
| `verified` | gold sections checked by a person (none yet) |
| `translation_reviewed` | translation checked by a native speaker |

A localized question can have a different correct answer per set: for the Italian (EU) asker several
residence questions are out of scope, and the tax questions on joint taxation and Kindergeld change.

## Splits for LLM runs

[splits.json](splits.json) names small lists of `set:id` items for runs that cost API money
(`python eval_answers.py --split validation`):

- `dev`: 10 hard items used to write prompt v2
- `validation`: 20 random items never seen while writing the prompts
- `tax`: all 15 tax questions once, languages rotated

The notes in that file record when items were replaced (a former set, the dropped Turkish set).

## Native-speaker review

```bash
python review/make_review.py
```

writes one workbook per reviewed set to `review/` (`review_ar.xlsx`, `review_ar_sy.xlsx`, `review_ar_eg.xlsx`,
`review_it.xlsx`). Reviewers tick ✓ or write a correction. Apply a returned workbook with

```bash
python review/apply_review.py review_ar_sy.xlsx
```

which shows the changes (dry run); add `--write` to update the `.jsonl` file. Corrected questions keep their old
text in `question_before_review`.
