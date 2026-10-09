"""Condition 4: agentic retrieval as a LangGraph state machine.

    plan ──► retrieve ──► follow_refs ──► check ──► answer ──► END
                ▲                           │
                └──── not sufficient ───────┘   (at most MAX_RETRIES extra rounds)

plan         one LLM call: split the question into sub-questions, one German query each
retrieve     hybrid search for every pending query, fused with RRF into one shared pool
follow_refs  no LLM: read the cross_refs of the best chunks and pull the cited Absätze in
check        one LLM call: can every sub-question be answered from the pool?
             if not, it names German queries for what is missing -> back to retrieve
answer       rag.finish(): the SAME prompt and citation check as conditions 1-3

Usage: rag.answer(question, "agent"), or RAG(...).answer(question, "agent").
"""
from __future__ import annotations

import json
import re
import time
from typing import TypedDict

import numpy as np
from langgraph.graph import END, START, StateGraph

from laws import CORPUS, OUT_OF_SCOPE, corpus_names
from rag import RRF_K, CountingLLM, detect_lang, finish
from retrieval import cite

K_PER_QUERY = 5      # hits per search query
CONTEXT_K = 12       # chunks handed to the answer step
REF_SOURCES = 6      # follow cross_refs of this many top chunks
MAX_NEW_REFS = 6     # at most this many chunks added via cross_refs per round
SECTION_REF_TOP = 2  # a ref to a whole § brings in its 2 most relevant Absätze
MAX_RETRIES = 2      # extra retrieve rounds after the first
CORPUS_LAWS = set(CORPUS)

PLAN_SYSTEM = f"""You prepare retrieval over the German statutes {corpus_names()}.
Split the user's question into 1 to 3 legal sub-questions (in English). For each, write one short \
German search query using statutory terminology (e.g. "Niederlassungserlaubnis Blaue Karte EU \
Monate" rather than "permanent residence").
If the user says they are a citizen of an EU/EEA country or Switzerland, add one query about \
whether the Residence Act applies to them, e.g. "Anwendungsbereich Aufenthaltsgesetz Unionsbürger \
Freizügigkeitsgesetz".
Return only JSON: {{"sub_questions": ["...", "..."], "queries": ["...", "..."]}}"""

CHECK_SYSTEM = f"""You check whether retrieved statute excerpts are enough to answer some sub-questions.
For each sub-question decide whether the excerpts contain the rule that answers it.
If something is missing, give up to 2 short German search queries for exactly the missing rule.
If the question is about a field these statutes do not cover ({OUT_OF_SCOPE}, ...), \
more searching will not help: answer sufficient = true.
Return only JSON: {{"sufficient": true or false, "missing_queries": ["..."]}}"""


class AgentState(TypedDict, total=False):
    question: str
    lang: str
    sub_questions: list[str]
    pending: list[str]           # queries to run in the next retrieve
    queries_done: list[str]      # all German queries searched so far
    scores: dict[str, float]     # chunk id -> fused score
    via: dict[str, str]          # chunk id -> how it entered the pool
    retries: int
    sufficient: bool
    trace: list[dict]
    t0: float
    result: dict


def _json(raw: str) -> dict:
    m = re.search(r"\{.*\}", raw, re.S)
    try:
        return json.loads(m.group()) if m else {}
    except json.JSONDecodeError:
        return {}


def _strings(x, n: int) -> list[str]:
    return [s.strip() for s in (x if isinstance(x, list) else []) if isinstance(s, str) and s.strip()][:n]


