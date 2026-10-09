#!/usr/bin/env python3
"""Single-pass RAG over the statutes in laws.CORPUS: retrieve -> generate -> validate citations.

    python rag.py "Kann ich als Student in Deutschland arbeiten?"
    python rag.py "유학생도 일할 수 있나요?" --condition rewrite

Conditions (plan section 5):
    dense    1. dense retrieval, single pass
    hybrid   2. BM25 + dense (RRF), single pass
    rewrite  3. hybrid + LLM rewrite of the question into German legal queries
    agent    4. LangGraph agent: plan sub-questions, retrieve, follow cross_refs,
                check sufficiency, retry up to 2x (see agent.py)

LLM is configured by environment variables or a .env file next to this script:
    OPENAI_API_KEY
    LLM_PROVIDER         = openai (default) | anthropic
    LLM_MODEL            = default gpt-5.4-nano (openai) / claude-sonnet-5-5 (anthropic)
    LLM_REASONING_EFFORT = low (default) | none | medium | high ; empty = do not send
    OPENAI_BASE_URL      = only for compatible servers, e.g. http://localhost:11434/v1 (Ollama)
"""
from __future__ import annotations

import argparse
import json
import os
import re
import time
from pathlib import Path
from typing import Protocol

from laws import CORPUS, LAWS, OUT_OF_SCOPE, TOPIC, corpus_names
from retrieval import RRF_K, LawIndex, cite

# Bump when REWRITE_SYSTEM / ANSWER_SYSTEM / agent prompts change, so eval results say which version they used.
PROMPT_VERSION = "v2"  # v1 texts: results/prompts_v1.txt

CONDITIONS = ("dense", "hybrid", "rewrite")
STATUSES = ("answer", "refuse_out_of_scope", "explain_without_judgment")


# --------------------------------------------------------------------------
# LLM clients
# --------------------------------------------------------------------------
class LLM(Protocol):
    name: str

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str: ...


class AnthropicLLM:
    def __init__(self, model: str):
        import anthropic
        self.name, self.client = model, anthropic.Anthropic()
        self.usage = {"input_tokens": 0, "output_tokens": 0}  # running total, for cost reports

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str:
        r = self.client.messages.create(model=self.name, max_tokens=max_tokens, temperature=0,
                                        system=system, messages=[{"role": "user", "content": user}])
        self.usage["input_tokens"] += r.usage.input_tokens
        self.usage["output_tokens"] += r.usage.output_tokens
        return "".join(b.text for b in r.content if b.type == "text")


class OpenAICompatLLM:
    """OpenAI API (or any compatible server such as Ollama / vLLM).

    GPT-5-family models reject `temperature` and `max_tokens` and spend part of the token
    budget on hidden reasoning. We send the modern parameters and, if the server rejects
    one, drop or rename it once and remember that for later calls.
    """

    def __init__(self, model: str, base_url: str | None = None, reasoning_effort: str | None = None):
        from openai import OpenAI
        self.name = model
        self.client = OpenAI(base_url=base_url)  # reads OPENAI_API_KEY
        self.extra: dict = {"temperature": 0}
        if reasoning_effort:
            self.extra["reasoning_effort"] = reasoning_effort
        self.limit_key = "max_completion_tokens"
        # running total, for cost reports; output includes hidden reasoning tokens
        self.usage = {"input_tokens": 0, "output_tokens": 0, "reasoning_tokens": 0}

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str:
        import openai
        messages = [{"role": "system", "content": system}, {"role": "user", "content": user}]
        # reasoning tokens count against the limit, so leave headroom
        budget = max_tokens * 4 if "reasoning_effort" in self.extra else max_tokens
        for _ in range(4):
            try:
                r = self.client.chat.completions.create(
                    model=self.name, messages=messages, **{self.limit_key: budget}, **self.extra)
                usage = getattr(r, "usage", None)  # compatible servers may omit it
                if usage:
                    self.usage["input_tokens"] += usage.prompt_tokens or 0
                    self.usage["output_tokens"] += usage.completion_tokens or 0
                    details = getattr(usage, "completion_tokens_details", None)
                    self.usage["reasoning_tokens"] += getattr(details, "reasoning_tokens", 0) or 0
                return r.choices[0].message.content or ""
            except openai.BadRequestError as e:
                msg = str(e)
                if "temperature" in msg and "temperature" in self.extra:
                    self.extra.pop("temperature")
                elif "reasoning_effort" in msg and "reasoning_effort" in self.extra:
                    self.extra.pop("reasoning_effort")
                elif "max_completion_tokens" in msg and self.limit_key == "max_completion_tokens":
                    self.limit_key = "max_tokens"
                else:
                    raise
        raise RuntimeError("OpenAI request kept failing after parameter fallbacks")


