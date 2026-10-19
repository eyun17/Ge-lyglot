# Ge(setz)🇩🇪(Po)lyglot 🤖
Ask about German law in your own language, get answers grounded in the original German statute text.

**Try it: [huggingface.co/spaces/eyun/gesetzpolyglot](https://huggingface.co/spaces/eyun/gesetzpolyglot)** (bring your own OpenAI, Claude or Gemini API key; see [Sharing the app](#sharing-the-app))

Ge-lyglot, which is a short name of Gesetz-Polyglot, is a retrieval-augmented QA system for the German laws that matter most to foreigners living in Germany.
Users ask in Korean, English, German, Italian or Arabic (Modern Standard or Syrian dialect); questions in other languages get a short note asking them to rephrase, without an LLM call. The system retrieves the German statute text, answers in the language of the question with citations, and checks that every citation points to a passage it actually retrieved.
The project compares four retrieval conditions, several LLMs and four prompt versions on the same questions, to see which setup finds the legal basis for an answer most reliably and answers correctly. It is evaluated in Korean, English, German, Arabic (Modern Standard Arabic and Syrian dialect) and Italian.

The corpus has fourteen federal laws (10,029 Absatz-level chunks):

| Area | Laws |
|---|---|
| Residence and work | **AufenthG** (Residence Act), **AufenthV** (Residence Ordinance), **BeschV** (Employment Ordinance) |
| EU citizens | **FreizügG/EU** (Freedom of Movement Act) |
| Asylum | **AsylG** (Asylum Act) |
| Citizenship and registration | **StAG** (Nationality Act), **BMG** (Federal Registration Act) |
| Tax | **EStG** (Income Tax Act), **AO** (Fiscal Code) |
| Social insurance | **SGB IV** (common rules), **SGB VI** (pension), **SGB V** (health), **VVG** § 193 (duty to have health insurance), **KSVG** (artists' social insurance) |

Not in the corpus: unemployment and long-term care insurance, VAT, church tax, the broadcasting fee (Rundfunkbeitrag), double taxation treaties, benefits such as Bürgergeld, and EU regulations (visa list, Schengen rules, the 2024 asylum regulations). Questions on these are answered with a referral or refused.

> **This is not legal or tax advice.** Use GesetzPolyglot only as an aid. The author accepts no liability for overreliance on its answers or for misuse; see [Disclaimer](#disclaimer).

<a id="disclaimer"></a>

## ⚠️ Disclaimer ⚠️

GesetzPolyglot is a research prototype, meant only as an aid for understanding German statutes.

- **Not advice.** It provides general legal information, not legal or tax advice. It does not replace the Ausländerbehörde, the BAMF, asylum procedure counselling, a lawyer or a tax advisor, and it does not assess anyone's individual case.
- **Asylum deadlines are short.** If you have received a decision in an asylum procedure, get advice immediately; some deadlines are one or two weeks.
- **Answers can be wrong.** Answers are generated automatically by a language model. They can be incomplete, outdated or wrong, even when they cite a statute and the citation check passes. The statute snapshot used is shown with every answer.
- **Check the source.** Always read the cited original text on gesetze-im-internet.de, and for your own situation consult a qualified professional.
- **No liability.** To the extent permitted by law, the author accepts no liability for decisions or actions taken on the basis of these answers, for overreliance on them, or for any misuse of this software. The software is provided "as is", without warranty of any kind.

The same notice is shown in the web app, and every answer ends with a short version of it in the language of the question.


## How it works

The same explanation is shown in the app, under "How was this app built?".

1. **The statutes.** The 14 federal laws are downloaded as XML from gesetze-im-internet.de and split into 10,029 paragraphs (Absätze). Every paragraph keeps its citation, its date and the sections it refers to.
2. **Search across languages.** A multilingual embedding model (bge-m3) turns every paragraph and the question into vectors, so a question in Korean or Arabic finds German text by meaning, not by words. A keyword search (BM25) can be added, fused by rank (RRF).
3. **Retrieval-augmented generation (RAG).** The language model does not answer from memory. It gets only the paragraphs the search found and must cite them, e.g. [AufenthG § 16b Abs. 3]. There are four search strategies; the most thorough one (the agent) splits the question, writes German legal search terms, follows cross-references between sections and searches again if something is missing.
4. **Checking the answer.** Every citation is checked against the paragraphs that were actually found; citations that were not are flagged. The answer also states its type: an answer, out of scope, or only the requirements without judging the user's case.
5. **Knowledge graph (experimental).** People ask with everyday words ("Anmeldung", "get my taxes back") that the statutes do not use. A small hand-built graph links such concepts, in five languages, and nationality groups (EU citizens, the countries privileged in AufenthV § 41, the Western Balkans) to the sections that answer them, and adds those sections to the search. It is off by default while it is being evaluated (`--kg` turns it on); see [the experiment](#experiment-a-multilingual-concept-graph).
6. **Evaluation.** The system is tested on 60 questions asked in six language sets, with the statute sections that answer them; the knowledge graph is also tested on questions written without seeing it. See [Evaluation](#evaluation).

## Overview

```
gesetze-im-internet.de XML
        │  gii_parser      dated snapshots → Absatz-level chunks + cross-references
        ▼
data/processed/chunks.jsonl   10,029 chunks (AufenthG 916, AufenthV 293, BeschV 88, AsylG 374,
                              FreizügG/EU 89, StAG 84, BMG 191, EStG 994, AO 1,427,
                              SGB IV 705, SGB VI 1,294, SGB V 2,911, VVG 524, KSVG 139)
        │  retrieval       bge-m3 embeddings, BM25, vector store (numpy | Chroma)
        ▼
data/index/
        │  rag             conditions 1–3: single-pass RAG + citation validation
        │  agent           condition 4: LangGraph agent
        ▼
app.py (Gradio UI) · evaluation/ (retrieval without LLM, end to end with LLM)
```

```
app.py                  Gradio web app (entry point)
gesetzpolyglot/         the system
  laws.py               the one list of statutes
  gii_parser.py         fetch and parse the official XML
  retrieval.py          index, dense / BM25 / hybrid search
  llm.py                LLM clients (OpenAI, Anthropic, Ollama) and --provider / --model
  prompts.py            all prompts, every version
  concepts.py, kg.py    experiment: multilingual concept graph for retrieval
  rag.py                conditions 1–3 and the shared answer step
  agent.py              condition 4 (LangGraph)
evaluation/             eval_retrieval.py, eval_answers.py, ablation.py, compare.py, query_translate.py
evalset/                evaluation questions (v2; v1 in archive/)
review/                 translation review workbooks and their scripts
tests/                  pytest, no model or API key needed
data/                   raw snapshots, parsed chunks, index (git-ignored)
results/                evaluation output (git-ignored)
```

| File | Purpose |
|---|---|
| [gesetzpolyglot/laws.py](gesetzpolyglot/laws.py) | The one list of statutes: which laws exist, which are indexed, and how the corpus is described in prompts and the app. See [Adding a law](#adding-a-law). |
| [gesetzpolyglot/gii_parser.py](gesetzpolyglot/gii_parser.py) | Downloads the official XML and parses it into one JSONL line per Absatz. Raw snapshots are stored under `data/raw/<law>/<date>/` and never overwritten. |
| [gesetzpolyglot/retrieval.py](gesetzpolyglot/retrieval.py) | Builds the index; dense, BM25 and hybrid (RRF) search. |
| [gesetzpolyglot/llm.py](gesetzpolyglot/llm.py) | LLM clients (OpenAI-compatible, Anthropic, Ollama), `.env` loading and the `--provider` / `--model` options shared by every script that calls an LLM. |
| [gesetzpolyglot/prompts.py](gesetzpolyglot/prompts.py) | Every prompt in every version (v1–v4, v4 by default); `PROMPT_VERSION` picks one. |
| [gesetzpolyglot/rag.py](gesetzpolyglot/rag.py) | Retrieve → generate → validate citations. Each answer has a status: `answer`, `refuse_out_of_scope` or `explain_without_judgment`. |
| [gesetzpolyglot/concepts.py](gesetzpolyglot/concepts.py), [kg.py](gesetzpolyglot/kg.py) | Experiment: a hand-written multilingual concept graph that adds the sections behind everyday words to the search (see [the experiment](#experiment-a-multilingual-concept-graph)). |
| [gesetzpolyglot/agent.py](gesetzpolyglot/agent.py) | Splits the question into sub-questions, follows cross-references, checks whether the evidence is sufficient, and retries retrieval up to 2 times. |
| [app.py](app.py) | Gradio web UI in English, with a small German gloss under each element (German is the language of the statutes). Answers come in the language of the question. A Sources panel lists every statute with its download date and last amendment, and "How was this app built?" explains the pipeline ([How it works](#how-it-works)). `--kg` turns on the concept graph. |
| [evaluation/eval_retrieval.py](evaluation/eval_retrieval.py) | Section-level recall@k, no LLM. |
| [evaluation/eval_answers.py](evaluation/eval_answers.py) | End-to-end evaluation with the LLM on chosen items: recall, answer status, citations, cost. |
| [evaluation/ablation.py](evaluation/ablation.py), [compare.py](evaluation/compare.py), [manifest.py](evaluation/manifest.py) | One command for a comparison with and without the concept graph; paired statistics (bootstrap intervals, McNemar, permutation test); a record of what each run depended on. See [Comparing runs](#comparing-runs-with-and-without-the-graph). |
| [evaluation/query_translate.py](evaluation/query_translate.py) | Experiment: translates questions with a local NLLB-200 model before retrieval (non-commercial license, not used by the app). |
| [evalset/](evalset/) | Evaluation questions: 60 questions, the same in each of six language files; see [evalset/README.md](evalset/README.md) and [splits.json](evalset/splits.json). The first version is kept in `evalset/archive/v1/`. |
| [review/](review/) | Translation review workbooks (.xlsx) for native speakers: German, Arabic (MSA), Syrian dialect, Italian. Built by [make_review.py](review/make_review.py), returned workbooks are applied with [apply_review.py](review/apply_review.py). |

Commands run from the project root as modules, e.g. `python -m gesetzpolyglot.retrieval build`; only the app is started with `python app.py`.

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
git clone https://github.com/eyun17/Ge-lyglot.git
```

```bash
cd Ge-lyglot
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

`requirements.txt` lists only the packages the code uses directly, without exact versions, so a fresh install gets current releases. [requirements.lock](requirements.lock) pins every package, dependencies included, to the versions this project was last tested with (Python 3.11, macOS, updated 2026-10-13). If a newer release breaks something, install those instead:

```bash
pip install -r requirements.lock
```

Run the scripts with the virtual environment's Python. If another environment is active (for example conda's `(base)`), `python` may point elsewhere and fail with `No module named 'gradio'`; `.venv/bin/python app.py` always uses the right one.

LLM settings live in `.env`, which is git-ignored:

```bash
cp .env.example .env
```

| Variable | Default | Notes |
|---|---|---|
| `OPENAI_API_KEY` | | required for OpenAI |
| `LLM_PROVIDER` | `openai` | `openai`, `anthropic` or `ollama` (local), see [Choose the LLM](#4-choose-the-llm-api-or-local) |
| `LLM_MODEL` | `gpt-5.4-mini` / `claude-sonnet-5-5` | chosen from the [answer evaluation](#answer-evaluation-with-the-llm) |
| `LLM_REASONING_EFFORT` | `low` | `none`, `low`, `medium`, `high`; empty = not sent |
| `OPENAI_BASE_URL` | | for other OpenAI-compatible servers |
| `OLLAMA_MODEL` | `qwen3:8b` | model for `ollama` |
| `OLLAMA_URL` | `http://localhost:11434` | |
| `OLLAMA_NUM_CTX` | `16384` | context window for local models |
| `PROMPT_VERSION` | `v4` | `v1` to `v4`, see [Prompt versions](#prompt-versions) |

## Usage

### 1. Fetch and parse the statutes

```bash
python -m gesetzpolyglot.gii_parser fetch
```

```bash
python -m gesetzpolyglot.gii_parser parse
```

A summary (chunk counts, unresolved cross-references) is written to `data/processed/report.json`.

### 2. Build the index

```bash
python -m gesetzpolyglot.retrieval build --store chroma
```

Without `--store`, only the numpy store is built. An existing numpy index can be moved to Chroma without re-embedding:

```bash
python -m gesetzpolyglot.retrieval to-chroma
```

Search from the command line; `--law` is a metadata filter:

```bash
python -m gesetzpolyglot.retrieval search "Zustimmung" --law BeschV --k 5
```

### 3. Ask questions

```bash
python -m gesetzpolyglot.rag "Can international students work in Germany?" --condition agent
```

```bash
python app.py
```

The app runs at http://127.0.0.1:7860; `--share` creates a temporary public link.

**Whose API key?** By default every user enters their own key in the app (OpenAI, Claude or Google Gemini) and pays for their own questions; the operator's keys are removed from the app's environment at start, so a request can never fall back to them. The key lives only in that browser session and is never stored, logged or shown. To answer with your own key from `.env` instead, for local tests or your own demos, start the app with `--server-key`:

```bash
python app.py --server-key
```

The evaluation scripts are not affected: they always use the key and model from `.env` (or `--provider` / `--model`).

### 4. Choose the LLM: API or local

Every script that calls an LLM (`gesetzpolyglot.rag`, `evaluation.eval_answers`, and `app.py` with `--server-key`) takes `--provider` and `--model`. They override `.env`.

| Provider | Runs | Model setting | Default |
|---|---|---|---|
| `openai` | OpenAI API, costs money | `LLM_MODEL` | `gpt-5.4-mini` |
| `anthropic` | Anthropic API, costs money | `LLM_MODEL` | `claude-sonnet-5-5` |
| `ollama` | locally with [Ollama](https://ollama.com), free | `OLLAMA_MODEL` | `qwen3:8b` |

A local model needs Ollama running and the model pulled once:

```bash
ollama pull qwen3:8b
```

```bash
python app.py --server-key --provider ollama
```

```bash
python -m evaluation.eval_answers --split validation --provider ollama --model llama3:8b
```

```bash
python app.py --server-key --provider openai --model gpt-5.4
```

For Ollama the code uses its native API rather than the OpenAI-compatible one, so it can set the context window (`OLLAMA_NUM_CTX`, default 16,384 tokens; Ollama's own default is a few thousand and silently cuts long prompts, here the answer rules) and switch off "thinking" for reasoning models such as qwen3. On a 16 GB Mac, 8B models fit next to the embedding model; expect tens of seconds per answer and a few minutes per agent question.


## Sharing the app

Both ways below are free for the operator: in the default mode every user brings their own API key, and the search runs on the CPU.

**A temporary link from your own computer.** The link works while the app runs on your machine and expires after 72 hours; good for a demo or an interview.

```bash
python app.py --share
```

**A permanent page on Hugging Face Spaces (free, on ZeroGPU).** The project's Space is [huggingface.co/spaces/eyun/gesetzpolyglot](https://huggingface.co/spaces/eyun/gesetzpolyglot). Free accounts can host Gradio Spaces only on ZeroGPU hardware (CPU Spaces need PRO); the app detects it and embeds questions on the GPU, which counts against each visitor's own daily ZeroGPU quota, not the operator's. [deploy/make_space.py](deploy/make_space.py) builds a self-contained folder: the app, the `gesetzpolyglot` package, the example questions, the search index (numpy store only, 55 MB in all) and the Space configuration (torch 2.13, the newest version ZeroGPU supports). It never copies `.env`, results or raw downloads, and stops if anything in the folder looks like an API key.

```bash
python deploy/make_space.py
```

Then create a Space (SDK: Gradio) on huggingface.co and upload the folder; `hf` comes with `huggingface_hub` and needs `hf auth login` once:

```bash
hf upload <user>/<space-name> dist/hf_space . --repo-type space
```

If the `hf` command is not found, run it as `python -m huggingface_hub.cli.hf` (same arguments).

The first start downloads bge-m3 (about 2 GB) and takes a few minutes; a free Space sleeps when nobody uses it and wakes on the next visit. Do not add your own API key as a Space secret: the Space runs in the bring-your-own-key mode. Choose a licence for the code before publishing (there is none in the repository yet).

## Vector stores

`gesetzpolyglot/retrieval.py` has two stores with the same interface. Which one is used is recorded as `store` in `data/index/meta.json`.

- **NumpyStore**: exact search, cosine similarity against all of `emb.npy`.
- **ChromaStore**: a persistent ChromaDB collection (`data/index/chroma/`, HNSW, cosine distance). Each chunk carries `law`, `section`, `absatz`, `title` and `snapshot` metadata, so queries can use `where` filters.

BM25 is not part of Chroma and always runs in memory; hybrid fuses the store's dense results with BM25 via RRF.
`emb.npy` is kept even when Chroma is used: the agent uses it to rank Absätze within a section, and it serves as the exact-search baseline.

At 10,029 chunks numpy is still fast enough. Chroma was added not for speed but for persistence, metadata filtering, and room to grow as more statutes are added.

**Verification.** On the real bge-m3 index, the 336 questions of evalset v2 that have gold sections give almost the same recall with both stores (dense 0.354 numpy vs 0.353 Chroma); dense returned identical top-8 lists for 307/336. Earlier, with the 324 questions of v1: on the thirteen-law corpus (9,890 chunks) the top-8 lists were identical for 313/324 questions with dense, 324/324 with BM25 and 309/324 with hybrid; on the three-law corpus (1,378 chunks) dense had matched every question. HNSW's approximation shows as the corpus grows, but it only reordered results: recall was the same for both stores in every mode and on every corpus size.

## Evaluation

The evaluation set has 60 questions, and every one of them is asked in six languages: Korean (original), English, German, Modern Standard Arabic, Syrian dialect and Italian. The nationality of the person asking is written into the question itself ("I'm Portuguese and work at the head office of a Spanish company…"), not tied to the language, so a difference between two sets is a difference of language only. Each question records that nationality as `persona_country` and `persona_group` (`eu`, `non_eu`, `none` when no nationality is given, `both`). [evalset/README.md](evalset/README.md) explains the fields; the first version of the set is archived (see [Evaluation set v1](#evaluation-set-v1-archived)).

| Set | File | Language | Written by |
|---|---|---|---|
| `ko` | [ko.jsonl](evalset/ko.jsonl) | Korean | project owner (original; 10 balance changes drafted by Claude Opus 5.5, checked by the owner) |
| `en` | [en.jsonl](evalset/en.jsonl) | English | project owner (27) / Claude Opus 5.5 (33 new or changed) |
| `de` | [de.jsonl](evalset/de.jsonl) | German | Claude Opus 5.5 |
| `ar` | [ar.jsonl](evalset/ar.jsonl) | Modern Standard Arabic | Claude Opus 5.5 |
| `ar-SY` | [ar_sy.jsonl](evalset/ar_sy.jsonl) | Syrian (Levantine) dialect | Claude Opus 5.5 |
| `it` | [it.jsonl](evalset/it.jsonl) | Italian | Claude Opus 5.5 |

The questions cover work and residence permits (21), tax (11), residence and settlement (5), study and Ausbildung (5), social, pension and artists' insurance (4), registration (3), visas and visa-free stays (3), citizenship (2), health insurance (2), EU free movement, family members of EU citizens and the broadcasting fee. 21 are `single` (one section answers them), 31 `multi` (several sections) and 8 `refusal` (out of scope, or explain the rules without judging the user's own case). 28 questions name a specific nationality, from every continent: 21 non-EU (Syrian and Korean twice; American, Canadian, Mexican, Colombian, Nigerian, Kenyan, South African, Indian, Vietnamese, Filipino, Chinese, Japanese, Taiwanese, Turkish, Serbian, Ukrainian, Brazilian-Australian) and 7 EU (Italian, Polish, Portuguese, Dutch, French, Austrian, Spanish); three more ask about non-EU or EU citizens in general, and one about both. Ten questions were adjusted after the first draft to even out topics and nationalities ([evalset/README.md](evalset/README.md#evaluation-set-v2)).

German was added as a question language: it is the language of the statutes, so it shows how much of the gap is language and how much is everyday words against legal ones. Syrian dialect stays because people type in dialect; MSA is its baseline. Text that was not written by the project owner is an AI draft (Claude Opus 5.5, `translated_by: claude-opus-5-5`), written in this working session without a machine-translation system, and waits for native-speaker review (workbooks in [review/](review/); reviewers are available for Syrian Arabic and Italian).

**Wording.** Questions are written the way people actually ask: permits and offices use the community's usual term, without the German term in parentheses (Korean 블루카드, 안멜둥; English "do the Anmeldung"; Arabic البطاقة الزرقاء; Italian Carta Blu UE, fare l'Anmeldung). The German set uses everyday German ("jobben", "Visum wechseln"), not legal language.

**EU law outside the corpus.** Three questions (n06, n08, n12) depend on EU law that is not on gesetze-im-internet.de: the visa list (Regulation (EU) 2018/1806) and the Schengen 90/180-day rule. The expected answer covers the German part (AufenthG, AufenthV) and names the EU regulation to consult for the rest; prompts v3 and v4 ask for this.

Retrieval recall is measured on the 56 questions per set (336 in total) that have gold sections. A gold section given without an Absatz counts as found if any Absatz of that section is retrieved.

```bash
python -m evaluation.eval_retrieval --store numpy --modes dense bm25 hybrid
```

```bash
python -m evaluation.eval_retrieval --store chroma --modes dense bm25 hybrid
```

Per-question results are written to `results/retrieval_<store>_<mode>.jsonl`; the v1 results are kept in `results/v1/`.

### Current results (recall@8; evalset v2; fourteen-law corpus as of 2026-10-13)

| Mode | All | All without dialect | ko | en | de | ar | ar-SY | it |
|---|---|---|---|---|---|---|---|---|
| dense | 0.353 | **0.372** | 0.330 | 0.375 | 0.432 | 0.339 | 0.256 | 0.384 |
| bm25 | 0.029 | 0.035 | 0.000 | 0.018 | 0.122 | 0.000 | 0.000 | 0.036 |
| hybrid | 0.299 | 0.308 | 0.330 | 0.304 | 0.265 | 0.339 | 0.256 | 0.301 |

On `multi` questions (dense): ko 0.274, en 0.290, de 0.360, ar 0.226, ar-SY 0.204, it 0.306.

By the asker's nationality (dense, all six sets): no nationality given 0.418 (27 questions with gold sections), non-EU 0.344 (20), **EU 0.198** (8), both 0.000 (1). By topic: work 0.54, citizenship 0.42, tax 0.29, registration 0.28, study 0.27, residence 0.24, social 0.18, health 0.17, visa 0.13.

Numpy and Chroma give almost the same recall (dense 0.354 vs 0.353; identical top-8 lists for 307 of 336 questions). These numbers are not comparable with v1: the questions are different and harder (more `multi`, new topics).

**Findings and limitations**
- **Retrieval follows the topic, not the asker's legal status.** EU-citizen questions score 0.198. For the Portuguese employee posted to Germany (n36), dense retrieves the intra-company-transfer rules for non-EU staff (AufenthG § 19a, BeschV) and never FreizügG/EU § 2; for the French worker's American spouse (n60), it retrieves family reunification under AufenthG §§ 28 and 30, exactly the law that does *not* apply. The question says "Portuguese" or "French", but nothing in the embedding connects that to the Freedom of Movement Act. Scope has to come from the answer step and the `rewrite`/`agent` scope query (which gets all 8 EU questions right in the [answer evaluation](#current-results-evalset-v2-gpt-54-mini-prompt-v4-2026-10-13)), or a deterministic check for EU citizens (roadmap).
- **Naming a nationality does not hurt retrieval, and can help.** On the six questions that got a nationality during the balance pass, dense recall went from 0.417 to 0.454. "I'm Serbian" pulls in BeschV § 26 Abs. 2, the special rule for the Western Balkans, in four of six languages.
- **German questions help, but less than expected.** German is the best set for dense (0.432), 0.06 above English. Even "Ich ziehe nach Deutschland. Muss ich meinen Wohnsitz anmelden?" does not find BMG § 17 Abs. 1 ("Wer eine Wohnung bezieht, hat sich … anzumelden"). Most of the gap is everyday words against statutory phrasing, not language. BM25 works only on German (0.122), and hybrid still loses to dense there.
- **The new topics are the hard ones.** Work questions, mostly carried over from v1, score 0.54; visas, health and social insurance stay under 0.2. 17 of the 60 questions score 0 in all six languages, among them registration (n03, n38), the Blue Card waiting time (n15), Ausbildung (n16), student health insurance (n23), the vocabulary-gap tax questions from v1 (n45, n52, n57) and the EU and both questions above (n36, n37, n60). These are the targets for `rewrite` and `agent`.
- **Syrian dialect still costs the most.** 0.256 against 0.339 for the same questions in MSA (−24%); on v1 the drop was about 40%.
- **Adding KSVG changed nothing for the old questions.** The Korean and English items whose text and gold are unchanged since v1 give the same dense recall on both corpora. On the artists' question (n10), KSVG chunks reach the top 8 in every language, but KSVG § 1 (who is insured) only in Syrian dialect; § 1 has no title in the official XML.
- The gold sections were written by hand and checked against the statute text, but are not yet verified by a lawyer, and the translations are not yet reviewed.

### Experiment: a multilingual concept graph

The retrieval misses above are mostly vocabulary: people write "get my taxes back", "Anmeldung" or "I'm Portuguese", the statutes say *Veranlagung*, "Wer eine Wohnung bezieht …" and *Unionsbürger*. [concepts.py](gesetzpolyglot/concepts.py) is a small hand-written graph that bridges this: 40 concepts at first (Blue Card, registration, tax refund, health insurance, …; 59 now, see below), each with aliases in Korean, English, German, Arabic and Italian and the sections that answer it, plus four country groups taken from the statutes (EU/EEA/Switzerland, the states of AufenthV § 41 Abs. 1 and 2, the Western Balkans of BeschV § 26 Abs. 2). Some links are conditional: a spouse of an EU citizen brings in FreizügG/EU § 3, not the Residence Act's family reunification. [kg.py](gesetzpolyglot/kg.py) finds concepts and nationalities in the question (a country named as a destination, "travel to the Netherlands", or next to a relative, "my American spouse", is not taken as the asker's nationality) and fuses their sections with the normal ranking via RRF; a question without a known concept keeps its ranking.

```bash
python -m gesetzpolyglot.kg "저는 포르투갈 사람인데 독일 지사로 파견되면 어떤 체류허가가 필요한가요?"
```

```bash
python -m evaluation.eval_retrieval --modes dense dense+kg --evalset evalset/heldout/ko.jsonl
```

| Questions | dense | dense + graph | hybrid + graph |
|---|---|---|---|
| evalset v2 (336) | 0.353 | 0.818 | 0.816 |
| **held-out questions (37, Korean)** | 0.198 | **0.302** | **0.315** |

**The evalset number is not a real estimate.** The graph was written by someone who knew the evaluation questions and their gold sections, and 101 of the 104 gold sections ended up in it: on evalset v2 it mostly looks up the answers it was given. To measure it honestly, the project owner wrote 40 new questions without seeing the graph ([evalset/heldout/ko.jsonl](evalset/heldout/ko.jsonl); 33 of them from situations suggested by Claude, worded by the owner), the gold sections were fixed from the statute text before running the graph, and the graph was not changed after seeing the results (except an Arabic alias for Austria that never matched, which changes none of the held-out numbers).

- **On new questions the graph helps a little: +0.07 (dense) to +0.12 (hybrid).** When a concept matches, it works: "a month in Germany without a visa" (0 → 1.00), "is a German degree better for permanent residence" (0 → 0.50).
- **Coverage is the limit.** In the first 20, 12 questions matched no concept at all ("moving to another city", "months spent abroad", "PhD", "internship", "home-office deduction"), because people phrase things in more ways than hand-written aliases cover. One question got worse (a spouse joining a permanent resident: 1.00 → 0.50), because the graph's sections pushed out one that dense search had found.
- **Three fixes found by reading one evalset question.** For the French worker's American spouse (n60) the graph used to take "American" for the asker's nationality, put the most specific section (FreizügG/EU § 3, family members of EU citizens) last, and keep AufenthG § 30 (family reunification for non-EU citizens) at the top, a law that does not apply. Now a country next to a relative does not count, the most specific sections come first, and a concept can name sections that no longer apply once a nationality group is known (`instead_of`): they are removed from the ranking. On evalset v2 this moved 0.792 to 0.818 (19 questions better, one worse: the Korean Blue-Card-without-degree question n27 lost BeschV § 26, now ranked after the concepts' sections); on the held-out questions nothing changed, because none of them names a relative's nationality. As the fixes came from an evalset question, only the held-out number counts.
- **Nationality roles, and the held-out questions become dev data (2026-10-17).** The 40 held-out questions showed that a country name can mean three things: the asker's nationality, a family member's ("my spouse is Spanish", which brings EU family law along), or just a place ("worked in France", "a Swiss company", "work in the Netherlands"). The graph now tells these apart: a family member's EU citizenship counts for family law but a family member's privileged nationality gives the asker nothing, and places count for nobody. 19 concepts that the held-out questions missed were added (parents joining, married to a German, dual citizenship, asylum seekers working, Duldung, a pending extension, long absences, unemployment benefit and permanent residence, PhD, internships, the landlord's confirmation, name changes, remote work, business trips, athletes, Schengen travel, tax deductions, home office, side jobs, shares), for 59 concepts in all. On the held-out questions dense recall with the graph went from 0.302 to 0.775, and nothing changed on evalset v2 (0.818, no question better or worse). **0.775 is not an estimate**: the graph was fitted to these questions, which are dev data from now on; the clean numbers for them are the ones above (0.302 retrieval only, and the LLM run). A new set of questions, kept away from the graph, is needed to measure this version.
- **The new questions are harder than evalset v2** (Korean dense 0.233 against 0.330), so the held-out set is also a useful check of the evaluation set itself.
- **Indexing the titles of referenced sections did not help.** Adding the titles of the sections a chunk cites ("§ 25 Absatz 2" → "Aufenthalt aus humanitären Gründen", 4,418 chunks) changed evalset v2 from 0.353 to 0.357 (10 questions better, 9 worse) and on v1 lowered the refugee questions it was meant for (0.400 → 0.350). It stays an option (`retrieval.py build --ref-titles`), not the default.

Next: let the LLM pick concepts in `rewrite` and the agent's plan instead of matching aliases, and measure it on the held-out questions before changing the graph again.

#### With the LLM: does the graph still help?

The numbers above are retrieval only. To see whether the graph still matters once an LLM writes the search queries and the answer, all four conditions were run with and without it on the 40 held-out questions (gpt-5.4-mini, prompt v4, 320 answers, about $2.00, 2026-10-15; [results/experiments/kg-llm-heldout40](results/experiments/kg-llm-heldout40/report.md), graph as before the held-out questions were seen):

| Condition | Status matches, without → with graph | recall@8, without → with graph | Graph effect on recall | LLM calls | s / question |
|---|---|---|---|---|---|
| dense | 28 → 31 / 40 | 0.198 → 0.302 | **+0.104, p = 0.03** | 1 | 3.6–3.9 |
| hybrid | 32 → 28 / 40 | 0.185 → 0.315 | **+0.131, p = 0.005** | 1 | 3.4–3.5 |
| rewrite | 37 → 38 / 40 | 0.423 → 0.450 | +0.027, p = 0.61 | 2 | 5.3–5.5 |
| agent | 37 → **38** / 40 | 0.428 → **0.509** | +0.081, p = 0.24 | 4.6 | 11.3–11.5 |

- **When the LLM writes the queries, it already does most of what the graph does.** `rewrite` alone (0.423) beats `dense` with the graph (0.302): turning "get my taxes back" into German legal terms is much of what the graph's aliases do. The best overall is the agent with the graph (38/40, 0.554 of the gold sections in its whole context), but its lead over the agent without the graph is not significant.
- **Better retrieval did not significantly change the answer status** in any condition (all p > 0.2).
- **The graph did not cause invalid citations.** There were 0 to 2 per 40 answers in every variant, all to sections the model named from general knowledge, none to sections the graph had added; the graph also costs no extra tokens.
- **Single runs are noisy.** GPT-5-family models reject `temperature`, so answers vary between runs. On the 18 questions where the graph matched nothing, retrieval was identical with and without it, yet the status still changed for 4 (dense) and 3 (hybrid) of them. Status differences of a few questions, such as hybrid's 32 → 28, are within that noise. Repeated runs would separate the two; they were not done to save cost.
- The graph's known weaknesses showed up here too: "네덜란드에서" (in the Netherlands) taken for EU nationality (h39), and a British asker who lost his job given the visa-free entry rule instead (h36).

#### Comparing runs with and without the graph

Every condition can run with or without the concept graph, and nothing else changes between the two: `RAG(..., graph=ConceptGraph())` fuses the graph's sections into `dense`, `hybrid` and `rewrite` and seeds the agent's pool with them; without `graph` retrieval is exactly as before. The switch is `--kg` in `gesetzpolyglot.rag` and `app.py`, `--kg off|on|both` in `eval_answers`, and the modes `dense+kg` / `hybrid+kg` in `eval_retrieval`. Each result row records `kg`, the graph version (`kg_version`, a hash of concepts.py) and which concepts matched.

One command runs a whole comparison and writes a folder a paper table can be built from:

```bash
python -m evaluation.ablation --name kg-2026-10-14
```

```bash
python -m evaluation.ablation --name kg-2026-10-14-llm --answers validation heldout --yes
```

The first run is retrieval only and free; the second adds the LLM runs (all four conditions, each with and without the graph; it prints the cost, about $2.40 with gpt-5.4-mini, and only starts with `--yes`). `results/experiments/<name>/` then holds:
- `manifest.json`: command, git commit and whether the tree had uncommitted changes, prompt version, model, index (embedding model, chunk count, statute snapshots), concept graph version, hashes of the question files, package versions
- the per-question results of every variant
- `report.md`: recall per language set, how many gold sections the graph links to at all (a share near 100% means the questions shaped the graph, so the result is an upper bound), and paired differences

[compare.py](evaluation/compare.py) does the paired statistics and can also be used on its own, for any two result files:

```bash
python -m evaluation.compare results/experiments/kg-2026-10-14/retrieval_heldout_dense.jsonl results/experiments/kg-2026-10-14/retrieval_heldout_dense+kg.jsonl
```

It pairs questions by (set, id) and reports, per metric, the difference with a 95% paired bootstrap interval, how many questions got better or worse, and a p-value (exact McNemar for yes/no metrics such as the answer status, a sign-flip permutation test otherwise), with fixed seeds so the numbers are reproducible. On the first 20 held-out questions the gain was not significant (dense +0.067, p = 0.5; hybrid +0.117, p = 0.12). With 37 it is: dense +0.104 (95% interval +0.02 to +0.20, p = 0.03), hybrid +0.131 (+0.05 to +0.22, p = 0.005), 9 questions better and none worse with hybrid. The share of questions with every gold section found does not change significantly yet (p = 0.25). For a reportable run, commit first so the manifest shows a clean tree, and never use held-out questions to build the graph.

### Evaluation set v1 (archived)

The first evaluation set (until 2026-10-12, now in [evalset/archive/v1/](evalset/archive/v1/)) tied the asker to the language: Arabic asked as a Syrian (or Egyptian) citizen, Italian as an Italian, English and Korean as a Korean. It had 62 questions in three modules (core residence and work, refugee and protection, tax and pension) and an Egyptian-dialect set; a former set was replaced on 2026-10-12 and a Turkish set was dropped for lack of a reviewer. Because the nationality changed with the language, differences between sets mixed language and legal status, which is why v2 writes the nationality into the question. The refugee module was dropped; the core and tax questions moved into v2.

Dense recall@8 on v1 (thirteen-law corpus, without KSVG):

| Module | Questions | All | ko | en | ar | ar-SY | ar-EG | it-IT |
|---|---|---|---|---|---|---|---|---|
| core | 30 | 0.468 | 0.513 | 0.571 | 0.532 | 0.397 | 0.301 | 0.494 |
| refugee | 17 | 0.400 | 0.400 | 0.467 | 0.400 | 0.233 | 0.300 | 0.600 |
| tax | 15 | 0.297 | 0.449 | 0.321 | 0.256 | 0.090 | 0.192 | 0.474 |

What v1 showed:
- **German terms in the question help.** An early draft wrote "vocational training (Ausbildung)". Removing the German terms in parentheses lowered dense recall from 0.593 to 0.567 and BM25 from 0.085 to 0.019. Real users rarely add them, so both versions are written without.
- **More laws barely hurt, unless they are close to the topic.** Adding AsylG (+37% chunks) left dense recall unchanged, and EStG, AO, SGB IV and SGB VI (×4.2) moved it from 0.567 to 0.564. AufenthV, FreizügG/EU, StAG, BMG, SGB V and VVG (×1.7) lowered the core set from 0.484 to 0.468 and tax from 0.323 to 0.297, mostly because AufenthV, the ordinance under AufenthG, competes on the same topics.
- **Scope is not retrieved.** For the Italian EU-citizen questions retrieval found the topic but never AufenthG § 1 Abs. 2, the section that says the Residence Act does not apply. v2 shows the same pattern for FreizügG/EU.
- **BM25 needs German.** It returned nothing for Korean and Arabic, and on English and Italian it added noise: English hybrid fell from 0.571 to 0.378.
- **Dialect, not nationality, cost recall.** The same questions gave 0.454 in MSA, 0.278 in Syrian and 0.275 in Egyptian dialect; Syrian and Egyptian askers scored the same in MSA.
- **The statutes rarely use the user's words.** Refugee questions missed AufenthG § 26 Abs. 3, which says "a residence permit under § 25 Absatz 1 or 2" rather than "refugee"; tax questions missed *Einspruch* (AO § 347), *Veranlagung* (EStG § 46) and *gewöhnlicher Aufenthalt* (AO § 9).
- **Index details matter.** EStG sections without a title in the XML now get the nearest outline heading (tax module 0.357 → 0.382). Very long chunks (EStG § 3 is 54,000 characters) are only partly seen by the embedding model, which reads about 1,024 tokens.

#### Experiment: translating the question before retrieval

Measured on v1. [query_translate.py](evaluation/query_translate.py) translates each question with Meta's NLLB-200 (`nllb-200-distilled-600M`, local, no API), which has its own codes for North Levantine (`apc_Arab`) and Egyptian Arabic (`arz_Arab`). [eval_retrieval.py](evaluation/eval_retrieval.py) then searches the translation (`--translate deu_Latn`) or both and fuses the rankings with RRF (`--fuse`).

```bash
python -m evaluation.eval_retrieval --modes dense --translate deu_Latn --fuse
```

| Set | Original | Translated to German | Original + German, fused |
|---|---|---|---|
| ko | 0.475 | 0.398 | 0.485 |
| en | 0.506 | 0.534 | 0.540 |
| ar (MSA) | 0.454 | 0.466 | 0.472 |
| ar-SY (dialect) | 0.278 | 0.407 | **0.432** |
| ar-EG (dialect) | 0.275 | 0.358 | **0.398** |
| it-IT | 0.543 | 0.426 | 0.509 |
| **All** | 0.422 | 0.432 | **0.473** |

Fusion closes half to three quarters of the dialect gap without hurting the other languages much; translating alone hurts Korean and Italian, because the translation loses details (دائرة الأجانب, Ausländerbehörde, became "Auslandsministerium"). **The NLLB-200 weights are CC-BY-NC 4.0 (non-commercial)**, so this is an experiment only and not part of the app; LLM `rewrite` is the commercial alternative. It has not been re-run on v2 yet.

### Answer evaluation with the LLM

[eval_answers.py](evaluation/eval_answers.py) runs the whole pipeline, LLM included, on chosen items. For each condition it records the recall@8 of what the answer step receives, whether the answer's status matches `expected_behavior`, citations that are not in the retrieved text, LLM calls, latency and tokens. This costs money, so it runs on small named splits from [evalset/splits.json](evalset/splits.json):

- `validation`: 30 of the 60 v2 questions, half of each type, each asked in one of the six sets (5 per set). One run (120 answers) costs about $0.70 with gpt-5.4-mini.
- `smoke`: 6 other questions, one per set, to check that a run works end to end.

```bash
python -m evaluation.eval_answers --split validation
```

```bash
python -m evaluation.eval_answers --split smoke --prompts v3 --model gpt-5.4
```

Without `--model` and `--prompts` it uses the defaults: gpt-5.4-mini and prompt v4.

#### Current results (evalset v2, gpt-5.4-mini, prompt v4, 2026-10-13)

| Condition | recall@8 | recall of all context | Status matches | Invalid citations | LLM calls | s / question |
|---|---|---|---|---|---|---|
| dense | 0.345 | 0.345 | 25/30 | 0 | 30 | 5.6 |
| hybrid | 0.280 | 0.280 | 22/30 | 0 | 30 | 3.7 |
| rewrite | **0.452** | 0.452 | **28/30** | 0 | 60 | 6.4 |
| agent | 0.435 | **0.613** | **28/30** | 0 | 137 | 13.5 |

With `rewrite` and the agent together, every set gets 9 or 10 of its 10 answers right (Korean, German, Arabic and Italian 10/10, Syrian dialect 9/10), except English with 7/10; the English misses are two questions whose content is hard (n10, n56), not the language. EU-citizen questions get 8/8, although single-pass retrieval finds their gold sections only rarely (0.198 recall, see above): the scope query in `rewrite` and the agent's plan brings in the Freedom of Movement Act.

**Findings**
- **When the system is wrong, it refuses rather than invents.** 16 of the 17 mismatches are `refuse_out_of_scope` where retrieval had found nothing relevant, e.g. registration (n03) or the Portuguese employee (n36) with `dense`/`hybrid`. No mismatch is a confident answer to a question that should have been refused. This is the status only: the content of the answers has been read in samples, not checked by a lawyer.
- **`rewrite` and the agent clearly beat single-pass retrieval** (28/30 against 22–25/30). They search in German and add the EU scope query, so registration, the posted Portuguese employee, the French worker's spouse (n60) and Ausbildung asked in Syrian dialect (n16) pass with them and fail with `dense`/`hybrid`. The agent hands 12 chunks to the answer step and covers 0.613 of the gold sections, but takes about twice as long as `rewrite`.
- **Asking both cases works where it matters.** Without a stated nationality, the answer splits into EU and non-EU only where the law differs, e.g. freelancing (n43): "If you are an EU/EEA citizen … If you are not … If you tell me your nationality, I can answer more precisely." Tax and citizenship questions are not split, and answers without a nationality are not longer than the others (about 600 characters against 760).
- **One status is debatable.** For "Exactly how much tax will I pay on 50,000 euros?" (n56) the model computed about €10,550 from the tariff formula in EStG § 32a, with caveats, instead of only explaining the rules. The figure is for taxable income, not salary, so the expected `explain_without_judgment` stays.

#### Prompt versions

All four live in [prompts.py](gesetzpolyglot/prompts.py); `PROMPT_VERSION` (or `--prompts`) picks one. Each version is kept unchanged, so earlier runs can be repeated; a change becomes a new version.

| Version | What it changed | Measured on |
|---|---|---|
| v1 | first version | evalset v1 |
| v2 | check scope first (EU/EEA citizens: AufenthG § 1 Abs. 2, plus a scope query in `rewrite` and the agent's plan); `explain_without_judgment` only when asked to predict the user's own case; answer the covered part instead of refusing; read each provision's Absatz, Satz and named group exactly; say when the user's country is not in a list; correct wrong assumptions | evalset v1 (below) |
| v3 | answer EU/EEA citizens from the Freedom of Movement Act (now in the corpus) instead of refusing; for EU law outside the corpus (visa list, Schengen short stays, asylum regulations) answer the German part and name the regulation to consult; never guess the nationality from the language: if it is not stated and matters, answer both cases and ask for it | evalset v2 |
| **v4** (default) | label the excerpts as search results the user has not seen; no offers of further help (only the nationality may be asked); AufenthG § 1 Abs. 2 no longer written as a citation inside the rules | evalset v2 |

v3 against v4 on the same 120 answers:

| Prompts | Status matches | Invalid citations | Answers offering more help ¹ | Asking the user for excerpts ² |
|---|---|---|---|---|
| v3 | 101/120 | 16 | 58 | 22 |
| v4 | **103/120** | **0** | **3** | **3** |

¹ "If you want, I can …" and its equivalents in the other languages. ² Counted with a phrase list, so approximate; the three v4 hits only call the excerpts "the given provisions" and no longer ask the user to send anything.

- **v3 talked as if the user had supplied the excerpts.** 58 of 120 answers ended with an offer, and some asked the user to "send the FreizügG/EU excerpts", although the user never sees them: the excerpts arrived in the user message without saying where they came from. v4 says so, forbids offers and points to the competent authority instead.
- **v3's invalid citations were all one leak.** All 16 were AufenthG § 1 Abs. 2, which the scope rule spelled out in citation form; the model copied it even when it was not retrieved. Written in words in v4, it disappeared.
- **The status matches are the same within noise.** Two answers changed from `answer` to `refuse_out_of_scope` where retrieval had found nothing relevant (n10 `rewrite`, n14 agent): v3 had answered from loosely related excerpts, v4 said the rule was not among the statutes found.
- A status line that does not name exactly one status is scored as `unclear` (wrong) in every version.

#### Earlier runs on evalset v1: choosing the model

These runs chose the model and wrote prompt v2. They used evalset v1 with its `dev` split (10 hard items used to write v2) and `validation` split (20 random items), on the three-law corpus; the splits are kept in [evalset/archive/v1/splits.json](evalset/archive/v1/splits.json).

**Validation, v1** (20 items × 4 conditions = 80 answers per run):

| Model | Prompts | Status matches | `unclear` | recall@8 rewrite | recall@8 agent | Cost |
|---|---|---|---|---|---|---|
| gpt-5.4-nano | v1 | 58/80 | 3 | 0.559 | 0.529 | $0.12 |
| gpt-5.4-nano | v2 | 71/80 | 6 | 0.500 | 0.676 | $0.12 |
| gpt-5.4-mini | v2 | **79/80** | 0 | 0.471 | 0.765 | $0.42 |
| gpt-5.4 | v1 | 60/80 | 0 | 0.588 | 0.676 | $1.35 |
| gpt-5.4 | v2 | **79/80** | 0 | 0.647 | 0.647 | $1.51 |
| llama3 8B, local (Ollama) ¹ | v2 | 37/80 | 33 | 0.235 | 0.265 | $0 |

¹ Run later, on the seven-law corpus with the Arabic items in the MSA set; the API rows were measured on the three-law corpus.

Without the LLM, the same 20 items give dense 0.765 and hybrid 0.588.

**Dev, v1** (10 hard items; status matches and recall@8 for `rewrite` / `agent`):

| Model | Prompts | Status matches | recall@8 |
|---|---|---|---|
| gpt-5.4-nano | v1 | 4 / 5 | 0.45 / 0.65 |
| gpt-5.4 | v1 | 8 / 8 | 0.50 / 0.40 |
| gpt-5.4-nano | v2 | 8 / 6 | 0.60 / 0.55 |
| gpt-5.4-mini | v2 | 9 / 10 | 0.65 / 0.50 |
| gpt-5.4 | v2 | 10 / 10 | 0.60 / 0.65 |

Costs are API token counts times list prices (gpt-5.4: $2.50 / $15 per 1M input / output tokens; gpt-5.4-mini: $0.75 / $4.50 and gpt-5.4-nano: $0.20 / $1.25, as listed by third-party trackers). All LLM experiments so far cost about $8.80. Average time per question with the agent on the validation set: nano 14 s, mini 10 s, gpt-5.4 24 s.

**Findings on v1**
- **A local 8B model is not good enough yet.** llama3 8B on a 16 GB M2 got 37/80. 33 answers had no valid status line, it answered 5 out-of-scope questions instead of refusing, and its rewritten queries cite made-up sections ("§ 25 Abs. 3 EStG"), so `rewrite` and `agent` retrieved far less (0.24–0.27) than searching the question directly (0.765). Some answers were plainly wrong, e.g. "you are not required to notify the immigration office" when AufenthG § 82 Abs. 6 requires it within two weeks. It also took about 90 seconds per agent question. Newer 8B models (e.g. qwen3:8b) may do better and can be tested the same way with `--provider ollama --model …`.
- **gpt-5.4-mini matches gpt-5.4 at about a quarter of the cost.** With v2 it got 79/80 on validation (same as gpt-5.4), made no format errors, and was the fastest. On the dev items it gave correct answers where nano failed: it cited § 1 Abs. 2 for the Italian EU-citizen question, separated § 26 Abs. 3 (refugees) from Abs. 4 (subsidiary protection), and corrected the Blue Card premise. It is now the default model.
- **v2's own examples can leak into citations.** Once, mini cited AufenthG § 1 Abs. 2 although it was not retrieved; the prompt mentions it in the scope rule. The citation check flags this (`invalid`). On evalset v2 this happened 16 times with v3, which led to v4.
- **v2 holds up on unseen items.** Status matches rose from 58 to 71 (nano) and from 60 to 79 (gpt-5.4). The main v1 error, answering a plain question about the rules with "I can't judge your case", almost disappears.
- **Most remaining nano errors are format errors.** 6 of nano's 9 misses with v2 are a copied template line ("STATUS: answer | refuse_out_of_scope"). gpt-5.4 and gpt-5.4-mini never did this.
- **A matching status is not a correct answer.** On the dev set, gpt-5.4 with v1 described subsidiary protection with the numbering from before the 2024 reform (§ 25 Abs. 2 Satz 1, "second alternative"), contradicting the excerpt in front of it. A stronger model can fall back on outdated training knowledge, so answers still have to be read.
- **`rewrite` helps on hard questions and hurts on easy ones.** On the dev items dense found nothing and `rewrite` reached 0.45–0.60. On the random validation items dense is better (0.765 vs 0.50–0.65): `rewrite` searches only the LLM's German queries and drops the original question, and the queries sometimes drift (q09: § 82 Abs. 1 instead of Abs. 6). Searching the original question together with the rewritten queries should keep both gains.
- **Some misses are gold sections that are too narrow.** For r08, gpt-5.4 answered correctly from AufenthG § 12a Abs. 2–4, but the gold names only Abs. 1.

## Adding a law

All statute names come from [laws.py](gesetzpolyglot/laws.py). To add one:

1. Add it to `LAWS` (abbreviation → gesetze-im-internet.de slug) and to `CORPUS`; update `TOPIC` and `OUT_OF_SCOPE` if the subject area changes.
2. Fetch, parse and rebuild the index:

```bash
python -m gesetzpolyglot.gii_parser fetch
```

```bash
python -m gesetzpolyglot.gii_parser parse
```

```bash
python -m gesetzpolyglot.retrieval build --store chroma
```

3. Re-run the evaluation and compare with the previous corpus.

AsylG was the first law added this way; EStG, AO, SGB IV and SGB VI followed. They needed three parser changes: the Social Code cites its own books by ordinal ("§ 28e des Vierten Buches" = SGB IV) and its own book as "dieses Buches"; chains like "§§ 286 ff." and "Buchstabe a oder b der Abgabenordnung" used to stop before the law name; and law abbreviations may contain a space ("SGB VI"). The same fixes also corrected a few old AufenthG cross-references (e.g. § 87 Abs. 2 pointed to AufenthG §§ 7 and 23 instead of SGB II and SGB XII). AufenthV, FreizügG/EU, StAG, BMG, SGB V and VVG followed on 2026-10-12, and KSVG (artists' social insurance) on 2026-10-13; for them the parser learned to keep a slash out of folder names (`FreizügG/EU` is stored under `data/raw/FreizügG_EU/`) and to survive a missing space in the official text ("§ 50 Absatz 4den" in BMG § 3). StAG has neither section titles nor an outline in the XML, so its chunks are indexed by text only. AsylG's text is the version after the 2024 EU asylum reform (in force since June 2026): 86 of its 374 chunks refer to EU Regulations 2024/1347, 2024/1348 or 2024/1351, which are not on gesetze-im-internet.de and not in the corpus. The answer prompt tells the model to say so instead of filling in the details.

## Roadmap

**Evaluation**
- a full answer evaluation over all 360 v2 questions (60 × six sets) with gpt-5.4-mini and prompt v4: about $8.30, extrapolated from the validation runs ($0.69 per 120 answers)
- have a lawyer read a sample of the answers: a matching status is not a correct answer
- have native speakers review the German, Arabic, Syrian and Italian questions of evalset v2 (workbooks ready in [review/](review/)), and verify the gold sections (some are too narrow, see the v1 findings)
- run `rewrite` and the agent on the dialect set against the NLLB translation [experiment](#experiment-translating-the-question-before-retrieval)

**Retrieval**
- a deterministic scope check for EU citizens, so AufenthG § 1 Abs. 2 and FreizügG/EU § 2 are retrieved without relying on the LLM's queries (EU askers score 0.198 recall with single-pass retrieval)
- `rewrite`: search the original question together with the rewritten queries, so easy questions do not lose what dense search finds
- concept graph: let the LLM pick concepts in `rewrite` and the agent's plan instead of matching aliases, then grow the graph, measuring each step on new held-out questions ([experiment](#experiment-a-multilingual-concept-graph))
- collect more held-out questions from people who have not seen the graph, in every question language
- repeat each LLM run (e.g. three times) to separate the graph's effect from run-to-run variation (about three times the cost)
- split very long chunks (EStG § 3 is 54,000 characters) by item, so dense search sees all of them
- a commercially usable translation model, if translating before retrieval goes into the app

**Corpus**
- VAT for freelancers (UStG § 19, small businesses), and double taxation treaties, which are published outside gesetze-im-internet.de
- the broadcasting fee (Rundfunkbeitrag): a treaty between the federal states, not a federal law, so not on gesetze-im-internet.de; it would need its own source and parser. It applies per dwelling, regardless of nationality
- the EU regulations the statutes point to (visa list 2018/1806, Schengen rules, asylum regulations 2024/1347, 2024/1348, 2024/1351) from EUR-Lex, which needs its own parser
- AufenthV's official zip is 19.5 MB because it contains form images; consider keeping only the XML in git

**App**
- more question languages (Turkish was removed until a reviewer is found); unsupported languages currently get a short note to rephrase
- a setting to switch the main UI language (e.g. Korean, Arabic, Italian); the German gloss stays on by default
- a format fix for small models that copy the status template, if gpt-5.4-nano is used to save cost

## Tests

```bash
python -m pytest -q
```

Tests use a fake embedder, so they run without the bge-m3 model or an API key. `tests/test_evalset.py` checks that the six evalset files hold the same questions (ids, gold sections, expected behavior, persona).

## Not in git

`data/index/` (embeddings and Chroma), `results/`, `.env` and `.venv/` are git-ignored, except the summary of each experiment (`results/experiments/<name>/report.md` and `manifest.json`), which is kept so reported numbers can be traced to a run. To reproduce, run steps 1–2 above, then `evaluation.eval_retrieval` and `evaluation.eval_answers`; the item lists for the LLM runs are in [evalset/splits.json](evalset/splits.json).

A Korean version of this README is in [README.ko.md](README.ko.md).
