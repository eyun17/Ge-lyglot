# GesetzPolyglot

독일 법을 내 언어로 묻고, 독일어 원문 조문에 근거한 답을 받습니다.

GesetzPolyglot은 독일에 사는 외국인에게 중요한 독일 법령을 대상으로 하는 RAG 질의응답 시스템입니다.
지금은 체류법(**AufenthG**), 고용령(**BeschV**), 망명법(**AsylG**)을 다루고, 다음으로 외국인 관련 세법을 추가할 예정입니다([로드맵](#로드맵) 참고).
한국어, 영어, 터키어, 아랍어, 이탈리아어, 독일어로 물으면 독일어 원문 조문을 찾아 인용과 함께 답하고, 인용이 실제로 검색된 조문인지 검증합니다.
같은 질문을 네 가지 검색 조건으로 돌려, 어떤 검색 방식이 답의 근거를 더 잘 찾는지 비교하는 것이 목적입니다.

> **법률·세무 자문이 아닙니다.** 참고용으로만 사용하세요. 답변을 과신하거나 오용해 생긴 결과에 대해 작성자는 책임지지 않습니다. [면책 고지](#면책-고지)를 참고하세요.

## 구성

```
gesetze-im-internet.de XML
        │  gii_parser.py      날짜별 스냅샷 다운로드 → Absatz 단위 청크 + 상호참조
        ▼
data/processed/chunks.jsonl   조문 1,378개 (AufenthG 916, BeschV 88, AsylG 374)
        │  retrieval.py       bge-m3 임베딩, BM25, 벡터 저장소 (numpy | Chroma)
        ▼
data/index/
        │  rag.py             조건 1–3: 단일 패스 RAG + 인용 검증
        │  agent.py           조건 4: LangGraph 에이전트
        ▼
app.py (Gradio UI) · eval_retrieval.py (검색 평가)
```

| 파일 | 역할 |
|---|---|
| [laws.py](laws.py) | 법령 목록을 한 곳에 모은 파일입니다. 어떤 법령이 있고 어떤 법령을 색인하는지, 프롬프트와 앱에서 코퍼스를 어떻게 설명하는지 정합니다. [법령 추가하기](#법령-추가하기) 참고. |
| [gii_parser.py](gii_parser.py) | 법령 XML을 받아 Absatz 단위 JSONL로 파싱합니다. 원본은 `data/raw/<law>/<날짜>/`에 덮어쓰지 않고 쌓입니다. |
| [retrieval.py](retrieval.py) | 인덱스를 만들고 dense, BM25, hybrid(RRF) 검색을 합니다. |
| [rag.py](rag.py) | 검색 → 생성 → 인용 검증. 답변 상태는 `answer`, `refuse_out_of_scope`, `explain_without_judgment` 중 하나입니다. |
| [agent.py](agent.py) | 질문을 하위 질문으로 나누고, 상호참조를 따라가고, 근거가 충분한지 확인해 최대 2번 다시 검색합니다. |
| [app.py](app.py) | Gradio 웹 UI입니다. 화면은 영어이고, 요소마다 아래에 독일어가 작고 연하게 함께 나옵니다(법령의 언어가 독일어이기 때문). 답변은 질문한 언어로 나옵니다. |
| [eval_retrieval.py](eval_retrieval.py) | 조항 단위 recall@k를 잽니다. |

### 비교하는 네 가지 조건

| 조건 | 내용 |
|---|---|
| `dense` | bge-m3 밀집 검색, 단일 패스 |
| `hybrid` | BM25 + dense를 RRF로 합침, 단일 패스 |
| `rewrite` | hybrid + LLM이 질문을 독일어 법률 검색어로 바꿈 |
| `agent` | LangGraph: plan → retrieve → follow_refs → check → answer |

네 조건 모두 마지막 단계(답변 프롬프트, 인용 검증)는 같은 `rag.finish()`를 씁니다. 그래서 차이는 검색 쪽에서만 납니다.

## 설치

Python 3.11 기준입니다.

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

`sentence-transformers`가 torch를 함께 설치합니다. Linux나 Windows에서 GPU가 없다면 CPU용 torch를 먼저 설치하면 용량이 크게 줄어듭니다.

```bash
pip install torch --index-url https://download.pytorch.org/whl/cpu
```

검증된 버전 조합은 [requirements.lock](requirements.lock)에 있습니다.

LLM 설정은 `.env`에 둡니다. `.env`는 git에 올라가지 않습니다.

```bash
cp .env.example .env
```

| 변수 | 기본값 | 설명 |
|---|---|---|
| `OPENAI_API_KEY` | | 필수 (OpenAI 사용 시) |
| `LLM_PROVIDER` | `openai` | `openai` 또는 `anthropic` |
| `LLM_MODEL` | `gpt-5.4-nano` / `claude-sonnet-5-5` | |
| `LLM_REASONING_EFFORT` | `low` | `none`, `low`, `medium`, `high`. 비워 두면 보내지 않습니다. |
| `OPENAI_BASE_URL` | | 호환 서버용, 예: `http://localhost:11434/v1` (Ollama) |

## 사용법

### 1. 데이터 받기와 파싱

```bash
python gii_parser.py fetch
```

```bash
python gii_parser.py parse
```

파싱 결과 요약(조문 수, 해결되지 않은 상호참조)은 `data/processed/report.json`에 저장됩니다.

### 2. 인덱스 만들기

```bash
python retrieval.py build --store chroma
```

`--store`를 빼면 numpy 저장소만 만듭니다. 이미 numpy로 만든 인덱스가 있다면 임베딩을 다시 하지 않고 Chroma로 옮길 수 있습니다.

```bash
python retrieval.py to-chroma
```

검색만 따로 해 볼 수도 있습니다. `--law`는 메타데이터 필터입니다.

```bash
python retrieval.py search "Zustimmung" --law BeschV --k 5
```

### 3. 질문하기

```bash
python rag.py "유학생도 일할 수 있나요?" --condition agent
```

```bash
python app.py
```

앱은 http://127.0.0.1:7860 에서 열립니다. `--share`를 붙이면 임시 공개 링크가 생깁니다.

## 벡터 저장소

`retrieval.py`에는 인터페이스가 같은 저장소가 두 개 있고, 어느 쪽을 쓸지는 `data/index/meta.json`의 `store` 값으로 정해집니다.

- **NumpyStore**: `emb.npy` 전체와 코사인 유사도를 계산하는 정확 검색입니다.
- **ChromaStore**: ChromaDB 영구 컬렉션(`data/index/chroma/`, HNSW, 코사인 거리)입니다. 각 조문에 `law`, `section`, `absatz`, `title`, `snapshot` 메타데이터가 붙어 있어 `where` 필터를 쓸 수 있습니다.

BM25는 Chroma에 없는 기능이라 항상 메모리에서 돌고, hybrid는 "저장소의 dense 결과 + BM25"를 RRF로 합칩니다.
`emb.npy`는 Chroma를 쓸 때도 남겨 둡니다. 에이전트가 조항 안의 Absatz 순위를 매길 때 쓰고, 정확 검색 기준선으로도 필요합니다.

조문 1,378개 규모에서는 numpy로도 충분히 빠릅니다. Chroma를 붙인 이유는 속도보다 영구 저장, 메타데이터 필터, 그리고 다른 법령(예: AufenthV)을 추가할 때의 확장성입니다.

**검증.** 실제 bge-m3 인덱스와 세 법령 코퍼스에서 평가 질문 246개(공통 156개, 난민 모듈 90개)를 두 저장소로 돌렸습니다. dense와 bm25는 top-8 목록이 246/246 동일했고, hybrid는 245/246이 같았습니다. hybrid는 dense 후보를 50개까지 가져오는데, 그 아래쪽 순위에서 HNSW 근사 때문에 순위가 한 칸 바뀔 수 있습니다. recall은 모든 모드에서 두 저장소가 같았습니다.

## 평가

평가셋은 같은 30문항으로 된 여섯 세트입니다. 세트는 언어와 질문하는 사람의 국적을 묶은 단위입니다.

| 세트 | 파일 | 질문자 |
|---|---|---|
| `ko` | [evalset_draft_ko.jsonl](evalset_draft_ko.jsonl) | 한국인 (원문) |
| `en` | [evalset_draft_en.jsonl](evalset_draft_en.jsonl) | 한국인 (`ko` 번역) |
| `tr-TR` | [evalset_draft_tr.jsonl](evalset_draft_tr.jsonl) | 튀르키예 국적자 |
| `ar-SY` | [evalset_draft_ar_sy.jsonl](evalset_draft_ar_sy.jsonl) | 시리아 국적자 |
| `ar-PS` | [evalset_draft_ar_ps.jsonl](evalset_draft_ar_ps.jsonl) | 팔레스타인인 |
| `it-IT` | [evalset_draft_it.jsonl](evalset_draft_it.jsonl) | 이탈리아 국적자 (EU) |

튀르키예, 시리아, 팔레스타인 출신은 독일에서 가장 큰 이민자 집단에 속하고, 이탈리아는 체류법이 대부분 적용되지 않는 EU 시민의 예로 넣었습니다. 파일마다 읽기용 `.md`가 함께 있습니다. 터키어·아랍어·이탈리아어 번역은 아직 원어민 검토를 받지 않았습니다.

| 유형 | 세트당 문항 수 | 기대 동작 |
|---|---|---|
| `single` | 12 | 조항 하나로 답할 수 있는 질문 |
| `multi` | 12 | 여러 조항을 묶어야 하는 질문 |
| `refusal` | 6 | 범위 밖이라 거절하거나, 개인 판단 없이 요건만 설명 |

`it-IT`는 다릅니다(11 / 10 / 9). 아래를 보세요.

**표현.** 질문은 각 커뮤니티 사람들이 실제로 묻는 방식으로 썼습니다. 체류허가나 기관 이름은 그 커뮤니티에서 흔히 쓰는 말로 쓰고, 괄호 속 독일어는 붙이지 않았습니다(한국어 블루카드·아우스빌둥·안멜둥, 영어 "do an Ausbildung"·"do their Anmeldung", 터키어 Mavi Kart·Ausbildung yapmak, 아랍어 البطاقة الزرقاء·أوسبيلدونغ, 이탈리아어 Carta Blu UE·fare l'Anmeldung). 이 용어들은 아직 원어민 검토가 필요합니다.

**현지화.** 질문자의 국적이 나오는 6문항("저는 한국 국적이고…" 등)은 세트마다 그 국적으로 바꾸고 `localized: true`로 표시했습니다. 국적이 바뀌면 정답이, 때로는 정답 조항까지 달라집니다.
- **튀르키예, 시리아, 팔레스타인:** 정답 조항은 같고 답이 달라집니다. 예를 들어 BeschV § 26 Abs. 1은 한국 국적자에게 취업 특례를 주지만 튀르키예·시리아·팔레스타인은 목록에 없으므로, 특례가 없다고 답해야 합니다. 팔레스타인 세트에는 독일이 팔레스타인을 국가로 승인하지 않아 국적이 무국적·불명으로 기록되는 경우가 많다는 메모도 달았습니다.
- **이탈리아:** 5문항(q01, q15, q24, q27, q29)이 범위 밖이 됩니다. EU 시민은 체류법이 아니라 EU 자유이동법의 적용을 받기 때문입니다(AufenthG § 1 Abs. 2 Nr. 1). 기대 동작은 `refuse_out_of_scope`, 정답 조항은 § 1 Abs. 2가 됩니다. 그래서 `it-IT`는 `single` 11, `multi` 10, `refusal` 9문항입니다.

정답 조항(`gold_sections`)이 있는 세트당 26문항(총 156문항)으로 검색 recall을 잽니다. 정답 조항이 Absatz 없이 적혀 있으면 그 조항의 어느 Absatz를 찾아도 맞은 것으로 칩니다.

```bash
python eval_retrieval.py --store numpy --modes dense bm25 hybrid
```

```bash
python eval_retrieval.py --store chroma --modes dense bm25 hybrid
```

문항별 결과는 `results/retrieval_<store>_<mode>.jsonl`에 저장됩니다. 위 명령은 공통 세트와 [난민·보호 모듈](#난민보호-모듈)을 함께 평가하고, 결과는 따로 보고합니다.

### 현재 결과 (recall@8, AufenthG·BeschV 2026-10-08, AsylG 2026-10-09 스냅샷)

| 모드 | 전체 | ko | en | tr-TR | ar-SY | ar-PS | it-IT |
|---|---|---|---|---|---|---|---|
| dense | **0.567** | 0.532 | 0.571 | 0.590 | 0.590 | 0.590 | 0.532 |
| bm25 | 0.019 | 0.000 | 0.038 | 0.038 | 0.000 | 0.000 | 0.038 |
| hybrid | 0.503 | 0.532 | 0.378 | 0.513 | 0.590 | 0.590 | 0.417 |

`multi` 질문(dense): ko 0.444, en 0.486, tr-TR 0.444, ar-SY 0.486, ar-PS 0.486, it-IT 0.483.

numpy와 Chroma의 recall은 동일합니다.

**읽는 법과 한계**
- bge-m3 밀집 검색은 언어와 관계없이 비슷하게 작동합니다(정답 조항이 같은 세트에서 0.532–0.590). 번역 없이도 독일어 조문을 찾습니다.
- **질문 속 독일어 용어가 검색을 크게 돕습니다.** 이전 초안은 "직업교육(Ausbildung)"처럼 독일어를 괄호로 붙였습니다. 괄호 속 독일어를 빼자 dense recall이 전체 0.593에서 0.567로(한국어 0.571 → 0.532, 아랍어 0.628 → 0.590) 떨어졌고, BM25는 거의 아무것도 찾지 못하게 됐습니다(0.085 → 0.019). 실제 사용자는 독일어 용어를 잘 붙이지 않으므로 지금 수치가 현실적인 기준선이고, `rewrite`가 메우려는 차이가 바로 이것입니다.
- **코퍼스가 커져도 dense 검색은 나빠지지 않았습니다.** AsylG를 추가해 청크가 1,004개에서 1,378개로(+37%) 늘었지만, dense recall은 156문항 모두에서 그대로였습니다. 정답 조항을 잃거나 새로 찾은 문항이 하나도 없고, AsylG 청크가 top 8에 들어온 문항도 7개뿐입니다. hybrid는 BM25가 54개 문항에서 AsylG 청크를 잡음으로 끌어오면서 양쪽으로 조금 움직였습니다(터키어 0.551 → 0.513, 이탈리아어 0.378 → 0.417). 이전 결과는 `results/before_asylg/`에 보관했습니다.
- **적용 범위는 검색되지 않습니다.** 정답이 "EU 시민에게는 체류법이 적용되지 않는다"인 이탈리아어 5문항에서 recall이 모든 모드에서 0입니다. 검색은 주제(유학생 취업, 블루카드)는 찾지만, 그 주제 전체가 범위 밖이라고 말하는 AufenthG § 1 Abs. 2는 한 번도 찾지 못했습니다. `it-IT` 점수가 가장 낮은 이유입니다. 검색 전에 적용 범위를 확인하는 단계(예: 질문자가 EU 시민이면 § 1 Abs. 2를 항상 가져오기)가 해결책 후보입니다.
- BM25는 질문이 독일어가 아니라서 거의 작동하지 않습니다. hybrid가 얼마나 손해를 보는지는 문자 체계에 따라 다릅니다.
  - 한국어와 아랍어는 독일어와 겹치는 토큰이 없습니다. BM25가 한국어 25/26, 아랍어 25/26 문항에서 아무것도 돌려주지 않아, hybrid가 사실상 dense가 되고 손해가 없습니다.
  - 영어, 터키어, 이탈리아어는 라틴 문자라 BM25가 거의 늘 무언가를 찾는데, 대부분 잡음입니다. 영어는 26/26 문항에서 결과를 돌려주고 hybrid가 0.571에서 0.378로 떨어집니다.
  - 질문을 독일어로 바꾸는 `rewrite` 조건이 이 문제를 겨냥한 것입니다.
- 여러 조항을 묶어야 하는 `multi` 질문의 recall이 낮습니다. 상호참조를 따라가는 `agent` 조건이 이 부분을 겨냥합니다.
- 시리아 세트와 팔레스타인 세트는 현지화된 6문항만 다르고 recall이 똑같습니다. 국적 표현은 검색에 거의 영향을 주지 않고 답에 영향을 줍니다. 그래서 아직 하지 않은 답변 단위 평가에서 확인해야 합니다.
- 평가셋은 아직 초안입니다. 정답 조항은 직접 작성했고 아직 검증(`verified`)되지 않았습니다.
- 조건 3·4(`rewrite`, `agent`)와 답변 품질에 대한 평가는 아직 이 README에 없습니다.

### 난민·보호 모듈

난민 지위, 보충적 보호, 체류 유예(Duldung), 가족 재결합, 망명 절차를 다루는 별도의 질문 세트입니다. 17문항(`single` 9, `multi` 4, `refusal` 4)이고, 파일은 `evalset_refugee_<세트>.jsonl`이며 읽기용 `.md`가 함께 있습니다. 질문에 국적이 나오지 않아 여섯 세트 모두 같은 질문이므로 언어 간 비교가 가능합니다. 공통 세트와는 다른 질문이라 따로 집계합니다(`module: refugee`). 정답 조항은 원문으로 확인했지만 아직 `verified`는 아닙니다.

| 모드 | 전체 | ko | en | tr-TR | ar-SY | ar-PS | it-IT |
|---|---|---|---|---|---|---|---|
| dense | **0.456** | 0.400 | 0.467 | 0.467 | 0.400 | 0.400 | 0.600 |
| bm25 | 0.017 | 0.000 | 0.000 | 0.100 | 0.000 | 0.000 | 0.000 |
| hybrid | 0.406 | 0.400 | 0.400 | 0.433 | 0.400 | 0.400 | 0.400 |

- **놓치는 이유는 언어가 아닙니다.** 6문항(r01, r04, r08, r11, r13, r15)은 여섯 언어 모두에서 0입니다. 원인은 조문을 쓰는 방식에 있습니다. 조문은 "난민"이라는 말을 거의 쓰지 않습니다. 난민의 영주권 조항인 AufenthG § 26 Abs. 3은 "§ 25 Abs. 1 또는 2에 따른 체류허가"라고만 쓰고, § 25 Abs. 2와 § 12a Abs. 1은 "EU 규정 2024/1347에 따른 국제적 보호"라고 씁니다. "난민"이라고 묻는 질문과 맞춰볼 단어가 없습니다. 해결책 후보는 두 가지입니다. 참조된 조항의 제목을 색인 텍스트에 함께 넣거나(그러면 § 26 Abs. 3에 "Aufenthalt aus humanitären Gründen"도 붙음), `agent`가 이런 참조를 따라가게 하는 것입니다.
- 언어에 따라 갈리는 문항도 있습니다. 망명 소송 기한(r09, AsylG § 74 Abs. 1)은 한국어와 이탈리아어에서는 찾지만 나머지 네 언어에서는 못 찾습니다.

## 법령 추가하기

법령 이름은 모두 [laws.py](laws.py)에서 가져옵니다. 법령을 추가하는 순서는 다음과 같습니다.

1. `LAWS`(약칭 → gesetze-im-internet.de 주소)와 `CORPUS`에 추가합니다. 다루는 분야가 바뀌면 `TOPIC`과 `OUT_OF_SCOPE`도 고칩니다.
2. 받고, 파싱하고, 인덱스를 다시 만듭니다.

```bash
python gii_parser.py fetch
```

```bash
python gii_parser.py parse
```

```bash
python retrieval.py build --store chroma
```

3. 평가를 다시 돌려 이전 코퍼스와 비교합니다.

AsylG가 이 방식으로 추가한 첫 법령입니다. 받은 본문은 2024년 EU 망명제도 개혁(2026년 6월 시행) 이후 버전이라, 청크 374개 중 86개가 EU 규정 2024/1347, 2024/1348, 2024/1351을 가리킵니다. 이 규정들은 gesetze-im-internet.de에 없어서 코퍼스에도 없습니다. 답변 프롬프트는 이 경우 세부 내용을 지어내지 말고 EU 규정에 있다고 밝히도록 되어 있습니다.

## 로드맵

**외국인 관련 세법.** 다음 코퍼스 확장은 외국인이 흔히 겪는 세금 문제를 다룹니다. 언제 독일에서 납세 의무가 생기는지, 제한 납세 의무에서 소득이 어떻게 과세되는지, 이중과세를 어떻게 피하는지 같은 질문입니다. 후보는 소득세법(EStG)과 조세기본법(AO)이며, 둘 다 지금 코퍼스와 같은 XML 형식으로 gesetze-im-internet.de에 있습니다. 이중과세방지협정은 따로 공표되므로 별도의 수집 단계가 필요합니다.

필요한 작업은 다음과 같습니다.
- [laws.py](laws.py)에 EStG와 AO 추가 ([법령 추가하기](#법령-추가하기) 참고)
- 평가셋에 세금 질문 추가 (single, multi, refusal, 모든 세트). 세금은 국적이 더 중요합니다(예: 이중과세방지협정이 나라마다 다름)
- 거절 규칙을 개인 체류 판단에서 개인 세액 판단까지 확장

**그 밖의 계획**
- 참조된 조항의 제목을 각 청크와 함께 색인해서, "§ 25 Absatz 2"처럼 번호로만 가리키는 조항도 찾을 수 있게 하기 (난민 모듈 분석 참고)
- EUR-Lex의 EU 망명 규정(2024/1347, 2024/1348, 2024/1351) 추가 (별도 파서 필요)
- `rewrite`, `agent` 조건 결과를 검색 기준선과 함께 보고
- EU 시민 적용 범위 확인 단계 (위 분석 참고)
- 앱의 기본 화면 언어를 바꾸는 설정 (예: 터키어, 아랍어, 이탈리아어, 한국어). 독일어 병기는 기본으로 유지
- 평가셋 정답 조항 검증, 터키어·아랍어·이탈리아어 번역 원어민 검토
- 체류령(AufenthV) 추가 (파서는 이미 지원)

## 테스트

```bash
python -m pytest -q
```

테스트는 가짜 임베더를 쓰기 때문에 bge-m3 모델이나 API 키 없이 돌아갑니다.

## 면책 고지

GesetzPolyglot은 독일 법령 이해를 돕기 위한 연구용 시제품이며, 참고용으로만 사용해야 합니다.

- **자문이 아닙니다.** 일반적인 법률 정보를 제공할 뿐, 법률·세무 자문이 아닙니다. 외국인청, 연방이민난민청(BAMF), 망명 절차 상담, 변호사, 세무사를 대신하지 않으며 개인의 사안을 판단하지 않습니다.
- **망명 절차의 기한은 짧습니다.** 망명 절차에서 결정문을 받았다면 바로 상담을 받으세요. 기한이 1–2주인 경우도 있습니다.
- **답변이 틀릴 수 있습니다.** 답변은 언어 모델이 자동으로 생성합니다. 조문을 인용하고 인용 검증을 통과하더라도 불완전하거나 최신이 아니거나 틀릴 수 있습니다. 사용한 법령 스냅샷 날짜는 답변마다 표시됩니다.
- **원문을 확인하세요.** 인용된 원문을 gesetze-im-internet.de에서 반드시 확인하고, 개인 사안은 자격 있는 전문가와 상담하세요.
- **책임을 지지 않습니다.** 법이 허용하는 범위에서, 작성자는 이 답변에 근거한 결정이나 행동, 답변에 대한 과도한 신뢰, 이 소프트웨어의 오용에 대해 책임을 지지 않습니다. 이 소프트웨어는 어떠한 보증도 없이 "있는 그대로" 제공됩니다.

같은 고지가 웹 앱에도 표시되며, 모든 답변 끝에는 질문 언어로 된 짧은 고지가 붙습니다.

## git에 올라가지 않는 것

`data/index/`(임베딩과 Chroma 포함), `results/`, `.env`, `.venv/`는 `.gitignore`에 있습니다. 저장소를 받은 사람은 위의 1–2단계로 데이터와 인덱스를 다시 만들면 됩니다.