def load_dotenv(path: Path | None = None) -> None:
    """Read KEY=VALUE lines from .env (next to this file) into os.environ.
    Variables already set in the shell win. No extra dependency needed."""
    path = path or Path(__file__).resolve().parent / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.removeprefix("export ").split("=", 1)
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
            val = val[1:-1]
        elif " #" in val:
            val = val.split(" #", 1)[0].rstrip()
        os.environ.setdefault(key.strip(), val)


def llm_from_env() -> LLM:
    load_dotenv()
    provider = os.environ.get("LLM_PROVIDER", "openai").lower()
    if provider == "openai":
        if not os.environ.get("OPENAI_API_KEY") and not os.environ.get("OPENAI_BASE_URL"):
            raise SystemExit("OPENAI_API_KEY is not set: put it in the .env file (see .env.example)")
        return OpenAICompatLLM(os.environ.get("LLM_MODEL", "gpt-5.4-nano"),
                               os.environ.get("OPENAI_BASE_URL"),
                               os.environ.get("LLM_REASONING_EFFORT", "low") or None)
    if provider == "anthropic":
        return AnthropicLLM(os.environ.get("LLM_MODEL", "claude-sonnet-5-5"))
    raise SystemExit(f"unknown LLM_PROVIDER: {provider}")


class CountingLLM:
    """Wraps an LLM to count calls per question (reported as a metric)."""

    def __init__(self, inner: LLM):
        self.inner, self.name, self.calls = inner, inner.name, 0

    def complete(self, system: str, user: str, max_tokens: int = 1200) -> str:
        self.calls += 1
        return self.inner.complete(system, user, max_tokens)


# --------------------------------------------------------------------------
# Language detection (rule-based: deterministic and free)
# --------------------------------------------------------------------------
_DE_WORDS = re.compile(r"\b(ich|und|nicht|kann|darf|muss|eine?n?|der|die|das|wie|wird|für|nach|"
                       r"bei|mit|oder|wenn|als|auf|ist|sind|habe|bekomme)\b", re.I)


_TR_WORDS = re.compile(r"\b(mi|mı|mu|mü|miyim|mıyım|ve|bir|için|ile|ne|nasıl|var|yok|değil|olarak)\b", re.I)

_IT_WORDS = re.compile(r"\b(il|lo|la|gli|di|del|della|che|non|per|posso|devo|può|sono|un|una|con|come|quando|"
                       r"dopo|prima|mentre|solo|anche|mio|mia|mi|ho|è|cosa|quali?|quanti?)\b"
                       r"|\b(?:l|all|dell|nell|dall|un)'", re.I)  # also elided articles: l'ufficio


def detect_lang(text: str) -> str:
    if re.search(r"[가-힣]", text):
        return "ko"
    if re.search(r"[\u0600-\u06FF]", text):
        return "ar"
    words = max(len(text.split()), 1)
    # before German: Turkish shares ö/ü, and questions often quote German terms (Ausländerbehörde)
    if re.search(r"[ğışĞŞİ]", text) or len(_TR_WORDS.findall(text)) / words > 0.15:
        return "tr"
    # also before German, for the same reason: quoted German terms carry umlauts
    if len(_IT_WORDS.findall(text)) / words > 0.15:
        return "it"
    if re.search(r"[äöüß]", text, re.I) or len(_DE_WORDS.findall(text)) / words > 0.15:
        return "de"
    return "en"