def build_graph(rag, llm: CountingLLM | None, question: str = ""):
    index = rag.index
    pos = {c["id"]: i for i, c in enumerate(index.chunks)}
    qvec: dict[str, np.ndarray] = {}  # embedding cache for ranking Absätze inside a §

    def top_ids(state: AgentState, n: int) -> list[str]:
        return sorted(state["scores"], key=state["scores"].get, reverse=True)[:n]

    # ---- nodes ----------------------------------------------------------------
    def plan(state: AgentState) -> dict:
        out = _json(llm.complete(PLAN_SYSTEM, state["question"], max_tokens=400))
        subs = _strings(out.get("sub_questions"), 3) or [state["question"]]
        queries = _strings(out.get("queries"), 3) or [state["question"]]
        step = {"step": "plan", "sub_questions": subs, "queries": queries}
        return {"sub_questions": subs, "pending": queries, "trace": state["trace"] + [step]}

    def retrieve(state: AgentState) -> dict:
        scores, via = dict(state["scores"]), dict(state["via"])
        new = []
        for q in state["pending"]:
            for h in index.search(q, K_PER_QUERY, mode="hybrid"):
                if h["id"] not in scores:
                    new.append(cite(h))
                    via[h["id"]] = f"search: {q}"
                scores[h["id"]] = scores.get(h["id"], 0.0) + 1.0 / (RRF_K + h["rank"])
        step = {"step": "retrieve", "round": state["retries"], "queries": state["pending"], "new": new}
        return {"scores": scores, "via": via, "pending": [],
                "queries_done": state["queries_done"] + state["pending"],
                "trace": state["trace"] + [step]}

    def section_best(law: str, section: str, rank_text: str) -> list[str]:
        """A ref to a whole § pulls in its Absätze closest to the German queries."""
        idxs = index.by_sec.get((law.lower(), section), [])
        if len(idxs) <= SECTION_REF_TOP:
            return [index.chunks[i]["id"] for i in idxs]
        if rank_text not in qvec:
            qvec[rank_text] = index.embedder.encode([rank_text])[0]
        sims = index.emb[idxs] @ qvec[rank_text]
        return [index.chunks[idxs[i]]["id"] for i in np.argsort(-sims)[:SECTION_REF_TOP]]

    def follow_refs(state: AgentState) -> dict:
        scores, via = dict(state["scores"]), dict(state["via"])
        candidates: list[tuple[str, str]] = []  # (target id, source id), best sources first
        rank_text = " ".join(state["queries_done"]) or question
        for src in top_ids(state, REF_SOURCES):
            for r in index.chunks[pos[src]].get("cross_refs", []):
                if r["status"] != "ok" or r["law"] not in CORPUS_LAWS:
                    continue
                if r["absatz"]:
                    targets = [f"{r['law']}-{r['section']}-{r['absatz']}"]
                else:
                    targets = section_best(r["law"], r["section"], rank_text)
                candidates += [(t, src) for t in targets if t in pos]
        added = []
        for tgt, src in candidates:
            if len(added) >= MAX_NEW_REFS:
                break
            if tgt in scores:
                continue
            scores[tgt] = 0.5 * scores[src]  # ranks below its source, but enters the context
            via[tgt] = f"cross-ref from {cite(index.chunks[pos[src]])}"
            added.append({"chunk": cite(index.chunks[pos[tgt]]), "from": cite(index.chunks[pos[src]])})
        step = {"step": "follow_cross_refs", "added": added}
        return {"scores": scores, "via": via, "trace": state["trace"] + [step]}

    def check(state: AgentState) -> dict:
        excerpts = "\n\n".join(
            f"[{cite(index.chunks[pos[i]])}] {index.chunks[pos[i]]['title']}\n{index.chunks[pos[i]]['text'][:500]}"
            for i in top_ids(state, CONTEXT_K))
        subs = "\n".join(f"- {s}" for s in state["sub_questions"])
        out = _json(llm.complete(CHECK_SYSTEM, f"Sub-questions:\n{subs}\n\nExcerpts:\n\n{excerpts}",
                                 max_tokens=300))
        sufficient = bool(out.get("sufficient", True))
        missing = [] if sufficient else _strings(out.get("missing_queries"), 2)
        step = {"step": "check", "sufficient": sufficient, "missing_queries": missing}
        return {"sufficient": sufficient or not missing, "pending": missing,
                "trace": state["trace"] + [step]}

    def route(state: AgentState) -> str:
        if state["sufficient"] or state["retries"] >= MAX_RETRIES:
            return "answer"
        return "retry"

    def bump(state: AgentState) -> dict:
        return {"retries": state["retries"] + 1}

    def answer(state: AgentState) -> dict:
        ids = top_ids(state, CONTEXT_K)
        chunks = [{**index.chunks[pos[i]], "rank": r + 1, "via": state["via"].get(i)}
                  for r, i in enumerate(ids)]
        trace = state["trace"] + [{"step": "context", "chunks": [cite(c) for c in chunks]}]
        return {"result": finish(state["question"], state["lang"], chunks, llm, trace,
                                 "agent", state["t0"], rag.llm.name)}

    # ---- graph ----------------------------------------------------------------
    g = StateGraph(AgentState)
    g.add_node("plan", plan)
    g.add_node("retrieve", retrieve)
    g.add_node("follow_refs", follow_refs)
    g.add_node("check", check)
    g.add_node("next_round", bump)
    g.add_node("answer", answer)
    g.add_edge(START, "plan")
    g.add_edge("plan", "retrieve")
    g.add_edge("retrieve", "follow_refs")
    g.add_edge("follow_refs", "check")
    g.add_conditional_edges("check", route, {"answer": "answer", "retry": "next_round"})
    g.add_edge("next_round", "retrieve")
    g.add_edge("answer", END)
    return g.compile()


def run_agent(rag, question: str) -> dict:
    t0 = time.time()
    llm = CountingLLM(rag.llm)
    graph = build_graph(rag, llm, question)
    lang = detect_lang(question)
    final = graph.invoke({
        "question": question, "lang": lang, "t0": t0, "scores": {}, "via": {}, "pending": [], "queries_done": [],
        "retries": 0, "sufficient": False, "trace": [{"step": "detect_lang", "lang": lang}],
    })
    return final["result"]


def mermaid() -> str:
    """Diagram of the graph, e.g. paste into https://mermaid.live"""
    class _Dummy:
        index = type("I", (), {"chunks": [], "by_sec": {}})()
        llm = type("L", (), {"name": "-"})()
    return build_graph(_Dummy(), None).get_graph().draw_mermaid()


if __name__ == "__main__":
    print(mermaid())
