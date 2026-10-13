#!/usr/bin/env python3
"""Single-pass RAG over the statutes in laws.CORPUS: retrieve -> generate -> validate citations.

    python -m gesetzpolyglot.rag "Kann ich als Student in Deutschland arbeiten?"
    python -m gesetzpolyglot.rag "유학생도 일할 수 있나요?" --condition rewrite
    python -m gesetzpolyglot.rag "유학생도 일할 수 있나요?" --provider ollama    # local model via Ollama

Conditions:
    dense    1. dense retrieval, single pass
    hybrid   2. BM25 + dense (RRF), single pass
    rewrite  3. hybrid + LLM rewrite of the question into German legal queries
    agent    4. LangGraph agent: plan sub-questions, retrieve, follow cross_refs,
                check sufficiency, retry up to 2x (see agent.py)

The LLM is chosen with --provider / --model, environment variables or .env (see llm.py);
the prompts live in prompts.py.
"""
from __future__ import annotations

import argparse
import json
import re
import time
from pathlib import Path

from .laws import LAWS
from .llm import LLM, CountingLLM, add_llm_args, apply_llm_args, llm_from_env
from .prompts import ANSWER_SYSTEM, FOOTER, LANG_NAMES, REWRITE_SYSTEM
from .retrieval import RRF_K, LawIndex, cite

CONDITIONS = ("dense", "hybrid", "rewrite")
STATUSES = ("answer", "refuse_out_of_scope", "explain_without_judgment")


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


def format_excerpts(chunks: list[dict]) -> str:
    return "\n\n".join(f"[{cite(c)}] {c.get('title', '')}\n{c['text']}" for c in chunks)


# --------------------------------------------------------------------------
# Parsing model output
# --------------------------------------------------------------------------
CITE_RE = re.compile(r"\[\s*(" + "|".join(map(re.escape, LAWS)) + r")\s*§\s*(\d+[a-z]?)"
                     r"(?:\s*(?:Abs\.|Absatz)\s*(\d+[a-z]?))?[^\]]*\]")
STATUS_RE = re.compile(r"^\s*STATUS:([^\n]*)\n*", re.I)


def parse_status(raw: str) -> tuple[str, str]:
    """The first line must name exactly one status. Anything else (no line, an unknown word, or the
    template copied as "answer | refuse_out_of_scope") is "unclear", so evaluation counts it as wrong."""
    m = STATUS_RE.match(raw)
    if not m:
        return "unclear", raw.strip()
    named = [s for s in STATUSES if re.search(rf"\b{s}\b", m.group(1).lower())]
    return (named[0] if len(named) == 1 else "unclear"), raw[m.end():].strip()


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
            from .agent import run_agent  # condition 4 lives in agent.py (LangGraph)
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
    add_llm_args(ap)
    args = ap.parse_args()
    apply_llm_args(args)
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