# --------------------------------------------------------------------------
# Prompts
# --------------------------------------------------------------------------
REWRITE_SYSTEM = f"""You turn a user's question about German {TOPIC} into search \
queries for a retriever over the German statutes {corpus_names()}.
Write 1 to 3 short German queries using the statutory terminology (e.g. "Aufenthaltserlaubnis \
zum Zweck des Studiums Beschäftigung Arbeitstage" rather than "Studentenjob"). One query per \
distinct legal sub-question. Do not answer the question.
If the user says they are a citizen of an EU/EEA country or Switzerland, add one query about \
whether the Residence Act applies to them, e.g. "Anwendungsbereich Aufenthaltsgesetz Unionsbürger \
Freizügigkeitsgesetz".
Return only JSON: {{"queries": ["...", "..."]}}"""

ANSWER_SYSTEM = f"""You answer questions about German {TOPIC} ({', '.join(CORPUS)}) \
for foreigners, using ONLY the statute excerpts provided.

Rules:
1. Reply in {{lang_name}}. Keep German legal terms in parentheses where helpful, e.g. 정주허가(Niederlassungserlaubnis).
2. Every factual statement must be backed by an excerpt and cited right after it in exactly this \
form: [AufenthG § 18a Abs. 1] or [BeschV § 26]. Cite only labels that appear in the excerpts.
3. Check scope first. If the user is a citizen of an EU/EEA country or Switzerland, the Residence \
Act largely does not apply to them (AufenthG § 1 Abs. 2 Nr. 1, if in the excerpts): say so, say \
that the Freedom of Movement Act governs their case and is not in the excerpts, use \
refuse_out_of_scope, and do not explain residence permits as if they needed one.
4. If the question is about another area of law ({OUT_OF_SCOPE}, ...), or the excerpts contain \
nothing relevant, say that this is outside what you can answer from {'/'.join(CORPUS)} \
(refuse_out_of_scope). If the excerpts answer only part of the question, answer that part, \
say what is missing, and use answer. Do not answer from general knowledge.
5. Choosing the status: use explain_without_judgment ONLY when the user asks you to predict or \
decide their own case (will I get the permit, will I win, is the decision against me lawful). \
A question about the rules is answer, even in the first person ("Can I work while ...", \
"How long until I can ...").
6. Read each provision's scope exactly: which Absatz and Satz, and which group or which permit \
holders it names. A rule for holders of one permit or status does not cover holders of another \
one mentioned in a different Satz. Never apply a rule to a group it does not name. If a provision lists countries or groups and the user's is not among \
them, say so explicitly: that is an answer, not a refusal.
7. If the question rests on a wrong assumption, say so and state what the excerpts actually require.
8. Asylum procedure: if the user asks about a deadline, an ongoing procedure or a decision in \
their own case, explain the relevant rules with citations but do not judge the case, and tell them \
to contact asylum procedure counselling (Asylverfahrensberatung) or a lawyer right away, because \
deadlines can be very short.
9. Many AsylG provisions refer to EU Regulations (EU) 2024/1347, 2024/1348 or 2024/1351. Their text \
is not in the excerpts: say that the details are in the EU regulation instead of filling them in \
from general knowledge.
10. Be concise: 2 to 6 sentences, or a short list of requirements.

Start your reply with exactly one status line, then a blank line, then the answer:
STATUS: answer | refuse_out_of_scope | explain_without_judgment"""

LANG_NAMES = {"ko": "Korean", "en": "English", "de": "German", "tr": "Turkish", "ar": "Arabic", "it": "Italian"}

