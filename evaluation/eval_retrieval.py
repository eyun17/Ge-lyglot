#!/usr/bin/env python3
"""Section-level retrieval recall for the single-pass baselines (conditions 1-2).

    python -m evaluation.eval_retrieval                       # dense + hybrid, k=8, all six language sets
    python -m evaluation.eval_retrieval --modes dense bm25 hybrid --k 5
    python -m evaluation.eval_retrieval --evalset evalset/en.jsonl
    python -m evaluation.eval_retrieval --store numpy            # exact baseline
    python -m evaluation.eval_retrieval --store chroma           # same evalset on the Chroma (HNSW) store
    python -m evaluation.eval_retrieval --translate deu_Latn      # translate each question to German first (NLLB, local)
    python -m evaluation.eval_retrieval --translate deu_Latn --fuse   # search original and translation, fuse with RRF

Reads one or more evalset files (default: the six language files in evalset/, the same 60 questions each);
items with empty gold_sections are skipped.
Recall is reported by set and type, then by persona_group (the asker's nationality: eu, non_eu, ...).
Items of the archived v1 evalset carry a "module" (core, refugee, tax), which is reported separately.
Writes results/retrieval_<store>_<mode>.jsonl (per item).
"""
from __future__ import annotations

import argparse
import json
import re
from collections import defaultdict
from pathlib import Path

from gesetzpolyglot.retrieval import RRF_K, LawIndex, cite

EVALSET_DIR = Path(__file__).resolve().parent.parent / "evalset"
# one file per language set, each holding the same questions (evalset v2)
EVALSET_FILES = ("ko", "en", "de", "ar", "ar_sy", "it")

# law abbreviations may contain a space: "SGB VI § 210 Abs. 1"
GOLD_RE = re.compile(r"^(\S+(?: [IVX]+)?)\s*§\s*(\d+[a-z]?)(?:\s+Abs\.\s*(\d+[a-z]?))?$")


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


def fused_search(index: LawIndex, queries: list[str], k: int, mode: str, pool: int = 50) -> list[dict]:
    """Search several phrasings of one question and fuse the rankings with RRF."""
    score, by_id = {}, {}
    for q in dict.fromkeys(queries):
        for h in index.search(q, pool, mode=mode):
            by_id[h["id"]] = h
            score[h["id"]] = score.get(h["id"], 0.0) + 1.0 / (RRF_K + h["rank"])
    return [by_id[i] for i in sorted(score, key=score.get, reverse=True)[:k]]


def evaluate(index: LawIndex, items: list[dict], mode: str, k: int,
             queries: dict[str, str | list[str]] | None = None) -> list[dict]:
    """queries: optional {question: text to search instead}, e.g. a translation of the question;
    a list of texts is searched one by one and fused (fused_search)."""
    rows = []
    for it in items:
        golds = [parse_gold(g) for g in it["gold_sections"]]
        if not golds:
            continue
        query = (queries or {}).get(it["question"], it["question"])
        hits = fused_search(index, query, k, mode) if isinstance(query, list) else index.search(query, k=k, mode=mode)
        found = [any(is_hit(g, h) for h in hits) for g in golds]
        missing = [g for g in golds if not index.get_section(*g)]
        rows.append({
            "id": it["id"], "module": it.get("module", "all"), "type": it["type"],
            "persona_group": it.get("persona_group"), "lang": it["lang"], "set": it.get("set", it["lang"]), "mode": mode, "k": k,
            "recall": sum(found) / len(golds), "all_found": all(found),
            **({"query": query} if query != it["question"] else {}),
            "retrieved": [cite(h) for h in hits],
            "missed": [s for s, f in zip(it["gold_sections"], found) if not f],
            # gold that does not exist in the corpus at all -> fix the evalset, not the retriever
            "gold_not_in_corpus": [s for s, g in zip(it["gold_sections"], golds) if g in missing],
        })
    return rows


def summarize(rows: list[dict]) -> dict:
    """Keys: 'all', '<set>', '<set>/<type>'. A set is a language plus the asker's nationality,
    e.g. ar-SY and ar-EG; files without a "set" field fall back to the language."""
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
                    default=[EVALSET_DIR / f"{l}.jsonl" for l in EVALSET_FILES])
    ap.add_argument("--index", type=Path, default=Path("data/index"))
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--modes", nargs="+", default=["dense", "hybrid"])
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--store", choices=["numpy", "chroma"], default=None,
                    help="vector store to evaluate (default: the one recorded in meta.json)")
    ap.add_argument("--translate", metavar="NLLB_CODE",
                    help="translate questions before searching, e.g. deu_Latn or arb_Arab (see query_translate.py)")
    ap.add_argument("--fuse", action="store_true",
                    help="with --translate: search the original question and its translation, fuse with RRF")
    args = ap.parse_args()

    missing = [str(p) for p in args.evalset if not p.exists()]
    if missing:  # never evaluate silently on fewer files than asked for
        raise SystemExit("evalset file(s) not found: " + ", ".join(missing))
    index = LawIndex.load(args.index, store=args.store)
    print(f"vector store: {index.store.name}")
    items = [json.loads(l) for p in args.evalset
             for l in p.open(encoding="utf-8") if l.strip()]
    args.out.mkdir(parents=True, exist_ok=True)
    queries, suffix = None, ""
    if args.translate:
        from evaluation.query_translate import translate_items
        queries, suffix = translate_items(items, args.translate), f"_tr-{args.translate}"
        if args.fuse:
            queries = {q: [q, t] for q, t in queries.items()}
            suffix = f"_fuse-{args.translate}"
    bad = set()
    for mode in args.modes:
        rows = evaluate(index, items, mode, args.k, queries)
        with (args.out / f"retrieval_{index.store.name}_{mode}{suffix}.jsonl").open("w", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r, ensure_ascii=False) + "\n")
                bad.update((r["id"], g) for g in r["gold_not_in_corpus"])  # same gold in every language
        # modules are reported separately: they are different question sets, not comparable
        for module in dict.fromkeys(r["module"] for r in rows):
            print(f"\n[{mode}] {module} — recall@{args.k}")
            for t, s in summarize([r for r in rows if r["module"] == module]).items():
                print(f"  {t:<14} n={s['n']:<3} recall={s['recall']:.3f}  all_found={s['all_found']:.3f}")
        groups = defaultdict(list)
        for r in rows:
            if r["persona_group"]:
                groups[r["persona_group"]].append(r)
        if groups:
            print(f"\n[{mode}] by persona_group (all sets)")
            for g, rs in groups.items():
                print(f"  {g:<14} n={len(rs):<3} recall={sum(r['recall'] for r in rs) / len(rs):.3f}")
    if bad:
        print("\ngold sections not found in corpus (check the evalset):")
        for qid, g in sorted(bad):
            print(f"  {qid}: {g}")


if __name__ == "__main__":
    main()
