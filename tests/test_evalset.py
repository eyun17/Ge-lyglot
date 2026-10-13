"""Run: python -m pytest tests/test_evalset.py   (no model needed). The six evalset files must hold the same questions:
same ids, gold sections and expected behavior."""
import json

from evaluation.eval_retrieval import EVALSET_DIR, EVALSET_FILES, parse_gold

FIELDS = ("old_id", "topic", "type", "expected_behavior", "gold_sections", "persona_country", "persona_group")
GROUPS = {"eu", "non_eu", "none", "both", "unclear"}


def load(name):
    return [json.loads(l) for l in (EVALSET_DIR / f"{name}.jsonl").open(encoding="utf-8") if l.strip()]


def test_sets_are_parallel():
    ref = load("ko")
    for name in EVALSET_FILES:
        rows = load(name)
        assert [r["id"] for r in rows] == [r["id"] for r in ref], name
        for r, k in zip(rows, ref):
            assert {f: r[f] for f in FIELDS} == {f: k[f] for f in FIELDS}, (name, r["id"])
            assert r["question"].strip(), (name, r["id"])


def test_fields():
    for r in load("ko"):
        assert r["persona_group"] in GROUPS, r["id"]
        for g in r["gold_sections"]:
            parse_gold(g)
        if r["expected_behavior"] == "answer":
            assert r["gold_sections"], r["id"]
    assert all("question_msa" in r for r in load("ar_sy"))


if __name__ == "__main__":
    test_sets_are_parallel()
    test_fields()
    print("ok")