FOOTER = {
    "ko": "법령 기준: {stand}\n이 답변은 법률 정보이며 법률 자문이 아닙니다. 개인 사정은 외국인청(Ausländerbehörde)이나 전문가에게 확인하세요.\n참고용으로만 사용하세요. 이 답변을 과신하거나 오용해 생긴 결과에 대해 작성자는 책임지지 않습니다.",
    "en": "Legal basis as of: {stand}\nThis is legal information, not legal advice. For your individual case, ask the Ausländerbehörde or a qualified advisor.\nUse it as an aid only. The author accepts no liability for overreliance on or misuse of this answer.",
    "de": "Rechtsstand: {stand}\nDies ist eine allgemeine Rechtsinformation, keine Rechtsberatung. Für Ihren Einzelfall wenden Sie sich an die Ausländerbehörde oder eine Beratungsstelle.\nNur als Hilfestellung gedacht. Für übermäßiges Vertrauen in diese Antwort oder ihre missbräuchliche Verwendung wird keine Haftung übernommen.",
    "tr": "Hukuki dayanak tarihi: {stand}\nBu yanıt hukuki bilgi niteliğindedir, hukuki danışmanlık değildir. Kişisel durumunuz için yabancılar dairesine (Ausländerbehörde) veya bir uzmana danışın.\nYalnızca yardımcı bilgi olarak kullanın. Bu yanıta aşırı güvenilmesinden veya kötüye kullanılmasından doğan sonuçlardan geliştirici sorumlu değildir.",
    "it": "Base giuridica aggiornata al: {stand}\nQuesta risposta è un'informazione giuridica, non una consulenza legale. Per il tuo caso specifico rivolgiti all'ufficio stranieri (Ausländerbehörde) o a un consulente qualificato.\nDa usare solo come supporto. L'autore non si assume alcuna responsabilità per un affidamento eccessivo su questa risposta o per un suo uso improprio.",
    "ar": "الأساس القانوني بتاريخ: {stand}\nهذه الإجابة معلومات قانونية وليست استشارة قانونية. للاستفسار عن حالتك الشخصية، راجع دائرة الأجانب (Ausländerbehörde) أو مختصاً مؤهلاً.\nاستخدمها كوسيلة مساعدة فقط. لا يتحمل المطوّر أي مسؤولية عن الاعتماد المفرط على هذه الإجابة أو إساءة استخدامها.",
}


def format_excerpts(chunks: list[dict]) -> str:
    return "\n\n".join(f"[{cite(c)}] {c.get('title', '')}\n{c['text']}" for c in chunks)


# --------------------------------------------------------------------------
# Parsing model output
# --------------------------------------------------------------------------
CITE_RE = re.compile(r"\[\s*(" + "|".join(map(re.escape, LAWS)) + r")\s*§\s*(\d+[a-z]?)"
                     r"(?:\s*(?:Abs\.|Absatz)\s*(\d+[a-z]?))?[^\]]*\]")
STATUS_RE = re.compile(r"^\s*STATUS:\s*([a-z_]+)\s*\n+", re.I)


def parse_status(raw: str) -> tuple[str, str]:
    m = STATUS_RE.match(raw)
    if m and m.group(1).lower() in STATUSES:
        return m.group(1).lower(), raw[m.end():].strip()
    return "answer", STATUS_RE.sub("", raw, count=1).strip()


def parse_queries(raw: str) -> list[str]:
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        qs = json.loads(m.group()).get("queries", []) if m else []
    except json.JSONDecodeError:
        qs = []
    return [q.strip() for q in qs if isinstance(q, str) and q.strip()][:3]


def validate_citations(text: str, retrieved: list[dict]) -> tuple[list[str], list[str]]:
    """A citation is valid if it points to a retrieved chunk. "§ 18a" without Absatz is valid
    if any Absatz of § 18a was retrieved; "§ 18a Abs. 2" needs exactly that Absatz."""
    have = {(c["law"], c["section"], c["absatz"]) for c in retrieved}
    secs = {(c["law"], c["section"]) for c in retrieved}
    valid, invalid = [], []
    for law, sec, absatz in CITE_RE.findall(text):
        label = f"{law} § {sec}" + (f" Abs. {absatz}" if absatz else "")
        ok = (law, sec, absatz) in have if absatz else (law, sec) in secs
        bucket = valid if ok else invalid
        if label not in bucket:
            bucket.append(label)
    return valid, invalid


def stand_line(chunks: list[dict]) -> str:
    seen = {}
    for c in chunks:
        stand = f" ({c['stand']})" if c.get("stand") else ""
        seen.setdefault(c["law"], f"{c['law']} {c.get('snapshot', '?')}{stand}")
    return "; ".join(seen.values()) or "—"


