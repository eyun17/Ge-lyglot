#!/usr/bin/env python3
"""Section-level retrieval recall for the single-pass baselines (conditions 1-2).

    python eval_retrieval.py                       # dense + hybrid, k=8, core set + refugee module, all sets
    python eval_retrieval.py --modes dense bm25 hybrid --k 5
    python eval_retrieval.py --evalset evalset/evalset_draft_en.jsonl
    python eval_retrieval.py --store numpy            # exact baseline
    python eval_retrieval.py --store chroma           # same evalset on the Chroma (HNSW) store

Reads one or more evalset files (default: every core and refugee file in evalset/);
items with empty gold_sections are skipped.
Items carry a "module" ("core" if absent, e.g. "refugee"); recall is reported per module, then by set and type.
Writes results/retrieval_<store>_<mode>.jsonl (per item).
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from retrieval import LawIndex, cite

EVALSET_DIR = Path(__file__).resolve().parent / "evalset"

GOLD_RE = re.compile(r"^(\S+)\s*§\s*(\d+[a-z]?)(?:\s+Abs\.\s*(\d+[a-z]?))?$")


def parse_gold(s: str) -> tuple[str, str, str | None]:
    m = GOLD_RE.match(s.strip())
    if not m:
        raise ValueError(f"bad gold section: {s!r} (expected 'AufenthG § 18a Abs. 1')")
    return m.group(1), m.group(2), m.group(3)


def is_hit(gold: tuple, chunk: dict) -> bool:
    """A gold without Absatz is satisfied by any Absatz of that section."""
    law, sec, absatz = gold
    return (chunk["law"].lower() == law.lower() and chunk["section"] == sec
            and (absatz is None or chunk["absatz"] == absatz))


def evaluate(index: LawIndex, items: list[dict], mode: str, k: int) -> list[dict]:
    rows = []
    for it in items:
        golds = [parse_gold(g) for g in it["gold_sections"]]
        if not golds:
            continue
        hits = index.search(it["question"], k=k, mode=mode)
        found = [any(is_hit(g, h) for h in hits) for g in golds]
        missing = [g for g in golds if not index.get_section(*g)]
        rows.append({
            "id": it["id"], "module": it.get("module", "core"), "type": it["type"], "lang": it["lang"], "set": it.get("set", it["lang"]), "mode": mode, "k": k,
            "recall": sum(found) / len(golds), "all_found": all(found),
            "retrieved": [cite(h) for h in hits],
            "missed": [s for s, f in zip(it["gold_sections"], found) if not f],
            # gold that does not exist in the corpus at all -> fix the evalset, not the retriever
            "gold_not_in_corpus": [s for s, g in zip(it["gold_sections"], golds) if g in missing],
        })
    return rows


def summarize(rows: list[dict]) -> dict:
    """Keys: 'all', '<set>', '<set>/<type>'. A set is a language plus the asker's nationality,
    e.g. ar-SY and ar-PS; files without a "set" field fall back to the language."""
    groups = defaultdict(list)
    for r in rows:
        groups["all"].append(r)
        s = r.get("set", r["lang"])
        groups[s].append(r)
        groups[f"{s}/{r['type']}"].append(r)
    return {t: {"n": len(rs),
                "recall": round(sum(r["recall"] for r in rs) / len(rs), 3),
                "all_found": round(sum(r["all_found"] for r in rs) / len(rs), 3)}
            for t, rs in groups.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--evalset", type=Path, nargs="+",
                    default=[EVALSET_DIR / f"evalset_{m}_{l}.jsonl" for m in ("draft", "refugee")
                             for l in ("ko", "en", "tr", "ar_sy", "ar_ps", "it")])
    ap.add_argument("--index", type=Path, default=Path("data/index"))
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--modes", nargs="+", default=["dense", "hybrid"])
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--store", choices=["numpy", "chroma"], default=None,
                    help="vector store to evaluate (default: the one recorded in meta.json)")
    args = ap.parse_args()

    missing = [str(p) for p in args.evalset if not p.exists()]
    if missing:  # never evaluate silently on fewer files than asked for
        raise SystemExit("evalset file(s) not found: " + ", ".join(missing))
    index = LawIndex.load(args.index, store=args.store)
    print(f"vector store: {index.store.name}")
    items = [json.loads(l) for p in args.evalset
             for l in p.open(encoding="utf-8") if l.strip()]
    args.out.mkdir(parents=True, exist_ok=True)
    bad = set()
    for mode in args.modes:
        rows = evaluate(index, items, mode, args.k)
        with (args.out / f"retrieval_{index.store.name}_{mode}.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                bad.update((r["id"], g) for g in r["gold_not_in_corpus"])  # same gold in every language
        # modules are reported separately: they are different question sets, not comparable
        for module in dict.fromkeys(r["module"] for r in rows):
            print(f"\n[{mode}] {module} — recall@{args.k}")
            for t, s in summarize([r for r in rows if r["module"] == module]).items():
                print(f"  {t:<14} n={s['n']:<3} recall={s['recall']:.3f}  all_found={s['all_found']:.3f}")
    if bad:
        print("\ngold sections not found in corpus (check the evalset):")
        for qid, g in sorted(bad):
            print(f"  {qid}: {g}")


if __name__ == "__main__":
    main()
