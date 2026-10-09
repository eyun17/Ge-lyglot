#!/usr/bin/env python3
"""End-to-end evaluation with the LLM: retrieval recall, answer status and citations, per condition.

    python eval_answers.py --pick ko:q03 it-IT:q15 en:r01      # set:id, from all evalset files
    python eval_answers.py --pick ko:q03 --conditions rewrite agent
    python eval_answers.py --pick ko:q03 --model gpt-5.4          # overrides LLM_MODEL from .env

Unlike eval_retrieval.py this calls the LLM (costs money). Per question and condition it records
    recall@8        gold sections in the first 8 chunks handed to the answer step
    recall_ctx      same, over everything handed to the answer step (the agent hands over 12)
    status_ok       answer status == expected_behavior
    invalid         citations that are not in the retrieved chunks
    llm_calls, latency_s, tokens
Writes results/answers_<run>.jsonl and prints a table plus token totals.
"""
from __future__ import annotations

import argparse
import json
import os
import time
from pathlib import Path

from eval_retrieval import is_hit, parse_gold
import rag as rag_module
from rag import RAG, llm_from_env
from retrieval import LawIndex, cite

CONDITIONS = ["dense", "hybrid", "rewrite", "agent"]


def load_items(paths: list[Path]) -> dict[tuple[str, str], dict]:
    items = {}
    for p in paths:
        for line in p.open(encoding="utf-8"):
            if line.strip():
                it = json.loads(line)
                items[(it.get("set", it["lang"]), it["id"])] = it
    return items


def recall(golds: list[tuple], chunks: list[dict]) -> float | None:
    if not golds:
        return None
    return sum(any(is_hit(g, c) for c in chunks) for g in golds) / len(golds)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--pick", nargs="+", required=True, help="set:id, e.g. ko:q03 ar-PS:r16")
    ap.add_argument("--conditions", nargs="+", default=CONDITIONS, choices=CONDITIONS)
    ap.add_argument("--index", type=Path, default=Path("data/index"))
    ap.add_argument("--out", type=Path, default=Path("results"))
    ap.add_argument("--run", default=time.strftime("%Y%m%d-%H%M%S"), help="name of the output file")
    ap.add_argument("--model", help="LLM model, overrides LLM_MODEL")
    args = ap.parse_args()
    if args.model:
        os.environ["LLM_MODEL"] = args.model  # .env only fills unset variables

    items = load_items(sorted(Path(".").glob("evalset_*.jsonl")))
    picked = []
    for p in args.pick:
        set_, qid = p.split(":")
        if (set_, qid) not in items:
            raise SystemExit(f"not found: {p}")
        picked.append(items[(set_, qid)])

    llm = llm_from_env()
    rag = RAG(LawIndex.load(args.index), llm)
    args.out.mkdir(parents=True, exist_ok=True)
    out_path = args.out / f"answers_{args.run}.jsonl"
    rows = []
    with out_path.open("w", encoding="utf-8") as f:
        for it in picked:
            golds = [parse_gold(g) for g in it["gold_sections"]]
            for cond in args.conditions:
                before = dict(llm.usage)
                r = rag.answer(it["question"], cond)
                used = {k: llm.usage[k] - before.get(k, 0) for k in llm.usage}
                queries = [q for t in r["trace"] for q in t.get("queries", [])]
                row = {
                    "set": it.get("set", it["lang"]), "id": it["id"], "module": it.get("module", "core"),
                    "type": it["type"], "condition": cond, "question": it["question"],
                    "expected": it["expected_behavior"], "status": r["status"],
                    "status_ok": r["status"] == it["expected_behavior"],
                    "gold": it["gold_sections"],
                    "recall@8": recall(golds, r["retrieved"][:8]),
                    "recall_ctx": recall(golds, r["retrieved"]),
                    "retrieved": [cite(c) for c in r["retrieved"]],
                    "citations": r["citations"], "invalid": r["invalid_citations"],
                    "queries": queries, "llm_calls": r["llm_calls"], "latency_s": r["latency_s"],
                    "tokens": used, "answer": r["answer"], "model": r["model"],
                    "prompt_version": rag_module.PROMPT_VERSION,
                }
                rows.append(row)
                f.write(json.dumps(row, ensure_ascii=False) + "\n")
                f.flush()
                rc = "  -  " if row["recall@8"] is None else f"{row['recall@8']:.2f}"
                print(f"{row['set']:<6} {row['id']:<4} {cond:<8} recall@8={rc} "
                      f"status={'ok ' if row['status_ok'] else 'NO '}{r['status']:<25} "
                      f"invalid={len(row['invalid'])} calls={r['llm_calls']} {r['latency_s']}s", flush=True)

    print(f"\nwritten: {out_path}")
    print(f"{'condition':<9} {'recall@8':>8} {'recall_ctx':>10} {'status_ok':>9} {'invalid':>7} {'calls':>5} "
          f"{'s/q':>5}  tokens in/out")
    for cond in args.conditions:
        rs = [r for r in rows if r["condition"] == cond]
        rec = [r["recall@8"] for r in rs if r["recall@8"] is not None]
        ctx = [r["recall_ctx"] for r in rs if r["recall_ctx"] is not None]
        tin = sum(r["tokens"].get("input_tokens", 0) for r in rs)
        tout = sum(r["tokens"].get("output_tokens", 0) for r in rs)
        print(f"{cond:<9} {sum(rec) / max(len(rec), 1):>8.3f} {sum(ctx) / max(len(ctx), 1):>10.3f} "
              f"{sum(r['status_ok'] for r in rs):>6}/{len(rs):<2} {sum(len(r['invalid']) for r in rs):>7} "
              f"{sum(r['llm_calls'] for r in rs):>5} {sum(r['latency_s'] for r in rs) / len(rs):>5.1f}  "
              f"{tin:,}/{tout:,}")
    print(f"model {llm.name}, prompts {rag_module.PROMPT_VERSION}, total tokens: {dict(llm.usage)}")


if __name__ == "__main__":
    main()