# --------------------------------------------------------------------------
# Pipeline
# --------------------------------------------------------------------------
class RAG:
    def __init__(self, index: LawIndex, llm: LLM, k: int = 8):
        self.index, self.llm, self.k = index, llm, k

    def _retrieve(self, question: str, condition: str, llm: LLM, trace: list) -> list[dict]:
        if condition == "dense":
            return self.index.search(question, self.k, mode="dense")
        if condition == "hybrid":
            return self.index.search(question, self.k, mode="hybrid")
        # rewrite: search each German query, fuse the rankings with RRF
        queries = parse_queries(llm.complete(REWRITE_SYSTEM, question, max_tokens=300)) or [question]
        trace.append({"step": "rewrite", "queries": queries})
        score, by_id = {}, {}
        for q in queries:
            for h in self.index.search(q, self.k, mode="hybrid"):
                by_id[h["id"]] = h
                score[h["id"]] = score.get(h["id"], 0.0) + 1.0 / (RRF_K + h["rank"])
        top = sorted(score, key=score.get, reverse=True)[: self.k]
        return [{**by_id[i], "rank": r + 1} for r, i in enumerate(top)]

    def answer(self, question: str, condition: str = "rewrite") -> dict:
        if condition == "agent":
            from agent import run_agent  # condition 4 lives in agent.py (LangGraph)
            return run_agent(self, question)
        if condition not in CONDITIONS:
            raise ValueError(f"condition must be one of {CONDITIONS + ('agent',)}")
        t0, llm, trace = time.time(), CountingLLM(self.llm), []
        lang = detect_lang(question)
        trace.append({"step": "detect_lang", "lang": lang})

        retrieved = self._retrieve(question, condition, llm, trace)
        trace.append({"step": "retrieve", "mode": condition, "hits": [cite(c) for c in retrieved]})
        return finish(question, lang, retrieved, llm, trace, condition, t0, self.llm.name)


def finish(question: str, lang: str, retrieved: list[dict], llm: "CountingLLM", trace: list,
           condition: str, t0: float, model: str) -> dict:
    """Shared last step for ALL conditions: same answer prompt, same citation check,
    same result dict. Keeping this identical is what makes the comparison fair."""
    system = ANSWER_SYSTEM.replace("{lang_name}", LANG_NAMES[lang])
    user = f"Statute excerpts:\n\n{format_excerpts(retrieved)}\n\nQuestion: {question}"
    status, body = parse_status(llm.complete(system, user))
    valid, invalid = validate_citations(body, retrieved)
    trace.append({"step": "validate", "valid": valid, "invalid": invalid})

    stand = stand_line(retrieved)
    return {
        "answer": body,
        "footer": FOOTER[lang].format(stand=stand),
        "status": status,
        "citations": valid,
        "invalid_citations": invalid,
        "retrieved": [{k: c.get(k) for k in ("id", "law", "section", "absatz", "title",
                                             "text", "source_url", "rank", "via")}
                      for c in retrieved],
        "stand": stand,
        "lang": lang,
        "condition": condition,
        "trace": trace,
        "llm_calls": llm.calls,
        "latency_s": round(time.time() - t0, 2),
        "model": model,
    }


_PIPELINE: RAG | None = None


def answer(question: str, condition: str = "rewrite", index_dir: str | Path = "data/index") -> dict:
    """Entry point for eval scripts and the Gradio app. Loads index + model once."""
    global _PIPELINE
    if _PIPELINE is None:
        _PIPELINE = RAG(LawIndex.load(Path(index_dir)), llm_from_env())
    return _PIPELINE.answer(question, condition)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("question")
    ap.add_argument("--condition", default="rewrite", choices=CONDITIONS + ("agent",))
    ap.add_argument("--index", default="data/index")
    ap.add_argument("--json", action="store_true", help="print the full result dict")
    args = ap.parse_args()
    r = answer(args.question, args.condition, args.index)
    if args.json:
        print(json.dumps(r, ensure_ascii=False, indent=2))
        return
    print(f"[{r['status']}] {r['lang']} · {r['condition']} · {r['llm_calls']} LLM calls · {r['latency_s']}s\n")
    print(r["answer"], "\n\n" + r["footer"])
    if r["invalid_citations"]:
        print("\n! citations not in retrieved excerpts:", ", ".join(r["invalid_citations"]))
    print("\nretrieved:", ", ".join(cite(c) for c in r["retrieved"]))


if __name__ == "__main__":
    main()
