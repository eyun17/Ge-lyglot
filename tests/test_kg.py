"""Run: python -m pytest tests/test_kg.py   (no model download; the corpus check reads data/processed/chunks.jsonl)"""
import json
import tempfile
from pathlib import Path

from gesetzpolyglot.concepts import CONCEPTS, COUNTRY_GROUPS
from gesetzpolyglot.kg import ConceptGraph, kg_search, parse_section
from gesetzpolyglot.retrieval import LawIndex
from test_retrieval import FakeEmbedder

CHUNKS = Path(__file__).resolve().parent.parent / "data" / "processed" / "chunks.jsonl"


def test_every_section_exists_in_the_corpus():
    """A renumbered section after an amendment would silently point nowhere."""
    have = {(c["law"], c["section"], c["absatz"]) for c in map(json.loads, CHUNKS.open(encoding="utf-8"))}
    secs = {(law, sec) for law, sec, _ in have}
    wanted = [s for c in CONCEPTS.values() for s in c["sections"]]
    wanted += [s for c in CONCEPTS.values() for d in ("with_group", "with_concept") for ss in c.get(d, {}).values() for s in ss]
    wanted += [s for g in COUNTRY_GROUPS.values() for s in g["sections"]]
    for s in wanted:
        law, sec, absatz = parse_section(s)
        assert ((law, sec, absatz) in have) if absatz else ((law, sec) in secs), s


def test_every_concept_has_all_five_languages():
    for cid, c in CONCEPTS.items():
        assert all(c.get(lang) for lang in ("ko", "en", "de", "ar", "it")), cid


def test_match():
    g = ConceptGraph()
    assert g.match("블루카드를 받은 뒤 영주권은?")[0] == ["blue_card", "settlement_permit"]
    assert g.match("أنا برتغالي وأعمل في المقر الرئيسي لشركة إسبانية")[1] == ["eu"]
    assert g.match("Sono serbo. Posso lavorare in Germania?")[1] == ["western_balkans"]
    assert g.match("The capital of my country")[1] == []          # "ital" must start a word
    assert g.match("Ich bin Österreicher")[1] == ["eu"]
    # a spouse of an EU citizen falls under FreizügG/EU § 3, not under the Residence Act's family reunification
    secs = g.sections("I'm French. Can my American spouse live with me?")
    assert ("FreizügG/EU", "3", "1") in secs and ("AufenthG", "30", None) in secs
    assert ("FreizügG/EU", "3", "1") not in g.sections("Can my spouse live with me in Germany?")


def test_kg_search_adds_sections_and_keeps_unmatched_questions():
    chunks = [
        {"id": "BMG-17-1", "law": "BMG", "section": "17", "absatz": "1", "title": "Anmeldung, Abmeldung",
         "text": "Wer eine Wohnung bezieht, hat sich innerhalb von zwei Wochen anzumelden.", "cross_refs": []},
        {"id": "AufenthG-16b-3", "law": "AufenthG", "section": "16b", "absatz": "3", "title": "Studium",
         "text": "Beschäftigung an 140 Arbeitstagen im Jahr.", "cross_refs": []},
    ]
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "chunks.jsonl"
        p.write_text("\n".join(json.dumps(c) for c in chunks), encoding="utf-8")
        idx = LawIndex.build(p, Path(d) / "idx", FakeEmbedder())
        g = ConceptGraph()
        hits = kg_search(idx, g, "이탈리아에서 이사하는데 안멜둥을 해야 하나요?", k=2)
        assert hits[0]["id"] == "BMG-17-1" and hits[0]["via"] == "concept graph"
        plain = kg_search(idx, g, "xyz", k=2)
        assert [h["id"] for h in plain] == [h["id"] for h in idx.search("xyz", 2, mode="dense")]


def test_destination_is_not_nationality():
    g = ConceptGraph()
    assert g.match("요르단 사람인데 독일 비자로 네덜란드에 여행갈 수 있나요")[1] == []
    assert g.match("I'm Jordanian. Can I travel to the Netherlands with a German visa?")[1] == []
    assert g.match("أنا أردني، هل يمكنني السفر إلى هولندا؟")[1] == []
    assert g.match("한국에도 소득이 있는데")[1] == []
    assert g.match("저는 포르투갈 사람인데")[1] == ["eu"]                       # nationality
    assert g.match("Ich ziehe von Italien nach Deutschland.")[1] == ["eu"]    # origin still counts
    assert g.match("أنا نمساوي وأعيش في ألمانيا")[1] == ["eu"]


def test_rag_switch_with_and_without_graph():
    """Without a graph retrieval is unchanged; with it, a concept_graph step is traced and the result says kg."""
    from gesetzpolyglot.rag import RAG

    class LLM:
        name = "fake"

        def complete(self, system, user, max_tokens=1200):
            return '{"queries": ["Anmeldung Wohnung"]}' if "search" in system else "STATUS: answer\n\nok"

    chunks = [
        {"id": "BMG-17-1", "law": "BMG", "section": "17", "absatz": "1", "title": "Anmeldung, Abmeldung",
         "text": "Wer eine Wohnung bezieht, hat sich anzumelden.", "cross_refs": []},
        {"id": "AufenthG-16b-3", "law": "AufenthG", "section": "16b", "absatz": "3", "title": "Studium",
         "text": "Beschäftigung an 140 Arbeitstagen.", "cross_refs": []},
    ]
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "chunks.jsonl"
        p.write_text("\n".join(json.dumps(c) for c in chunks), encoding="utf-8")
        idx = LawIndex.build(p, Path(d) / "idx", FakeEmbedder())
        q = "안멜둥을 해야 하나요?"
        for cond in ("dense", "hybrid", "rewrite", "agent"):
            off = RAG(idx, LLM(), k=1).answer(q, cond)
            on = RAG(idx, LLM(), k=1, graph=ConceptGraph()).answer(q, cond)
            assert off["kg"] is False and on["kg"] is True, cond
            assert not any(t["step"] == "concept_graph" for t in off["trace"]), cond
            kg = next(t for t in on["trace"] if t["step"] == "concept_graph")
            assert kg["concepts"] == ["registration"], cond
            assert on["retrieved"][0]["id"] == "BMG-17-1", cond


def test_compare_statistics():
    from evaluation.compare import compare, mcnemar_p
    assert mcnemar_p([0] * 10, [1] * 10) < 0.01 and mcnemar_p([0, 1], [1, 0]) == 1.0
    a = {("ko", f"q{i}"): {"recall": 0.0} for i in range(20)}
    b = {("ko", f"q{i}"): {"recall": 1.0 if i < 15 else 0.0} for i in range(20)}
    r = compare(a, b, ["recall"])[0]
    assert r["diff"] == 0.75 and r["better"] == 15 and r["worse"] == 0 and r["ci_low"] > 0.5 and r["p"] < 0.001
