"""Run: python test_agent.py   (no API key, no model download)"""
import json
import tempfile
from pathlib import Path

import agent
from rag import RAG

agent.K_PER_QUERY = 1  # tiny corpus: one hit per query, so cross_refs must do the rest
from retrieval import LawIndex
from test_retrieval import FakeEmbedder


def _c(sec, absatz, title, text, refs=(), law="AufenthG"):
    return {"id": f"{law}-{sec}" + (f"-{absatz}" if absatz else ""), "law": law, "section": sec,
            "absatz": absatz, "title": title, "text": text, "snapshot": "2026-10-08",
            "stand": "zuletzt geändert 21.7.2026", "source_url": f"https://x/__{sec}.html",
            "cross_refs": [{"law": l, "section": s, "absatz": a, "status": st} for l, s, a, st in refs]}


CHUNKS = [
    _c("18g", "1", "Blaue Karte EU", "Blaue Karte EU für Fachkraft mit akademischer Ausbildung Mindestgehalt.",
       refs=[("AufenthG", "18", "2", "ok"), ("AufenthG", "18c", None, "ok"), ("StGB", "1", None, "external")]),
    _c("18", "2", "Grundsatz", "Erteilung setzt Arbeitsplatzangebot und Zustimmung voraus."),
    _c("18c", "1", "Niederlassungserlaubnis für Fachkräfte", "Niederlassungserlaubnis nach drei Jahren."),
    _c("18c", "2", "Niederlassungserlaubnis für Fachkräfte", "Inhaber Blaue Karte erhalten Niederlassungserlaubnis nach 27 Monaten."),
    _c("18c", "3", "Niederlassungserlaubnis für Fachkräfte", "Hochqualifizierte sofort."),
    _c("26", "1", "Bestimmte Staaten", "Staatsangehörige der Republik Korea Zustimmung.", law="BeschV"),
    _c("60", "1", "Abschiebungsverbot", "Ein Ausländer darf nicht abgeschoben werden."),
]


class ScriptedLLM:
    name = "scripted"

    def __init__(self, replies):
        self.replies, self.calls = list(replies), []

    def complete(self, system, user, max_tokens=1200):
        self.calls.append((system.split("\n")[0][:40], user))
        return self.replies.pop(0)


def _rag(d, llm):
    p = Path(d) / "chunks.jsonl"
    p.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in CHUNKS), encoding="utf-8")
    return RAG(LawIndex.build(p, Path(d) / "idx", FakeEmbedder()), llm)


def test_agent_follows_refs_and_retries():
    llm = ScriptedLLM([
        '{"sub_questions": ["Blue Card requirements"], "queries": ["Blaue Karte EU Mindestgehalt"]}',
        '{"sufficient": false, "missing_queries": ["Republik Korea Zustimmung"]}',
        '{"sufficient": true, "missing_queries": []}',
        "STATUS: answer\n\n블루카드 요건 [AufenthG § 18g Abs. 1], 정주허가 [AufenthG § 18c Abs. 2], "
        "한국 국적 [BeschV § 26 Abs. 1].",
    ])
    with tempfile.TemporaryDirectory() as d:
        r = _rag(d, llm).answer("블루카드 받고 정주허가는 언제 되나요?", "agent")

    steps = [t["step"] for t in r["trace"]]
    assert steps == ["detect_lang", "plan", "retrieve", "follow_cross_refs", "check",
                     "retrieve", "follow_cross_refs", "check", "context", "validate"]
    refs = next(t for t in r["trace"] if t["step"] == "follow_cross_refs")["added"]
    added = {a["chunk"] for a in refs}
    assert "AufenthG § 18 Abs. 2" in added                       # Absatz-level ref
    assert len([a for a in added if a.startswith("AufenthG § 18c")]) == 2  # section ref -> top 2
    assert not any("StGB" in a for a in added)                    # external laws are skipped
    via = {c["id"]: c["via"] for c in r["retrieved"]}
    assert via["AufenthG-18g-1"].startswith("search:")
    assert via["AufenthG-18-2"] == "cross-ref from AufenthG § 18g Abs. 1"
    assert r["condition"] == "agent" and r["llm_calls"] == 4 and r["lang"] == "ko"
    assert r["citations"] == ["AufenthG § 18g Abs. 1", "AufenthG § 18c Abs. 2", "BeschV § 26 Abs. 1"]
    assert r["invalid_citations"] == []


def test_agent_stops_after_max_retries_and_survives_bad_json():
    llm = ScriptedLLM(["not json at all"]
                      + ['{"sufficient": false, "missing_queries": ["Abschiebungsverbot"]}'] * 3
                      + ["STATUS: refuse_out_of_scope\n\nOut of scope."])
    with tempfile.TemporaryDirectory() as d:
        r = _rag(d, llm).answer("How do I pay German income tax?", "agent")
    assert [t["step"] for t in r["trace"]].count("check") == 3   # first round + 2 retries
    plan = next(t for t in r["trace"] if t["step"] == "plan")
    assert plan["queries"] == ["How do I pay German income tax?"]  # fallback when JSON is broken
    assert r["status"] == "refuse_out_of_scope" and r["llm_calls"] == 5


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
