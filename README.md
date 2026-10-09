# GesetzPolyglot

Ask about German law in your own language, get answers grounded in the original German statute text.

GesetzPolyglot is a retrieval-augmented QA system for the German laws that matter most to foreigners living in Germany.
The current corpus covers residence, employment and asylum law: the Residence Act (**AufenthG**), the Employment Ordinance (**BeschV**) and the Asylum Act (**AsylG**). Tax law for foreigners is next (see [Roadmap](#roadmap)).
Users ask in Korean, English, Turkish, Arabic, Italian or German; the system retrieves the German statute text, answers with citations, and checks that every citation points to a passage it actually retrieved.
The project compares four retrieval conditions, several LLMs and two prompt versions on the same questions, to see which setup finds the legal basis for an answer most reliably and answers correctly.

> **This is not legal or tax advice.** Use GesetzPolyglot only as an aid. The author accepts no liability for overreliance on its answers or for misuse; see [Disclaimer](#disclaimer).

## Disclaimer

GesetzPolyglot is a research prototype, meant only as an aid for understanding German statutes.

- **Not advice.** It provides general legal information, not legal or tax advice. It does not replace the Ausländerbehörde, the BAMF, asylum procedure counselling, a lawyer or a tax advisor, and it does not assess anyone's individual case.
- **Asylum deadlines are short.** If you have received a decision in an asylum procedure, get advice immediately; some deadlines are one or two weeks.
- **Answers can be wrong.** Answers are generated automatically by a language model. They can be incomplete, outdated or wrong, even when they cite a statute and the citation check passes. The statute snapshot used is shown with every answer.
- **Check the source.** Always read the cited original text on gesetze-im-internet.de, and for your own situation consult a qualified professional.
- **No liability.** To the extent permitted by law, the author accepts no liability for decisions or actions taken on the basis of these answers, for overreliance on them, or for any misuse of this software. The software is provided "as is", without warranty of any kind.

The same notice is shown in the web app, and every answer ends with a short version of it in the language of the question.


## Overview

```
gesetze-im-internet.de XML
        │  gii_parser.py      dated snapshots → Absatz-level chunks + cross-references
        ▼
data/processed/chunks.jsonl   1,378 chunks (AufenthG 916, BeschV 88, AsylG 374)
        │  retrieval.py       bge-m3 embeddings, BM25, vector store (numpy | Chroma)
        ▼
data/index/
        │  rag.py             conditions 1–3: single-pass RAG + citation validation
        │  agent.py           condition 4: LangGraph agent
        ▼
app.py (Gradio UI) · eval_retrieval.py (retrieval, no LLM) · eval_answers.py (end to end, with LLM)
```

| File | Purpose |
|---|---|
| [laws.py](laws.py) | The one list of statutes: which laws exist, which are indexed, and how the corpus is described in prompts and the app. See [Adding a law](#adding-a-law). |
| [gii_parser.py](gii_parser.py) | Downloads the official XML and parses it into one JSONL line per Absatz. Raw snapshots are stored under `data/raw/<law>/<date>/` and never overwritten. |
| [retrieval.py](retrieval.py) | Builds the index; dense, BM25 and hybrid (RRF) search. |
| [rag.py](rag.py) | Retrieve → generate → validate citations. Each answer has a status: `answer`, `refuse_out_of_scope` or `explain_without_judgment`. |
| [agent.py](agent.py) | Splits the question into sub-questions, follows cross-references, checks whether the evidence is sufficient, and retries retrieval up to 2 times. |
| [app.py](app.py) | Gradio web UI in English, with a small German gloss under each element (German is the language of the statutes). Answers come in the language of the question. |
| [eval_retrieval.py](eval_retrieval.py) | Section-level recall@k, no LLM. |
| [eval_answers.py](eval_answers.py) | End-to-end evaluation with the LLM on chosen items: recall, answer status, citations, cost. |
| [evalset/](evalset/) | Evaluation questions (core set and refugee module, six sets each) and [splits.json](evalset/splits.json). |

### The four conditions

| Condition | Description |
|---|---|
| `dense` | bge-m3 dense retrieval, single pass |
| `hybrid` | BM25 + dense fused with RRF, single pass |
| `rewrite` | hybrid + an LLM rewrites the question into German legal search queries |
| `agent` | LangGraph: plan → retrieve → follow_refs → check → answer |

All four share the same final step, `rag.finish()`: the same answer prompt and the same citation check. Differences between conditions therefore come from retrieval alone.

## Setup

Tested with Python 3.11.

```bash
git clone https://github.com/<user>/GesetzPolyglot.git
```

```bash
cd GesetzPolyglot
```

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

`sentence-transformers` pulls in torch. On Linux or Windows without a GPU, install the CPU build first to keep the download small:

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

Known-good versions are pinned in [requirements.lock](requirements.lock).

LLM settings live in `.env`, which is git-ignored:

```bash
cp .env.example .env
```

| Variable | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | | required for OpenAI |
| `LLM_PROVIDER` | `openai` | `openai` or `anthropic` |
| `LLM_MODEL` | `gpt-5.4-mini` / `claude-sonnet-5-5` | chosen from the [answer evaluation](#answer-evaluation-with-the-llm) |
| `LLM_REASONING_EFFORT` | `low` | `none`, `low`, `medium`, `high`; empty = not sent |
| `OPENAI_BASE_URL` | | for compatible servers, e.g. `http://localhost:11434/v1` (Ollama) |
| `PROMPT_VERSION` | `v2` | `v1` or `v2`, see [Answer evaluation](#answer-evaluation-with-the-llm) |

## Usage

### 1. Fetch and parse the statutes

```bash
python gii_parser.py fetch
```

```bash
python gii_parser.py parse
```

A summary (chunk counts, unresolved cross-references) is written to `data/processed/report.json`.

### 2. Build the index

```bash
python retrieval.py build --store chroma
```

Without `--store`, only the numpy store is built. An existing numpy index can be moved to Chroma without re-embedding:

```bash
python retrieval.py to-chroma
```

Search from the command line; `--law` is a metadata filter:

```bash
python retrieval.py search "Zustimmung" --law BeschV --k 5
```

### 3. Ask questions

```bash
python rag.py "Can international students work in Germany?" --condition agent
```

```bash
python app.py
```

The app runs at http://127.0.0.1:7860; `--share` creates a temporary public link.

## Vector stores

`retrieval.py` has two stores with the same interface. Which one is used is recorded as `store` in `data/index/meta.json`.

- **NumpyStore**: exact search, cosine similarity against all of `emb.npy`.
- **ChromaStore**: a persistent ChromaDB collection (`data/index/chroma/`, HNSW, cosine distance). Each chunk carries `law`, `section`, `absatz`, `title` and `snapshot` metadata, so queries can use `where` filters.

BM25 is not part of Chroma and always runs in memory; hybrid fuses the store's dense results with BM25 via RRF.
`emb.npy` is kept even when Chroma is used: the agent uses it to rank Absätze within a section, and it serves as the exact-search baseline.

At 1,378 chunks numpy is fast enough. Chroma was added not for speed but for persistence, metadata filtering, and room to grow when more statutes (e.g. AufenthV) are added.

**Verification.** On the real bge-m3 index and the three-law corpus, all 246 evaluation questions (156 core, 90 refugee module) were run against both stores. Dense and BM25 top-8 lists were identical, 246/246. Hybrid matched on 245/246: hybrid draws 50 dense candidates, and at the low end of that pool HNSW's approximation can shift a ranking by one place. Recall was the same for both stores in every mode.

## Evaluation

The core evaluation set has 30 questions in six sets (the [refugee module](#refugee-and-protection-module) below is a second set). Each set is a language plus the nationality of the person asking:

| Set | File | Asker |
|---|---|---|
| `ko` | [evalset_draft_ko.jsonl](evalset/evalset_draft_ko.jsonl) | Korean (original) |
| `en` | [evalset_draft_en.jsonl](evalset/evalset_draft_en.jsonl) | Korean (translation of `ko`) |
| `tr-TR` | [evalset_draft_tr.jsonl](evalset/evalset_draft_tr.jsonl) | Turkish citizen |
| `ar-SY` | [evalset_draft_ar_sy.jsonl](evalset/evalset_draft_ar_sy.jsonl) | Syrian citizen |
| `ar-PS` | [evalset_draft_ar_ps.jsonl](evalset/evalset_draft_ar_ps.jsonl) | Palestinian |
| `it-IT` | [evalset_draft_it.jsonl](evalset/evalset_draft_it.jsonl) | Italian citizen (EU) |

Turkish, Syrian and Palestinian communities are among the largest immigrant groups in Germany; Italian adds an EU citizen, for whom the Residence Act largely does not apply. Each file has a readable `.md` companion. The Turkish, Arabic and Italian translations have not yet been reviewed by native speakers.

| Type | Per set | Expected behavior |
|---|---|---|
| `single` | 12 | answerable from one section |
| `multi` | 12 | needs several sections combined |
| `refusal` | 6 | out of scope (refuse), or explain the requirements without judging the case |

`it-IT` differs (11 / 10 / 9), see below.

**Wording.** Questions are written the way people in each community actually ask: permits and institutions use the community's usual term, without the German term in parentheses (Korean 블루카드, 아우스빌둥, 안멜둥; English "do an Ausbildung", "do their Anmeldung"; Turkish Mavi Kart, Ausbildung yapmak; Arabic البطاقة الزرقاء, أوسبيلدونغ; Italian Carta Blu UE, fare l'Anmeldung). These terms still need native-speaker review.

**Localization.** Six questions name the asker's nationality (for example "I'm a South Korean citizen…"). In each set they are rewritten for that set's nationality and marked `localized: true`. The nationality changes the correct answer, and sometimes the gold sections:
- **Turkish, Syrian, Palestinian:** gold sections stay the same, but the answer changes. For example, BeschV § 26 Abs. 1 grants an employment privilege to Korean citizens; it does not list Turkey, Syria or Palestine, so the answer must say there is no privilege. The Palestinian set also notes that Germany does not recognise Palestine as a state, so nationality is often recorded as stateless or unclear.
- **Italian:** five questions (q01, q15, q24, q27, q29) become out of scope. EU citizens fall under the Freedom of Movement Act, not the Residence Act (AufenthG § 1 Abs. 2 Nr. 1). The expected behavior becomes `refuse_out_of_scope`, with § 1 Abs. 2 as the gold section. `it-IT` therefore has 11 `single`, 10 `multi` and 9 `refusal` items.

Retrieval recall is measured on the 26 questions per set (156 in total) that have gold sections. A gold section given without an Absatz counts as found if any Absatz of that section is retrieved.

```bash
python eval_retrieval.py --store numpy --modes dense bm25 hybrid
```

```bash
python eval_retrieval.py --store chroma --modes dense bm25 hybrid
```

Per-question results are written to `results/retrieval_<store>_<mode>.jsonl`. The commands above evaluate the core set and the [refugee module](#refugee-and-protection-module); each is reported on its own.

### Current results (recall@8; AufenthG and BeschV as of 2026-10-08, AsylG as of 2026-10-09)

| Mode | All | ko | en | tr-TR | ar-SY | ar-PS | it-IT |
|---|---|---|---|---|---|---|---|
| dense | **0.567** | 0.532 | 0.571 | 0.590 | 0.590 | 0.590 | 0.532 |
| bm25 | 0.019 | 0.000 | 0.038 | 0.038 | 0.000 | 0.000 | 0.038 |
| hybrid | 0.503 | 0.532 | 0.378 | 0.513 | 0.590 | 0.590 | 0.417 |

On `multi` questions (dense): ko 0.444, en 0.486, tr-TR 0.444, ar-SY 0.486, ar-PS 0.486, it-IT 0.483.

Numpy and Chroma give identical recall.

**Findings and limitations**
- Dense retrieval with bge-m3 holds up across all languages (0.532–0.590 on the sets with the same gold sections). Cross-lingual retrieval into German works without translation.
- **German terms in the question help a lot.** An earlier draft wrote terms like "vocational training (Ausbildung)". Removing the German terms in parentheses lowered dense recall from 0.593 to 0.567 overall (Korean 0.571 → 0.532, Arabic 0.628 → 0.590) and left BM25 with almost nothing (0.085 → 0.019). Real users rarely add the German term, so the current numbers are the realistic baseline, and this is the gap `rewrite` is meant to close.
- **A larger corpus did not hurt dense retrieval.** Adding AsylG grew the corpus from 1,004 to 1,378 chunks (+37%). Dense recall stayed exactly the same on all 156 questions: no question lost or gained a gold section, and AsylG chunks entered the top 8 for only 7 questions. Hybrid moved a little in both directions (Turkish 0.551 → 0.513, Italian 0.378 → 0.417), because BM25 now pulls AsylG chunks in as noise for 54 questions. The previous results are kept in `results/before_asylg/`.
- **Scope is not retrieved.** On the five Italian questions where the correct answer is "the Residence Act does not apply to EU citizens", recall is 0 in every mode. Retrieval finds the topic (student work, Blue Card) but never AufenthG § 1 Abs. 2, the section that says the whole topic is out of scope. This is why `it-IT` scores lowest. With prompt v2, `rewrite` adds a scope query and does find § 1 Abs. 2 (see [Answer evaluation](#answer-evaluation-with-the-llm)); a deterministic check that always pulls § 1 Abs. 2 for EU citizens would not depend on the LLM.
- BM25 barely works, because the questions are not in German. How much that hurts hybrid depends on the script:
  - Korean and Arabic share no tokens with German. BM25 returns nothing for 25/26 Korean and 25/26 Arabic questions, so hybrid falls back to dense and loses nothing.
  - English, Turkish and Italian use Latin script, so BM25 almost always finds *some* matching tokens, mostly noise. For English it returns results for 26/26 questions, and hybrid drops from 0.571 to 0.378.
  - The `rewrite` condition, which turns questions into German queries, targets exactly this.
- Recall on `multi` questions is low. The `agent` condition, which follows cross-references, targets this.
- The Syrian and Palestinian sets differ only in six localized questions, and their recall is identical. Nationality wording barely moves retrieval; it matters for the answer, which only the [answer evaluation](#answer-evaluation-with-the-llm) can check.
- The evaluation set is a draft: gold sections were written by hand and have not yet been verified.
- Conditions 3–4 (`rewrite`, `agent`) and answer quality are evaluated with the LLM on smaller splits; see [Answer evaluation with the LLM](#answer-evaluation-with-the-llm).

### Refugee and protection module

A second, separate question set covers refugee status, subsidiary protection, Duldung, family reunification and the asylum procedure: 17 questions (9 `single`, 4 `multi`, 4 `refusal`), files `evalset/evalset_refugee_<set>.jsonl` with readable `.md` companions. The questions do not mention nationality, so they are identical in all six sets and comparable across languages. They are reported separately from the core set (`module: refugee`), because they are different questions. Gold sections were checked against the statute text but are not yet `verified`.

| Mode | All | ko | en | tr-TR | ar-SY | ar-PS | it-IT |
|---|---|---|---|---|---|---|---|
| dense | **0.456** | 0.400 | 0.467 | 0.467 | 0.400 | 0.400 | 0.600 |
| bm25 | 0.017 | 0.000 | 0.000 | 0.100 | 0.000 | 0.000 | 0.000 |
| hybrid | 0.406 | 0.400 | 0.400 | 0.433 | 0.400 | 0.400 | 0.400 |

- **The misses are not about language.** Six questions (r01, r04, r08, r11, r13, r15) score 0 in all six languages. The cause is how the statutes are written: they rarely say "refugee". AufenthG § 26 Abs. 3, the settlement permit for refugees, only says "a residence permit under § 25 Absatz 1 or 2"; § 25 Abs. 2 and § 12a Abs. 1 refer to "international protection under Regulation (EU) 2024/1347". A question that says "refugee" has nothing to match. Candidate fixes: add the titles of referenced sections to the indexed text (so § 26 Abs. 3 also carries "Aufenthalt aus humanitären Gründen"), or let the `agent` follow these references.
- Some misses do depend on language: the asylum lawsuit deadline (r09, AsylG § 74 Abs. 1) is found in Korean and Italian but not in the other four.

### Answer evaluation with the LLM

[eval_answers.py](eval_answers.py) runs the whole pipeline, LLM included, on chosen items. For each condition it records the recall@8 of what the answer step receives, whether the answer's status matches `expected_behavior`, citations that are not in the retrieved text, LLM calls, latency and tokens. This costs money, so it runs on small named splits from [evalset/splits.json](evalset/splits.json):

- `dev`: 10 hard items (dense recall 0) used to diagnose prompt v1 and write v2.
- `validation`: 20 random items, stratified by module and type. Their question ids never appear in `dev`, in any language. Used to check that v2 holds up on questions it was not written for.

```bash
python eval_answers.py --split validation
```

```bash
python eval_answers.py --split dev --prompts v1 --model gpt-5.4
```

Without `--model` and `--prompts` it uses the defaults (gpt-5.4-mini, v2).

**Prompt versions.** Both live in [rag.py](rag.py) and [agent.py](agent.py); `PROMPT_VERSION` (or `--prompts`) picks one, v2 by default. Compared with v1, v2 tells the model to check scope first (EU/EEA citizens: AufenthG § 1 Abs. 2, plus a scope query in `rewrite` and the agent's plan), to use `explain_without_judgment` only when asked to predict the user's own case, to answer the covered part of a question instead of refusing, to read each provision's Absatz, Satz and named group exactly, to say when the user's country is not in a list, and to correct wrong assumptions. A status line that does not name exactly one status is scored as `unclear` (wrong).

**Validation** (20 items × 4 conditions = 80 answers per run):

| Model | Prompts | Status matches | `unclear` | recall@8 rewrite | recall@8 agent | Cost |
|---|---|---|---|---|---|---|
| gpt-5.4-nano | v1 | 58/80 | 3 | 0.559 | 0.529 | $0.12 |
| gpt-5.4-nano | v2 | 71/80 | 6 | 0.500 | 0.676 | $0.12 |
| gpt-5.4-mini | v2 | **79/80** | 0 | 0.471 | 0.765 | $0.42 |
| gpt-5.4 | v1 | 60/80 | 0 | 0.588 | 0.676 | $1.35 |
| gpt-5.4 | v2 | **79/80** | 0 | 0.647 | 0.647 | $1.51 |

Without the LLM, the same 20 items give dense 0.765 and hybrid 0.588.

**Dev** (10 hard items; status matches and recall@8 for `rewrite` / `agent`):

| Model | Prompts | Status matches | recall@8 |
|---|---|---|---|
| gpt-5.4-nano | v1 | 4 / 5 | 0.45 / 0.65 |
| gpt-5.4 | v1 | 8 / 8 | 0.50 / 0.40 |
| gpt-5.4-nano | v2 | 8 / 6 | 0.60 / 0.55 |
| gpt-5.4-mini | v2 | 9 / 10 | 0.65 / 0.50 |
| gpt-5.4 | v2 | 10 / 10 | 0.60 / 0.65 |

Costs are API token counts times list prices (gpt-5.4: $2.50 / $15 per 1M input / output tokens; gpt-5.4-mini: $0.75 / $4.50 and gpt-5.4-nano: $0.20 / $1.25, as listed by third-party trackers). All LLM experiments so far cost about $5.40. Average time per question with the agent on the validation set: nano 14 s, mini 10 s, gpt-5.4 24 s.

**Findings**
- **gpt-5.4-mini matches gpt-5.4 at about a quarter of the cost.** With v2 it got 79/80 on validation (same as gpt-5.4), made no format errors, and was the fastest. On the dev items it gave correct answers where nano failed: it cited § 1 Abs. 2 for the Italian EU-citizen question, separated § 26 Abs. 3 (refugees) from Abs. 4 (subsidiary protection), and corrected the Blue Card premise. It is now the default model.
- **v2's own examples can leak into citations.** Once, mini cited AufenthG § 1 Abs. 2 although it was not retrieved; the prompt mentions it in the scope rule. The citation check flags this (`invalid`), which is what it is for.
- **v2 holds up on unseen items.** Status matches rose from 58 to 71 (nano) and from 60 to 79 (gpt-5.4). The main v1 error, answering a plain question about the rules with "I can't judge your case", almost disappears.
- **Most remaining nano errors are format errors.** 6 of nano's 9 misses with v2 are a copied template line ("STATUS: answer | refuse_out_of_scope"). gpt-5.4 and gpt-5.4-mini never did this.
- **A matching status is not a correct answer.** On the dev set, gpt-5.4 with v1 described subsidiary protection with the numbering from before the 2024 reform (§ 25 Abs. 2 Satz 1, "second alternative"), contradicting the excerpt in front of it. A stronger model can fall back on outdated training knowledge, so answers still have to be read.
- **`rewrite` helps on hard questions and hurts on easy ones.** On the dev items dense found nothing and `rewrite` reached 0.45–0.60. On the random validation items dense is better (0.765 vs 0.50–0.65): `rewrite` searches only the LLM's German queries and drops the original question, and the queries sometimes drift (q09: § 82 Abs. 1 instead of Abs. 6). Searching the original question together with the rewritten queries should keep both gains.
- **Some misses are gold sections that are too narrow.** For r08, gpt-5.4 answered correctly from AufenthG § 12a Abs. 2–4, but the gold names only Abs. 1.

## Adding a law

All statute names come from [laws.py](laws.py). To add one:

1. Add it to `LAWS` (abbreviation → gesetze-im-internet.de slug) and to `CORPUS`; update `TOPIC` and `OUT_OF_SCOPE` if the subject area changes.
2. Fetch, parse and rebuild the index:

```bash
python gii_parser.py fetch
```

```bash
python gii_parser.py parse
```

```bash
python retrieval.py build --store chroma
```

3. Re-run the evaluation and compare with the previous corpus.

AsylG was the first law added this way. Its text is the version after the 2024 EU asylum reform (in force since June 2026): 86 of its 374 chunks refer to EU Regulations 2024/1347, 2024/1348 or 2024/1351, which are not on gesetze-im-internet.de and not in the corpus. The answer prompt tells the model to say so instead of filling in the details.

## Roadmap

**Tax law for foreigners.** The next corpus extension covers the tax questions foreigners typically face, such as when they become taxable in Germany, how income is taxed under limited tax liability, and how double taxation is avoided. Candidate sources are the Income Tax Act (EStG) and the Fiscal Code (AO), both available from gesetze-im-internet.de in the same XML format as the current corpus. Double taxation treaties are published separately and would need their own ingestion step.

What this involves:
- adding EStG and AO to [laws.py](laws.py) (see [Adding a law](#adding-a-law))
- tax questions in the evaluation set (single, multi, refusal), in every set; nationality matters even more here (e.g. double taxation treaties differ by country)
- extending the refusal rules from individual residence decisions to individual tax assessments

**Other planned work**
- index the titles of referenced sections with each chunk, so provisions that only cite "§ 25 Absatz 2" can still be found (see the refugee module findings)
- the EU asylum regulations (2024/1347, 2024/1348, 2024/1351) from EUR-Lex, which needs its own parser
- `rewrite`: search the original question together with the rewritten queries (see the answer evaluation findings)
- a format fix for small models that copy the status template, if gpt-5.4-nano is used to save cost
- a full answer evaluation over all 246 questions with the chosen model and prompt version (about $5 with the default gpt-5.4-mini; $1.5 with nano, $19 with gpt-5.4; extrapolated from the validation runs)
- a deterministic scope check for EU citizens, so § 1 Abs. 2 is always retrieved rather than left to the LLM's queries
- a setting to switch the app's main UI language (e.g. Turkish, Arabic, Italian, Korean); the German gloss stays on by default
- verify the gold sections in the evaluation set (some are too narrow, see the answer evaluation findings), and have native speakers review the Turkish, Arabic and Italian translations
- add the Residence Ordinance (AufenthV); the parser already knows it

## Tests

```bash
python -m pytest -q
```

Tests use a fake embedder, so they run without the bge-m3 model or an API key.

## Not in git

`data/index/` (embeddings and Chroma), `results/`, `.env` and `.venv/` are git-ignored. To reproduce, run steps 1–2 above, then `eval_retrieval.py` and `eval_answers.py`; the item lists for the LLM runs are in [evalset/splits.json](evalset/splits.json).

A Korean version of this README is in [README.ko.md](README.ko.md).
