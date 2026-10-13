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
SUPPORTED_LANGS = ("ko", "en", "de", "it", "ar")  # the languages the evaluation set covers

# Function words per language. Only en, de and it are supported among Latin-script languages; the
# others are listed so that a French or Spanish question is recognised as such and not taken for English.
_WORDS = {
    "en": "the a an i my me you your is are am was can could do does did have has had to of in on at for and or "
          "if what how when which who will would should be it this that with from after before while get need "
          "still also any much many long not there they we our as by than so my",
    "de": "ich und nicht kann darf muss ein eine einen einem einer der die das den dem des wie wird werden für "
          "nach bei mit oder wenn als auf ist sind habe hat bekomme mein meine meinen bin noch auch schon was wo "
          "warum wann welche welcher zu zum zur in im vom von aus über ohne man sich mich mir es",
    "it": "il lo la i gli le l un una uno di del della dei delle degli dello al alla allo ai alle all dell nell "
          "dall sull che non per posso puoi può possono devo deve devono sono è ho ha hanno mi ti si ci con come "
          "quando dopo prima mentre solo anche mio mia miei mie cosa quali quale quanti quanto quante senza e o "
          "ma se dove perché nel nella negli ancora in possiamo essere vorrei",
    "fr": "le la les des du de est sont je j peux peut peuvent ils elles et pour avec dans une un que qui pas "
          "ne mon ma mes au aux ce cette être avoir quand comment pourquoi",
    "es": "el la los las del de es son puedo puede pueden y para con una un que no mi mis al por cómo cuánto "
          "qué cuándo estoy tengo hay sin pero",
    "pt": "o a os as do da dos das é são posso pode podem em e para com uma um que não meu minha no na como "
          "quando eu tenho sem mas",
    "nl": "de het een en ik is zijn kan mag moet van voor met niet wat hoe wanneer mijn ook nog in als werken",
    "pl": "i w z na się nie jest są czy mogą może do jak co dla mój moja jestem mam",
    "tr": "ve bir için ile ne nasıl var yok değil olarak mi mı mu mü miyim mıyım ben benim",
}
_WORDS = {lang: set(ws.split()) for lang, ws in _WORDS.items()}
_TOKEN_RE = re.compile(r"[^\W\d_]+")
# letters of scripts we do not support (CJK, kana, Cyrillic, Greek, Hebrew, Devanagari, Thai, ...)
_OTHER_SCRIPT = re.compile(r"[^\W\d_a-zA-Z\u00C0-\u024F\uAC00-\uD7A3\u1100-\u11FF\u3130-\u318F\u0600-\u06FF\u0750-\u077F]")
_PERSIAN_URDU = re.compile(r"[پچژگٹڈڑںےکیۀ]")  # Arabic script, but not Arabic
_TURKISH = re.compile(r"[ğışĞŞİ]")


def detect_lang(text: str) -> str | None:
    """One of SUPPORTED_LANGS, or None for a language we do not support (the caller then asks the user
    to rephrase instead of answering in a guessed language). Rule-based: deterministic and free."""
    if re.search(r"[가-힣]", text):
        return "ko"
    if re.search(r"[\u0600-\u06FF]", text):
        return None if _PERSIAN_URDU.search(text) else "ar"
    if _OTHER_SCRIPT.search(text) or _TURKISH.search(text):
        return None
    tokens = _TOKEN_RE.findall(text.lower())
    if not tokens:
        return None
    score = {lang: sum(t in ws for t in tokens) / len(tokens) for lang, ws in _WORDS.items()}
    # German compounds quoted in other languages (Ausländerbehörde) carry umlauts, so umlauts only add a little
    score["de"] += 0.5 * sum(any(ch in t for ch in "äöüß") for t in tokens) / len(tokens)
    best = max(score, key=score.get)
    if score[best] == 0:  # keywords only ("Blue Card salary"): no sentence to judge, answer in English
        return "en"
    return best if best in SUPPORTED_LANGS and score[best] >= 0.15 else None


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
        if condition not in CONDITIONS + ("agent",):
            raise ValueError(f"condition must be one of {CONDITIONS + ('agent',)}")
        t0, llm, trace = time.time(), CountingLLM(self.llm), []
        lang = detect_lang(question)
        trace.append({"step": "detect_lang", "lang": lang})
        if lang is None:  # unsupported language: ask the user to rephrase, before any LLM call
            return unsupported_language(question, condition, trace, t0, self.llm.name)
        if condition == "agent":
            from .agent import run_agent  # condition 4 lives in agent.py (LangGraph)
            return run_agent(self, question)

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


UNSUPPORTED_MESSAGE = (
    "Sorry, this language is not supported yet. Please ask in Korean, English, German, Italian or Arabic "
    "(Modern Standard or Syrian dialect).\n\n"
    "Diese Sprache wird noch nicht unterstützt. Bitte fragen Sie auf Koreanisch, Englisch, Deutsch, Italienisch "
    "oder Arabisch (Hocharabisch oder syrischer Dialekt).")


def unsupported_language(question: str, condition: str, trace: list, t0: float, model: str) -> dict:
    """Result for a question in a language we do not support: no retrieval, no LLM call."""
    return {"answer": UNSUPPORTED_MESSAGE, "footer": "", "status": "unsupported_language", "citations": [],
            "invalid_citations": [], "retrieved": [], "stand": "", "lang": None, "condition": condition,
            "trace": trace, "llm_calls": 0, "latency_s": round(time.time() - t0, 2), "model": model}


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
