# Evaluation set (v2)

60 questions, the same in every language file. The asker's nationality is written into the question itself
("I'm Portuguese and work at …"), not tied to the language, so the same persona appears in Korean, German,
Syrian Arabic and so on. That way a difference between two sets is a difference of language only.

| File | Set | Language | Written by | Reviewed |
|---|---|---|---|---|
| [ko.jsonl](ko.jsonl) | `ko` | Korean | project owner (original); 10 balance changes drafted by Claude Opus 5.5 and checked by the owner | yes |
| [en.jsonl](en.jsonl) | `en` | English | project owner (27, from v1) / Claude Opus 5.5 (33 new or changed) | 27 of 60 |
| [de.jsonl](de.jsonl) | `de` | German | Claude Opus 5.5, from `ko` | not yet |
| [ar.jsonl](ar.jsonl) | `ar` | Modern Standard Arabic | Claude Opus 5.5, from `ko` | not yet |
| [ar_sy.jsonl](ar_sy.jsonl) | `ar-SY` | Syrian (Levantine) dialect | Claude Opus 5.5, from `ar` | not yet |
| [it.jsonl](it.jsonl) | `it` | Italian | Claude Opus 5.5, from `ko` | not yet |

The AI drafts (model id `claude-opus-5-5`) were written in the same working session as the rest of the project;
no machine-translation system was used. Questions unchanged since v1 keep their v1 text. The drafts stay drafts
until a native speaker has reviewed them (`translation_reviewed`).

**Balance.** After the first draft, ten questions were changed so that topics and nationalities are less one-sided
(2026-10-13): six got a nationality (Nigerian, Vietnamese, Colombian, Serbian, Filipino, Spanish; for the Serbian
asker the answer changes, because BeschV § 26 Abs. 2 has a special rule for the Western Balkans), three overlapping
work questions were replaced by citizenship (StAG), student health insurance (SGB V) and deregistration (BMG), and
the second benefits refusal became an unemployment-benefit refusal (SGB III, not in the corpus). 28 questions now
name a specific nationality, from every continent.

| | Questions |
|---|---|
| type | 21 `single` · 31 `multi` · 8 `refusal` |
| expected behavior | 52 `answer` · 5 `explain_without_judgment` · 3 `refuse_out_of_scope` |
| persona group | 28 `none` (no nationality) · 23 `non_eu` · 8 `eu` · 1 `both` |
| topic | 21 work · 11 tax · 5 residence · 5 study · 4 social · 3 registration · 3 visa · 2 citizenship · 2 health · 4 other |

## Fields

| Field | Meaning |
|---|---|
| `id` | `n01`–`n60`, the same across files |
| `old_id` | the v1 id (`q01`–`q30`, `t01`–`t15`) if the question comes from v1, else `null` |
| `set` / `lang` | language set (groups results) / language code used by the app |
| `topic` | `work`, `tax`, `residence`, `visa`, `social`, … |
| `type` | `single` (one section answers it), `multi` (several), `refusal` (refuse or explain without judging) |
| `question` | the question as a user would type it |
| `expected_behavior` | `answer`, `refuse_out_of_scope` or `explain_without_judgment` |
| `gold_sections` | the statute sections that answer it, e.g. `AufenthG § 16b Abs. 3`; empty for refusals outside the corpus |
| `persona_country` | ISO code of the asker's nationality as stated in the question (`PT`, `SY`, `BR+AU`), empty if none |
| `persona_group` | `eu`, `non_eu`, `none`, `both` (asks about EU and non-EU citizens) or `unclear` |
| `notes` | why the gold sections and expected behavior are what they are (Korean) |
| `open_question` | something still to check about the item (Korean), if any |
| `question_msa` | `ar_sy` only: the Modern Standard Arabic version |
| `translated_from` / `translated_by` | source set and who wrote the text (`project owner` or `claude-opus-5-5`) |
| `translation_reviewed` | text checked by a native speaker |
| `verified` | gold sections checked by a lawyer (none yet) |

Questions without a nationality (`persona_group: none`) keep the same gold sections in every language: the
nationality is never inferred from the language. Where the answer depends on it, the prompt (v3 and later) answers both cases
(EU/EEA/Swiss and everyone else) and asks the user to state their nationality.

Some questions point to EU law that is not in the corpus: the visa list (Regulation (EU) 2018/1806) and the
Schengen 90/180-day rule (n06, n08, n12). The expected answer covers the German law and names the EU regulation
to consult for the rest; the prompt (v3 and later) asks for exactly that.

`python -m pytest tests/test_evalset.py` checks that the six files are parallel (same ids, gold sections, behavior, persona).

## Splits for LLM runs

[splits.json](splits.json) names small lists of `set:id` items for runs that cost API money
(`python -m evaluation.eval_answers --split validation`):

- `validation`: 30 of the 60 questions, half of each type, each asked in one of the six sets (5 per set)
- `smoke`: 6 other questions, one per set, to check that a run works end to end

## Native-speaker review

```bash
python review/make_review.py
```

writes `review/review_ar.xlsx`, `review_ar_sy.xlsx`, `review_it.xlsx` and `review_de.xlsx`. Reviewers tick ✓ or
write a correction. Apply a returned workbook with

```bash
python review/apply_review.py review_ar_sy.xlsx
```

which shows the changes (dry run); add `--write` to update the `.jsonl` file. Corrected questions keep their old
text in `question_before_review`.

## Held-out questions

[heldout/ko.jsonl](heldout/ko.jsonl) holds 40 Korean questions written by the project owner without seeing the
concept graph (`gesetzpolyglot/concepts.py`), to measure it honestly: the main set was known while the graph was
written. h1–h7 are the owner's own topics, h8–h40 are situations suggested by Claude and worded by the owner. The
gold sections were fixed from the statute text before the graph was run. Keep this set out of graph-building:
once a question has shaped the graph, it no longer measures it. Same fields as the main set, plus `written_by`
and `gold_by`.

## v1 (archived)

[archive/v1/](archive/v1/) holds the first evalset: 62 questions in three modules (core, refugee, tax), where the
asker's nationality depended on the language set (a Syrian asker in Arabic, an Italian one in Italian), plus an
Egyptian-dialect set. The results in the main README up to 2026-10-12 were measured on v1. v2 drops the refugee
module, makes the persona part of the question, adds German, and adds questions on EU free movement, registration,
visa-free stays, artists' social insurance and health insurance.
