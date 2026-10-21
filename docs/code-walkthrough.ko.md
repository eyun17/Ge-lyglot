# 코드 따라 읽기: GesetzPolyglot을 처음부터

이 문서는 코드를 **데이터가 흐르는 순서대로** 설명합니다. 법령 XML을 받는 데서 시작해서, 조각으로 나누고, 검색하고, LLM이 답하고, 그 답을 검증하고, 마지막으로 얼마나 잘했는지 재는 데까지 갑니다. 장마다 "직접 해 보기" 명령이 있으니 터미널에서 따라 돌려 보세요. 모두 프로젝트 폴더(`/Users/eyun/Gelyglot`)에서 실행하고, 비용이 드는 명령에는 따로 표시했습니다.

```bash
cd /Users/eyun/Gelyglot
```

## 차례

0. [먼저 알아 둘 말](#0-먼저-알아-둘-말)
1. [만들어진 순서](#1-만들어진-순서)
2. [laws.py: 법령 목록](#2-lawspy-법령-목록)
3. [gii_parser.py: XML을 조각으로](#3-gii_parserpy-xml을-조각으로)
4. [retrieval.py: 검색 엔진](#4-retrievalpy-검색-엔진)
5. [llm.py: LLM 연결](#5-llmpy-llm-연결)
6. [prompts.py: 프롬프트와 버전](#6-promptspy-프롬프트와-버전)
7. [rag.py: 검색 → 답변 → 검증](#7-ragpy-검색--답변--검증)
8. [agent.py: LangGraph 에이전트](#8-agentpy-langgraph-에이전트)
9. [kg.py, concepts.py: 개념 그래프](#9-kgpy-conceptspy-개념-그래프)
10. [app.py: 웹 화면](#10-apppy-웹-화면)
11. [evaluation/: 얼마나 잘하나 재기](#11-evaluation-얼마나-잘하나-재기)
12. [tests/: 테스트](#12-tests-테스트)
13. [혼자 해 보기](#13-혼자-해-보기)

---

## 0. 먼저 알아 둘 말

| 말 | 뜻 |
|---|---|
| **청크(chunk)** | 검색 단위로 자른 텍스트 조각. 여기서는 법 조항의 항(Absatz) 하나 |
| **임베딩(embedding)** | 문장을 숫자 1,024개짜리 목록(벡터)으로 바꾼 것. 뜻이 비슷한 문장은 비슷한 벡터가 됨 |
| **코사인 유사도** | 두 벡터의 방향이 얼마나 같은지(1에 가까울수록 비슷함). 검색은 질문 벡터와 가장 비슷한 청크 벡터를 찾는 일 |
| **BM25** | 단어가 겹치는 정도로 매기는 고전적인 키워드 검색 점수 |
| **RRF** | 여러 검색 결과 순위를 하나로 합치는 방법. 점수 대신 순위만 씀 |
| **RAG** | 먼저 검색하고, 찾은 텍스트만 LLM에게 줘서 답하게 하는 방식 |
| **프롬프트** | LLM에게 주는 지시문 |
| **recall@8** | 정답 조항 중 상위 8개 검색 결과에 들어온 비율 |
| **trace** | 질문 하나를 처리하면서 거친 단계의 기록 |

---

## 1. 만들어진 순서

코드는 처음부터 지금 모습이 아니었습니다. 이 순서를 알면 "왜 이렇게 생겼는지"가 이해됩니다.

1. **법 3개로 시작:** 체류법(AufenthG), 고용령(BeschV), 망명법(AsylG)을 받아 조각내는 파서를 만들었습니다.
2. **검색:** 조각들을 bge-m3로 임베딩하고 dense, BM25, hybrid 검색을 만들었습니다.
3. **RAG:** 검색 결과로 LLM이 답하고, 인용을 검증하는 파이프라인을 만들었습니다.
4. **에이전트:** 질문을 나누고 참조를 따라가는 LangGraph 에이전트를 만들었습니다.
5. **평가:** 평가 질문과 정답 조항을 만들고 recall을 쟀습니다.
6. **법 늘리기:** 세금·연금·건강보험 등을 더해 14개 법이 됐습니다. 이때 파서 버그를 많이 고쳤습니다.
7. **평가셋 v2:** 국적을 언어와 떼어 질문 안에 넣었습니다.
8. **프롬프트 v2 → v3 → v4:** 평가에서 문제를 찾을 때마다 새 버전을 만들었습니다.
9. **폴더 정리:** `gesetzpolyglot/`, `evaluation/`, `tests/`로 나눴습니다.
10. **개념 그래프(KG)와 비교 실험 도구**를 만들었습니다.
11. **앱:** 사용자 API 키 방식으로 바꾸고 Hugging Face Space에 올렸습니다.

```
gesetzpolyglot/   시스템 본체       ← 2–9장
app.py            웹 화면           ← 10장
evaluation/       평가 도구         ← 11장
tests/            테스트            ← 12장
evalset/          평가 질문 (데이터)
data/             원본 XML, 조각, 인덱스 (데이터)
```

---

## 2. laws.py: 법령 목록

가장 단순한 파일이고, 다른 모든 파일이 이 파일을 봅니다.

```python
LAWS = {
    "AufenthG": "aufenthg_2004",   # 약칭 → gesetze-im-internet.de 주소의 일부
    "BeschV": "beschv_2013",
    ...
}
CORPUS = ["AufenthG", "AufenthV", "BeschV", ...]   # 실제로 검색하는 14개
TITLES = {"AufenthG": ("Aufenthaltsgesetz", "Residence Act"), ...}   # 앱의 출처 표에 쓰는 정식 이름
TOPIC = "residence, EU free movement, employment, ..."              # 프롬프트와 앱에 들어가는 분야 설명
OUT_OF_SCOPE = "unemployment and long-term care insurance, VAT, ..."  # 안 다루는 분야
```

**왜 따로 두나:** 법 목록이 파서, 검색, 프롬프트, 앱에 흩어져 있으면 법 하나를 추가할 때 여러 곳을 고쳐야 하고 빠뜨리기 쉽습니다. 한 곳에 모아 두면 여기만 고치면 됩니다. 이런 원칙을 "단일 진실 공급원(single source of truth)"이라고 부릅니다.

`assert set(TITLES) == set(LAWS)`처럼, 법을 추가하면서 정식 이름을 빠뜨리면 바로 오류가 나게 해 두었습니다.

---

## 3. gii_parser.py: XML을 조각으로

### 3-1. 받기: `fetch()`

웹페이지를 긁는(스크래핑) 대신, gesetze-im-internet.de가 법마다 공식으로 제공하는 XML 압축 파일을 받습니다.

```python
url = f"{BASE}/{LAWS[law]}/xml.zip"            # 예: .../aufenthg_2004/xml.zip
data = urllib.request.urlopen(req, timeout=60).read()
snap = raw_dir(law, root) / now.strftime("%Y-%m-%d")   # data/raw/AufenthG/2026-10-08/
(snap / "xml.zip").write_bytes(data)
manifest = {"law": law, "url": url, "fetched_at": ..., "sha256": hashlib.sha256(data).hexdigest()}
```

- **날짜별 폴더(스냅샷):** 같은 날 다시 받으면 건너뛰고, 예전 날짜 것은 지우지 않습니다. 법이 개정돼도 "그 실험은 어느 날짜의 법으로 했는지"를 알 수 있습니다.
- **sha256:** 파일 내용의 지문입니다. 내용이 한 글자라도 바뀌면 값이 달라지니, 같은 파일인지 확인할 수 있습니다.

### 3-2. XML 구조

법 XML은 대략 이렇게 생겼습니다(단순화).

```xml
<norm>   <!-- 목차 제목 -->
  <metadaten><gliederungseinheit>
    <gliederungsbez>Kapitel 2</gliederungsbez><gliederungstitel>Einreise und Aufenthalt</gliederungstitel>
  </gliederungseinheit></metadaten>
</norm>
<norm>   <!-- 조항 하나 -->
  <metadaten><enbez>§ 16b</enbez><titel>Studium</titel></metadaten>
  <textdaten><text><Content>
    <P>(1) Einem Ausländer wird zum Zweck des Vollzeitstudiums ...</P>
    <P>(3) Die Aufenthaltserlaubnis berechtigt ... 140 Arbeitstage ...</P>
  </Content></text></textdaten>
</norm>
```

`<norm>` 하나가 목차 제목이거나 조항(§) 하나입니다. 조항 안의 `<P>` 하나가 대개 항(Absatz) 하나입니다.

### 3-3. 조각내기: `parse_law()`

```python
for norm in norms:
    gl = meta.find("gliederungseinheit")
    if gl is not None:                       # ① 목차 제목이면: 현재 위치(path)만 갱신하고 넘어감
        path = path[: depth - 1] + [label]
        continue
    enbez = meta.findtext("enbez")           # ② "§ 16b" 같은 조항 번호
    if not enbez.startswith("§"):
        continue                             #    목차표, 부록 등은 건너뜀
    for child in content:                    # ③ 문단마다
        txt = clean(render(child))
        ma = ABS_RE.match(txt)               #    "(3) ..."로 시작하면 새 항
        if ma:
            absaetze.append([ma.group(1), txt[ma.end():]])
        elif absaetze:
            absaetze[-1][1] += "\n" + txt    #    아니면 앞 항에 이어 붙임 (목록 등)
    ...
    chunks.append({"id": "AufenthG-16b-3", "law": ..., "section": "16b", "absatz": "3",
                   "title": "Studium", "gliederung": path, "text": ..., "_refs": parse_refs(...)})
```

- **`render()`:** XML 요소를 평범한 텍스트로 펼칩니다. 번호 목록(`<DL>`)은 "1. …" 줄로 바꾸고, 각주는 버립니다.
- **삭제된 조항:** "(weggefallen)"(삭제됨)만 있는 항은 건너뜁니다.
- **같은 번호가 두 번 나오는 경우:** 공식 원문에도 실수가 있습니다(망명법 § 31에 "(3)"이 두 번). id가 겹치면 저장소가 오류를 내기 때문에 `_2`를 붙여 구분합니다.

**왜 항 단위로 자르나:** 조항 전체는 길고 여러 규칙이 섞여 검색이 흐려집니다. 문장 단위는 맥락이 끊깁니다. 독일 법에서 항 하나가 대개 규칙 하나라서 가장 알맞은 단위입니다.

### 3-4. 참조 찾기: `parse_refs()`와 `resolve()`

조문에는 "§ 25 Absatz 1 oder 2 Satz 1에 따른 체류허가"처럼 다른 조항을 가리키는 말이 많습니다. 이걸 찾아 `cross_refs`로 저장해 두면, 나중에 에이전트가 참조를 따라갈 수 있습니다.

정규식 하나로는 안 되는 이유는 표현이 너무 다양해서입니다.
- "§§ 16a, 16b und 18a" (여러 조항)
- "§ 25 Absatz 1 oder 2" (여러 항)
- "§§ 286 ff." (286조 이하)
- "§ 28e des Vierten Buches" (사회법전 제4권 = SGB IV)
- "dieses Gesetzes" (이 법)

그래서 `parse_refs()`는 텍스트를 **앞에서부터 한 토큰씩 읽어 가는 작은 해석기**로 만들었습니다. `T_NUM`(숫자), `T_ABS`("Absatz"), `T_SEP`("und", "oder", "bis"), `T_DET`("Satz 1", "Nummer 2") 같은 작은 정규식을 차례로 맞춰 보면서, 지금 읽는 숫자가 조항 번호인지, 항 번호인지, 문장·호 번호인지를 판단합니다.

```
"§ 25 Absatz 1 oder 2 Satz 1"
  §        → 참조 시작
  25       → 조항(section) 25
  Absatz 1 → 항 1         → {section 25, absatz 1}
  oder 2   → 앞이 항이었으니 2도 항 → {section 25, absatz 2}
  Satz 1   → 문장 번호, 저장하지 않음
```

`resolve()`는 찾은 참조가 실제로 있는지 확인하고, 각각 `ok`(코퍼스에 있음), `external`(코퍼스에 없는 법), `unresolved`(법은 있는데 조항이 없음)로 표시합니다.

### 3-5. 결과물

`data/processed/chunks.jsonl`, 한 줄에 청크 하나씩 10,029줄입니다.

```json
{"id": "AufenthG-26-3", "law": "AufenthG", "section": "26", "absatz": "3",
 "title": "Dauer des Aufenthalts", "gliederung": ["Kapitel 2 ...", "Abschnitt 5 ..."],
 "text": "Einem Ausländer, der eine Aufenthaltserlaubnis nach § 25 Absatz 1 oder 2 ...",
 "snapshot": "2026-10-08", "source_url": "https://www.gesetze-im-internet.de/aufenthg_2004/__26.html",
 "cross_refs": [{"law": "AufenthG", "section": "25", "absatz": "1", "status": "ok"}, ...]}
```

**직접 해 보기**
```bash
grep '"id": "AufenthG-26-3"' data/processed/chunks.jsonl | .venv/bin/python -m json.tool | head -30
```
```bash
.venv/bin/python -c "import json; r=json.load(open('data/processed/report.json')); print({k: r[k] for k in list(r)[:5]})"
```

---

## 4. retrieval.py: 검색 엔진

### 4-1. 무엇을 색인하나: `index_text()`

```python
def index_text(c):
    head = f"{c['law']} § {c['section']}" + (f" Abs. {c['absatz']}" if c.get("absatz") else "")
    title = section_title(c)                  # 제목, 없으면 목차 제목
    return f"{head} {title}\n{c['text']}"
# → "AufenthG § 16b Abs. 3 Studium\nDie Aufenthaltserlaubnis berechtigt ..."
```

본문 앞에 "어느 법 몇 조, 제목"을 붙여 색인합니다. 그래야 "블루카드"를 물었을 때 제목이 "Blaue Karte EU"인 조항이 잘 걸립니다.

### 4-2. dense 검색: 임베딩

```python
class STEmbedder:
    def __init__(self, model="BAAI/bge-m3", max_len=1024):
        self.m = SentenceTransformer(model)
        self.m.max_seq_length = max_len
    def encode(self, texts):
        return self.m.encode(texts, normalize_embeddings=True, ...)   # 길이 1로 맞춘 벡터
```

- **bge-m3:** 100개 넘는 언어를 같은 벡터 공간에 넣는 모델입니다. 그래서 한국어 질문 벡터와 독일어 조문 벡터를 바로 비교할 수 있습니다. 번역이 필요 없습니다.
- **정규화(normalize):** 벡터 길이를 1로 맞추면 코사인 유사도 = 내적(곱해서 더하기)이 됩니다. 계산이 간단해집니다.
- **`max_len=1024`:** 1,024토큰보다 긴 조문은 뒤쪽이 잘립니다. EStG § 3처럼 아주 긴 조문의 약점입니다.

```python
class NumpyStore:
    def query(self, vec, n, law=None):
        sims = self.emb @ vec            # 10,029개 청크 벡터와 질문 벡터를 한 번에 내적
        order = np.argsort(-sims)[:n]    # 큰 순서대로 n개
```

10,029 × 1,024 행렬 곱 한 번이면 끝나서, 이 규모에서는 이걸로 충분히 빠릅니다. `ChromaStore`는 같은 일을 데이터베이스(HNSW라는 근사 검색)로 합니다. 결과가 거의 같아서, 두 저장소는 인터페이스(`query()`)가 같고 바꿔 끼울 수 있게 만들었습니다.

### 4-3. BM25와 hybrid

```python
self.bm25 = BM25Okapi([tokenize(index_text(c)) for c in chunks])   # 단어 단위 색인
scores = self.bm25.get_scores(tokenize(query))
```

BM25는 단어가 같아야 점수가 나옵니다. 한국어 질문과 독일어 조문은 겹치는 단어가 없어서, 독일어 질문이 아니면 거의 쓸모가 없었습니다. 실험으로 확인한 결과입니다.

**hybrid = dense와 BM25를 RRF로 합치기**
```python
for lst in (dense_50, bm25_50):
    for rank, i in enumerate(lst):
        rrf[i] = rrf.get(i, 0) + 1.0 / (60 + rank + 1)
```
예: 어떤 조문이 dense 1등, BM25 3등이면 1/61 + 1/63 = 0.0323점입니다. dense에만 1등이면 1/61 = 0.0164점입니다. **두 목록 모두 위쪽에 있는 조문이 이깁니다.** 점수 크기가 다른 두 검색기를 순위만으로 공평하게 합칠 수 있어서, 이 프로젝트 곳곳에서 씁니다.

### 4-4. `LawIndex`: 묶음

```python
idx = LawIndex.build(chunks_path, out)        # 임베딩 계산 → emb.npy, chunks.jsonl, meta.json 저장 (CPU로 15분쯤)
idx = LawIndex.load(Path("data/index"))       # 저장된 것 불러오기 (몇 초)
idx.search("Blaue Karte Gehalt", k=8, mode="hybrid")
idx.get_section("AufenthG", "18a")            # 조항 번호로 바로 찾기
```

**직접 해 보기** (무료, 처음엔 모델을 불러오느라 30초쯤 걸림)
```bash
.venv/bin/python -m gesetzpolyglot.retrieval search "유학생 아르바이트" --mode dense --k 5
```
```bash
.venv/bin/python -m gesetzpolyglot.retrieval search "유학생 아르바이트" --mode bm25 --k 5
```
두 결과를 비교해 보면 BM25가 한국어에서 왜 약한지 바로 보입니다.

---

## 5. llm.py: LLM 연결

### 5-1. 모든 LLM은 같은 모양

```python
class LLM(Protocol):
    name: str
    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str: ...
```

OpenAI, Claude, Ollama(로컬) 클라이언트가 모두 `complete(system, user)` 하나만 가지고 있습니다. 그래서 나머지 코드는 어떤 회사 모델인지 몰라도 됩니다. 이런 설계를 "인터페이스에 맞춰 프로그래밍한다"고 합니다. 테스트에서 가짜 LLM을 끼우는 것도 이 덕분입니다.

### 5-2. OpenAI 클라이언트의 재시도

GPT-5 계열은 `temperature` 같은 옛 파라미터를 거부합니다. 그래서 일단 보내 보고, 거부당하면 그 파라미터를 빼고 다시 보냅니다.

```python
for _ in range(4):
    try:
        return self.client.chat.completions.create(...)
    except openai.BadRequestError as e:
        if "temperature" in str(e): self.extra.pop("temperature")   # 빼고 다시
        elif ...: ...
        else: raise
```

이 때문에 GPT-5 계열은 매번 답이 조금씩 다를 수 있습니다(실험에서 확인한 "잡음"의 원인).

### 5-3. 키는 어디서 오나

- **평가 스크립트:** `llm_from_env()`가 `.env` 파일과 환경변수에서 읽습니다. 우선순위는 명령줄(`--provider`, `--model`) > 셸 환경변수 > `.env`입니다.
- **공개 앱:** `make_llm(provider, model, api_key)`가 사용자가 입력한 키로만 만듭니다. 빈 키는 오류로 처리하고, 환경변수의 키로 넘어가지 않게 키를 항상 직접 넘깁니다.

```python
def make_llm(provider, model, api_key):
    if not api_key.strip(): raise ValueError("no API key given")
    if provider == "anthropic": return AnthropicLLM(model, api_key=api_key)
    if provider == "openai":    return OpenAICompatLLM(model, None, "low", api_key=api_key)
    if provider == "google":    return OpenAICompatLLM(model, GOOGLE_BASE_URL, None, api_key=api_key)
```

Gemini는 Google이 OpenAI와 같은 형식의 주소를 제공해서, OpenAI 클라이언트에 주소만 바꿔 연결했습니다.

---

## 6. prompts.py: 프롬프트와 버전

### 6-1. 버전을 어떻게 관리하나

```python
PROMPT_VERSION = os.environ.get("PROMPT_VERSION", "v4")
ANSWER_SYSTEM_V3 = ANSWER_SYSTEM.replace(_RULE3_V2, _RULE3_V3).replace(_RULE9_V2, _RULE9_V3)
assert _RULE3_V3 in ANSWER_SYSTEM_V3, "v2 rules 3/9 not found"
...
if PROMPT_VERSION == "v4":
    REWRITE_SYSTEM, ANSWER_SYSTEM, EXCERPTS_HEADER = REWRITE_SYSTEM_V3, ANSWER_SYSTEM_V4, EXCERPTS_HEADER_V4
```

- **새 버전은 이전 버전에서 바뀐 규칙만 `replace`로 갈아 끼워** 만듭니다. 어디가 달라졌는지 코드에서 바로 보입니다.
- **`assert`:** 갈아 끼울 문장을 못 찾으면(누가 원문을 고쳤으면) 바로 오류가 납니다. 조용히 엉뚱한 프롬프트가 되는 것을 막습니다.
- **한 번 평가한 버전은 고치지 않습니다.** 예전 실험을 똑같이 다시 돌릴 수 있어야 비교가 정직하기 때문입니다.
- 프롬프트는 **import할 때** 정해집니다. 그래서 평가 스크립트는 환경변수를 먼저 설정하고 나서 rag를 불러옵니다.

### 6-2. 답변 프롬프트의 핵심 규칙 (v4)

1. 질문 언어로 답할 것
2. 모든 사실 뒤에 `[AufenthG § 18a Abs. 1]` 형식으로 인용할 것, 받은 조문에 있는 것만
3. 적용 범위부터 확인할 것(EU 시민이면 자유이동법). 국적을 모르면 두 경우로 나눠 답할 것
4. 범위 밖이면 거절하고, 일부만 답할 수 있으면 그 부분은 답할 것
5. "본인 사건을 판단해 달라"는 질문에만 `explain_without_judgment`
6–9. 조항의 대상과 범위를 정확히 읽을 것, 잘못된 전제는 바로잡을 것, 망명 기한 주의, 코퍼스 밖 EU 규정은 이름만 밝힐 것
10. 짧게, 추가 도움을 제안하지 말 것
11. 조문은 시스템이 검색한 것이니 사용자에게 조문을 달라고 하지 말 것

그리고 첫 줄에 반드시 `STATUS: answer`(또는 `refuse_out_of_scope`, `explain_without_judgment`)를 쓰게 합니다. 기계가 응답 유형을 읽을 수 있게 하기 위해서입니다.

**직접 해 보기**
```bash
PROMPT_VERSION=v4 .venv/bin/python -c "from gesetzpolyglot import prompts; print(prompts.ANSWER_SYSTEM)"
```

---

## 7. rag.py: 검색 → 답변 → 검증

질문 하나가 `RAG.answer(question, condition)`으로 들어오면:

### 7-1. 언어 감지: `detect_lang()`

```python
if re.search(r"[가-힣]", text): return "ko"            # 한글이 있으면 한국어
if re.search(r"[؀-ۿ]", text):                # 아랍 문자
    return None if _PERSIAN_URDU.search(text) else "ar"
if _OTHER_SCRIPT.search(text) or _TURKISH.search(text): return None   # 지원 안 하는 문자
score = {lang: (기능어 개수 / 단어 수) for lang in en, de, it, fr, es, pt, nl, pl, tr}
best = max(score)
return best if best in 지원언어 and score >= 0.15 else None
```

LLM을 부르지 않는 규칙 기반이라 무료이고 항상 같은 결과가 나옵니다. 프랑스어, 스페인어 같은 기능어 목록도 일부러 넣었습니다. 그래야 프랑스어를 영어로 착각하지 않고 "지원하지 않음"으로 판단합니다. `None`이 나오면 검색도 LLM 호출도 하지 않고 안내문만 돌려줍니다.

### 7-2. 검색: `_retrieve()`

```python
if condition in ("dense", "hybrid"):
    ranked = self.index.search(question, n, mode=condition)        # 질문 그대로 검색
else:  # rewrite
    queries = parse_queries(llm.complete(REWRITE_SYSTEM, question))   # LLM이 독일어 검색어 1–3개 생성
    for q in queries: ... RRF로 합침
if self.graph: out, step = fuse_kg(...)                          # 개념 그래프가 켜져 있으면 섞기
```

agent 조건은 `agent.py`로 넘어갑니다(8장).

### 7-3. 공통 마무리: `finish()`

**모든 조건이 똑같은 `finish()`를 씁니다.** 그래서 조건끼리 차이가 나면 그건 순수하게 검색 방식 때문입니다. 공정한 비교를 위한 설계입니다.

```python
system = ANSWER_SYSTEM.replace("{lang_name}", LANG_NAMES[lang])
user = f"{EXCERPTS_HEADER}\n\n{format_excerpts(retrieved)}\n\nQuestion: {question}"
status, body = parse_status(llm.complete(system, user))       # 첫 줄의 STATUS 읽기
valid, invalid = validate_citations(body, retrieved)          # 인용 검증
```

**인용 검증 (`validate_citations`)**
```python
CITE_RE = re.compile(r"\[\s*(AufenthG|BeschV|...)\s*§\s*(\d+[a-z]?)(?:\s*(?:Abs\.|Absatz)\s*(\d+[a-z]?))?[^\]]*\]")
for law, sec, absatz in CITE_RE.findall(answer):
    ok = (law, sec, absatz) in 검색된_것 if absatz else (law, sec) in 검색된_조항
```
답 속의 `[법 § 조 Abs. 항]`을 모두 찾아, 실제로 검색해 온 조문과 대조합니다. 없으면 `invalid`이고, 앱에서 ⚠️로 표시됩니다. **LLM이 지어낸 조항 번호를 잡아내는 장치**입니다.

**응답 유형 (`parse_status`):** 첫 줄이 정확히 한 가지 유형을 말해야 합니다. 템플릿을 베껴 "answer | refuse"라고 쓰면 `unclear`(오답)로 셉니다.

**직접 해 보기** (유료, 1센트 미만)
```bash
env -u OPENAI_API_KEY .venv/bin/python -m gesetzpolyglot.rag "유학생도 일할 수 있나요?" --condition rewrite --json
```
출력의 `trace`를 위에서부터 읽어 보세요: `detect_lang` → `rewrite`(LLM이 만든 독일어 검색어) → `retrieve` → `validate`.

---

## 8. agent.py: LangGraph 에이전트

LangGraph는 "함수(노드)들을 화살표로 연결하고, 하나의 공유 dict(상태)를 들고 돌아다니게 하는" 도구입니다.

```
plan → retrieve → follow_refs → check ─(충분)→ answer
          ▲                        │
          └────(부족, 최대 2번)────┘
```

| 노드 | LLM 사용 | 하는 일 |
|---|---|---|
| plan | 1번 | 질문을 하위 질문과 독일어 검색어로 나눔 |
| retrieve | 없음 | 검색어마다 hybrid 검색, 점수를 RRF로 누적 |
| follow_refs | 없음 | 상위 조문의 `cross_refs`(3장)를 따라가 참조된 조문을 추가 |
| check | 1번 | "이걸로 충분한가?" 부족하면 빠진 부분의 검색어를 받아 다시 retrieve |
| answer | 1번 | 상위 12개 조문으로 7장의 `finish()` 호출 |

```python
g = StateGraph(AgentState)
g.add_node("plan", plan); ...
g.add_edge(START, "plan"); g.add_edge("plan", "retrieve"); ...
g.add_conditional_edges("check", route, {"answer": "answer", "retry": "next_round"})
```

**follow_refs가 왜 중요한가:** 난민 정주허가 조항(§ 26 Abs. 3)은 "난민"이라는 말 없이 "§ 25 Absatz 2에 따른 체류허가"라고만 씁니다. "난민"으로 검색하면 못 찾지만, § 25를 찾으면 거기서 참조를 따라갈 수 있습니다.

노드마다 상태가 어떻게 바뀌는지 직접 보는 데모가 있습니다(LLM 대신 대본을 읽는 가짜, 무료).
```bash
.venv/bin/python -m pytest tests/test_agent.py -q
```

---

## 9. kg.py, concepts.py: 개념 그래프

**`concepts.py`(데이터):** 개념 59개와 국적 그룹 4개입니다.
```python
"registration": {"ko": ["안멜둥", "주민등록", ...], "en": [...], "de": [...], "ar": [...], "it": [...],
                 "sections": ["BMG § 17 Abs. 1"]},
"family": {..., "sections": ["AufenthG § 27", "AufenthG § 30"],
           "with_group": {"eu": ["FreizügG/EU § 3 Abs. 1", ...]},        # EU 국적이 있으면 추가
           "instead_of": {"eu": ["AufenthG § 27", ..., "AufenthG § 30"]}},  # EU 국적이면 빼기
```

**`kg.py`(로직)**
1. `match()`: 질문에서 개념 별칭을 찾습니다. 라틴 문자 별칭은 단어 처음에서만 맞추고("ital"은 "Italian"엔 맞고 "capital"엔 안 맞음), 한국어와 아랍어는 조사·접두사가 붙으니 어디서든 맞춥니다.
2. `nationalities()`: 나라 이름마다 역할을 정합니다.
   - **장소:** "네덜란드에", "프랑스에서 일하다", "스위스회사", "travel to …"
   - **가족:** 앞뒤 두 단어 안에 배우자·엄마 같은 말이 있음
   - **질문자:** 나머지
3. `plan()`: 붙일 조항 목록(구체적인 것부터)과 뺄 조항을 정합니다.
4. `kg_chunks()`: 조항 번호를 실제 청크로 바꿉니다. 조 전체면 질문과 가장 가까운 항 2개를 고릅니다.
5. `fuse_kg()`: 기존 검색 결과와 RRF로 섞고, 뺄 조항을 지웁니다. 아무 개념도 안 걸리면 기존 결과 그대로입니다.

**직접 해 보기** (무료)
```bash
.venv/bin/python -m gesetzpolyglot.kg "저는 프랑스 사람이고 독일에서 일하고 있습니다. 미국인 배우자도 같이 독일에 살 수 있나요?"
```

**교훈(실험 결과):** 평가 질문을 아는 사람이 그래프를 만들면 점수가 크게 부풀려집니다(0.79). 그래프를 본 적 없는 사람의 질문에서는 효과가 +0.10 정도였습니다. 자세한 건 README의 실험 섹션에 있습니다.

---

## 10. app.py: 웹 화면

Gradio는 파이썬 함수에 웹 화면을 붙여 주는 라이브러리입니다.

```python
with gr.Blocks(title="Gelyglot") as demo:
    q = gr.Textbox(label="Question")                 # 입력 칸
    cond = gr.Dropdown([...], label="Retrieval condition")
    key = gr.Textbox(type="password", label="API key")
    btn = gr.Button("Ask / Fragen")
    out = gr.Markdown()                              # 출력 칸
    btn.click(run, [q, cond, provider, model, key], [out, src, steps, tr])   # 버튼 → 함수 → 출력
```

`btn.click(함수, 입력들, 출력들)`이 핵심입니다. 버튼을 누르면 입력 칸의 값들이 함수 인자로 들어가고, 함수가 돌려준 값들이 출력 칸에 들어갑니다.

- **`run()`:** 입력을 검사하고(빈 질문, 빈 키), 답변 함수를 부르고, 오류는 `explain_error()`로 읽기 쉬운 문장으로 바꿉니다(키는 `***`로 가림).
- **`render()`:** 결과 dict를 화면용으로 바꿉니다. 인용은 원문 링크로, 잘못된 인용은 ⚠️로, 검색된 조문은 펼침 목록으로, trace는 단계 설명으로 바꿉니다.
- **실행 모드 두 가지:**
  - 기본은 사용자 키 모드입니다. 시작할 때 서버의 키 환경변수를 지우고, 질문마다 사용자 키로 LLM을 새로 만듭니다(인덱스는 공유).
  - `--server-key`는 `.env`의 운영자 키를 씁니다.
- **ZeroGPU:** Hugging Face 무료 Space에서는 `spaces`를 파일 맨 위에서 먼저 불러오고, 질문 임베딩 함수만 `@spaces.GPU`로 감쌉니다(`use_zero_gpu()`).

**직접 해 보기** (켜는 건 무료, 질문할 때 내 키 비용)
```bash
.venv/bin/python app.py
```

---

## 11. evaluation/: 얼마나 잘하나 재기

### 11-1. 평가 질문 (`evalset/*.jsonl`)

```json
{"id": "n13", "set": "ko", "question": "비EU 국적 유학생은 독일에서 공부하면서 일을 할 수 있나요? ...",
 "type": "single", "expected_behavior": "answer", "gold_sections": ["AufenthG § 16b Abs. 3"],
 "persona_country": "", "persona_group": "non_eu", ...}
```
같은 60문항이 6개 언어 파일에 있습니다. `gold_sections`가 "정답 조항"이고, `expected_behavior`가 "기대하는 응답 유형"입니다.

### 11-2. 검색 평가 (`eval_retrieval.py`, 무료)

```python
def is_hit(gold, chunk):          # 정답 조항과 검색된 청크가 같은가
    law, sec, absatz = gold
    return chunk["law"] == law and chunk["section"] == sec and (absatz is None or chunk["absatz"] == absatz)

found = [any(is_hit(g, h) for h in hits) for g in golds]
recall = sum(found) / len(golds)  # 정답 2개 중 1개 찾으면 0.5
```

### 11-3. 답변 평가 (`eval_answers.py`, 유료)

문항마다, 조건마다 실제로 답을 받아 recall, 응답 유형 일치(`status_ok`), 잘못된 인용, LLM 호출 수, 시간, 토큰을 한 줄씩 기록합니다. `--kg both`면 같은 문항을 그래프를 켜고 끈 채로 두 번 돌립니다.

### 11-4. 짝지은 비교 (`compare.py`)

두 방식을 **같은 문항끼리** 비교합니다(짝지은 비교). 문항마다 난이도가 달라서, 따로 평균 내는 것보다 정확합니다.

- **부트스트랩 신뢰구간:** 문항을 무작위로 다시 뽑아(중복 허용) 평균 차이를 1만 번 계산하고, 가운데 95% 범위를 구간으로 씁니다. 구간에 0이 들어 있으면 "차이가 없을 수도 있다"는 뜻입니다.
- **McNemar 검정 (맞음/틀림 지표):** 두 방식의 결과가 **다른** 문항만 봅니다. A만 맞힌 문항과 B만 맞힌 문항 수가 얼마나 기울었는지로 p값을 계산합니다.
- **p값:** "실제로는 차이가 없는데 우연히 이만큼 차이가 날 확률"입니다. 보통 0.05보다 작으면 "유의하다"고 합니다.
- 시드를 고정해서 같은 결과 파일이면 항상 같은 숫자가 나옵니다.

### 11-5. 실험 실행기와 기록 (`ablation.py`, `manifest.py`)

`ablation.py`는 위 단계를 한 번에 돌려 `results/experiments/<이름>/`에 결과와 `report.md`를 씁니다. `manifest.json`에는 git 커밋, 프롬프트 버전, 모델, 인덱스, 그래프 버전, 질문 파일 지문(해시)이 남습니다. **"이 숫자가 어떤 상태에서 나왔는가"를 나중에 정확히 밝히기 위한 기록**입니다.

**직접 해 보기** (무료, 몇 분)
```bash
.venv/bin/python -m evaluation.eval_retrieval --evalset evalset/ko.jsonl --modes dense
```
```bash
.venv/bin/python -m evaluation.ablation --name my-first-ablation --sets heldout
```

---

## 12. tests/: 테스트

```bash
.venv/bin/python -m pytest -q
```

테스트 52개가 1–4초 안에 돌고, **진짜 모델도 API 키도 필요 없습니다.** 비결은 가짜를 끼워 넣는 것입니다.

- **가짜 임베더 (`FakeEmbedder`):** 단어를 해시해서 벡터를 만듭니다. 뜻은 모르지만 같은 단어가 있으면 비슷한 벡터가 되어, 검색 로직을 시험하기엔 충분합니다.
- **가짜 LLM (`ScriptedLLM`, `FakeLLM`):** 정해진 대본대로만 답합니다. 그래서 "LLM이 이렇게 답하면 파이프라인이 이렇게 동작해야 한다"를 확인할 수 있습니다.
- **5장에서 본 "모두 같은 모양" 설계가 있기에** 가짜를 끼울 수 있습니다.

| 파일 | 지키는 것 |
|---|---|
| `test_gii_parser.py` | 참조 해석(§§ ff., SGB 서수, 같은 번호 중복 등) |
| `test_retrieval.py` | 색인 텍스트, 검색 모드, recall 계산 |
| `test_rag.py` | 언어 감지, 응답 유형, 인용 검증, 프롬프트 버전 |
| `test_agent.py` | 에이전트가 참조를 따라가고, 재시도 한도를 지키고, 망가진 JSON에도 버티는지 |
| `test_kg.py` | 그래프 조항이 코퍼스에 실제로 있는지, 국적 역할, 비교 통계 |
| `test_byok.py` | 사용자 키 필수, 운영자 키로 넘어가지 않음, 오류에 키가 안 보임, ZeroGPU 연결 |
| `test_evalset.py` | 6개 언어 파일의 문항·정답이 서로 일치하는지 |

버그를 고칠 때마다 그 버그를 재현하는 테스트를 하나씩 추가했습니다. 같은 버그가 다시 생기면 바로 걸립니다.

---

## 13. 혼자 해 보기

쉬운 것부터 해 보세요. 막히면 이 문서의 해당 장을 다시 보면 됩니다.

1. **검색 결과 비교:** 같은 질문을 한국어·독일어·영어로 `retrieval search`에 넣어 보고 결과가 얼마나 다른지 봅니다(4장).
2. **조문 하나 따라가기:** `chunks.jsonl`에서 `AufenthG-26-3`의 `cross_refs`를 보고, 그 조문들을 `get_section`으로 찾아봅니다(3장, 4장).
3. **개념 추가:** `concepts.py`에 개념 하나를 5개 언어 별칭과 함께 넣고 `pytest tests/test_kg.py`를 돌려 봅니다. 없는 조항을 쓰면 테스트가 잡아 줍니다(9장).
4. **프롬프트 실험:** `prompts.py`에 v5를 만들어 규칙 하나를 바꾸고, `--prompts v5`로 질문 하나를 돌려 봅니다. v4는 고치지 말고 새 버전으로 만드세요(6장).
5. **비교 하나 만들기:** `ablation.py`를 돌린 뒤 `compare.py`로 dense와 dense+kg를 비교하고, 신뢰구간이 무슨 뜻인지 스스로 설명해 봅니다(11장).

이 다섯 개를 해 보면 면접에서 어떤 질문이 와도 코드를 직접 짚으며 설명할 수 있을 겁니다.
