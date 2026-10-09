"""Run: python test_retrieval.py   (no model download; uses a fake embedder)"""
import json
import tempfile
from pathlib import Path

import numpy as np

from eval_retrieval import evaluate, is_hit, parse_gold, summarize
from retrieval import LawIndex, tokenize


class FakeEmbedder:
    """Hashed bag-of-words, so 'dense' behaves like a weak lexical model."""
    name = "fake"

    def encode(self, texts):
        out = np.zeros((len(texts), 256), dtype=np.float32)
        for i, t in enumerate(texts):
            for tok in tokenize(t):
                out[i, sum(map(ord, tok)) % 256] += 1
            out[i] /= np.linalg.norm(out[i]) or 1
        return out


def _chunk(sec, absatz, title, text, law="AufenthG"):
    return {"id": f"{law}-{sec}" + (f"-{absatz}" if absatz else ""), "law": law, "section": sec,
            "absatz": absatz, "title": title, "text": text, "snapshot": "2026-10-05"}


CHUNKS = [
    _chunk("16b", "1", "Studium", "Einem Ausländer wird zum Zweck des Studiums eine Aufenthaltserlaubnis erteilt."),
    _chunk("16b", "3", "Studium", "Die Aufenthaltserlaubnis berechtigt zur Ausübung einer Beschäftigung an 140 Arbeitstagen."),
    _chunk("18g", "1", "Blaue Karte EU", "Einer Fachkraft mit akademischer Ausbildung wird eine Blaue Karte EU erteilt bei Mindestgehalt."),
    _chunk("20a", None, "Chancenkarte", "Die Chancenkarte wird zur Suche nach einer Erwerbstätigkeit erteilt."),
    _chunk("26", "1", "Bestimmte Staaten", "Für Staatsangehörige der Republik Korea kann die Zustimmung erteilt werden.", law="BeschV"),
]


def _index(d):
    p = Path(d) / "chunks.jsonl"
    p.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in CHUNKS), encoding="utf-8")
    LawIndex.build(p, Path(d) / "index", FakeEmbedder())
    return LawIndex.load(Path(d) / "index", FakeEmbedder())  # round-trip through disk


def test_parse_gold_and_hit():
    assert parse_gold("AufenthG § 16b Abs. 3") == ("AufenthG", "16b", "3")
    assert parse_gold("AufenthG § 20a") == ("AufenthG", "20a", None)
    assert is_hit(("AufenthG", "16b", None), CHUNKS[0]) and is_hit(("aufenthg", "16b", "3"), CHUNKS[1])
    assert not is_hit(("AufenthG", "16b", "3"), CHUNKS[0])
    assert not is_hit(("BeschV", "16b", None), CHUNKS[0])


def test_search_modes_and_get_section():
    with tempfile.TemporaryDirectory() as d:
        idx = _index(d)
        for mode in ("dense", "bm25", "hybrid"):
            top = idx.search("Blaue Karte EU Mindestgehalt", k=2, mode=mode)[0]
            assert top["id"] == "AufenthG-18g-1" and top["rank"] == 1, mode
        assert idx.search("Chancenkarte", k=1)[0]["id"] == "AufenthG-20a"  # found via section title
        assert idx.search("xyzzy", k=3, mode="bm25") == []
        assert [c["id"] for c in idx.get_section("aufenthg", "§ 16b")] == ["AufenthG-16b-1", "AufenthG-16b-3"]
        assert [c["id"] for c in idx.get_section("AufenthG", "16b", 3)] == ["AufenthG-16b-3"]
        assert idx.get_section("AufenthG", "99") == []


def test_evaluate():
    items = [
        {"id": "a", "type": "single", "lang": "de", "question": "Beschäftigung Arbeitstagen Studium",
         "gold_sections": ["AufenthG § 16b Abs. 3"]},
        {"id": "b", "type": "multi", "lang": "de", "question": "Republik Korea Zustimmung",
         "gold_sections": ["BeschV § 26 Abs. 1", "AufenthG § 99"]},
        {"id": "c", "type": "refusal", "lang": "de", "question": "Rente", "gold_sections": []},
    ]
    with tempfile.TemporaryDirectory() as d:
        rows = evaluate(_index(d), items, "hybrid", k=2)
    assert [r["id"] for r in rows] == ["a", "b"]  # empty gold skipped
    assert rows[0]["recall"] == 1.0 and rows[0]["all_found"]
    assert rows[1]["recall"] == 0.5 and rows[1]["missed"] == ["AufenthG § 99"]
    assert rows[1]["gold_not_in_corpus"] == ["AufenthG § 99"]
    s = summarize(rows)
    assert s["all"] == {"n": 2, "recall": 0.75, "all_found": 0.5}
    assert s["de"] == s["all"] and s["de/single"]["recall"] == 1.0 and s["de/multi"]["n"] == 1


def test_chroma_store_matches_numpy():
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "chunks.jsonl"
        p.write_text("\n".join(json.dumps(c, ensure_ascii=False) for c in CHUNKS), encoding="utf-8")
        np_idx = LawIndex.build(p, Path(d) / "a", FakeEmbedder())
        ch_idx = LawIndex.build(p, Path(d) / "b", FakeEmbedder(), store="chroma")
        assert np_idx.store.name == "numpy" and ch_idx.store.name == "chroma"
        for q in ("Blaue Karte EU Mindestgehalt", "Studium Beschäftigung Arbeitstagen", "Republik Korea"):
            qv = FakeEmbedder().encode([q])[0]
            relevant = int(((np_idx.emb @ qv) > 0).sum())  # ignore ties at similarity 0
            a = [h["id"] for h in np_idx.search(q, relevant, mode="dense")]
            b = [h["id"] for h in ch_idx.search(q, relevant, mode="dense")]
            assert relevant >= 1 and a == b, (q, a, b)  # HNSW is exact on a corpus this small
        # metadata filter
        hits = ch_idx.search("Zustimmung erteilt", 5, mode="hybrid", law="BeschV")
        assert [h["law"] for h in hits] == ["BeschV"]
        assert {h["law"] for h in np_idx.search("Zustimmung erteilt", 5, mode="dense", law="BeschV")} == {"BeschV"}
        # persisted: reload from disk picks Chroma from meta.json
        again = LawIndex.load(Path(d) / "b", FakeEmbedder())
        assert again.store.name == "chroma" and again.store.col.count() == len(CHUNKS)
        # converting an existing numpy index without re-embedding
        LawIndex.to_chroma(Path(d) / "a")
        conv = LawIndex.load(Path(d) / "a", FakeEmbedder())
        assert conv.store.name == "chroma"
        assert conv.search("Chancenkarte", 1, mode="dense")[0]["id"] == "AufenthG-20a"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
