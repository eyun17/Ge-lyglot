#!/usr/bin/env python3
"""Run one experiment with and without the concept graph, and write everything a paper table needs.

    python -m evaluation.ablation --name kg-2026-10-14                                  # retrieval only, free
    python -m evaluation.ablation --name kg-2026-10-14 --answers validation heldout     # + LLM runs: shows the cost
    python -m evaluation.ablation --name kg-2026-10-14 --answers validation heldout --yes   # ... and runs them

Writes results/experiments/<name>/:
    manifest.json                       commit, prompt version, model, index, concept graph version, file hashes
    retrieval_<set>_<mode>.jsonl        per question, for each mode with and without "+kg"
    answers_<set>.jsonl (+ .manifest)   per question and condition, each with and without the graph (--answers)
    report.md                           tables: means per language set, paired differences with 95% intervals and p

Question sets: "main" is evaluation set v2 (six languages); "heldout" are questions written without seeing the
graph (evalset/heldout/), the honest measure of it. "validation" (answers only) is the split in splits.json.
Retrieval runs are free; answer runs call the LLM and only start with --yes.
"""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

from evaluation.compare import run as compare_run
from evaluation.eval_retrieval import EVALSET_DIR, EVALSET_FILES, evaluate
from evaluation.manifest import write_manifest
from gesetzpolyglot.retrieval import LawIndex

ROOT = Path(__file__).resolve().parent.parent
SETS = {"main": [EVALSET_DIR / f"{n}.jsonl" for n in EVALSET_FILES],
        "heldout": sorted((EVALSET_DIR / "heldout").glob("*.jsonl"))}
COST_PER_ANSWER = 0.0058  # gpt-5.4-mini, prompt v4: $0.69 for 120 answers (2026-10-13); the agent costs more


def load(files: list[Path]) -> list[dict]:
    return [json.loads(l) for p in files for l in p.open(encoding="utf-8") if l.strip()]


def graph_coverage(items: list[dict]) -> tuple[int, int]:
    """How many gold sections the concept graph links to at all. A high share means the graph may have been
    written with these questions in mind, so their result is an upper bound rather than an estimate."""
    from gesetzpolyglot.concepts import CONCEPTS, COUNTRY_GROUPS
    from gesetzpolyglot.kg import parse_section
    linked = {parse_section(x)[:2] for c in CONCEPTS.values() for x in c["sections"]}
    linked |= {parse_section(x)[:2] for c in CONCEPTS.values() for d in ("with_group", "with_concept")
               for xs in c.get(d, {}).values() for x in xs}
    linked |= {parse_section(x)[:2] for g in COUNTRY_GROUPS.values() for x in g["sections"]}
    gold = {(it["id"], parse_section(g)[:2]) for it in items for g in it["gold_sections"]}  # once per question
    return sum(sec in linked for _, sec in gold), len(gold)


def by_set_table(rows_by_mode: dict[str, list[dict]]) -> str:
    modes = list(rows_by_mode)
    sets = list(dict.fromkeys(r["set"] for rs in rows_by_mode.values() for r in rs))
    head = "| mode | all | " + " | ".join(sets) + " |\n|---|---|" + "---|" * len(sets)
    lines = [head]
    for m in modes:
        per = defaultdict(list)
        for r in rows_by_mode[m]:
            per[r["set"]].append(r["recall"])
        allr = [r["recall"] for r in rows_by_mode[m]]
        lines.append(f"| {m} | {sum(allr) / len(allr):.3f} | "
                     + " | ".join(f"{sum(per[s]) / len(per[s]):.3f}" for s in sets) + " |")
    return "\n".join(lines)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--name", required=True, help="experiment name, e.g. kg-2026-10-14")
    ap.add_argument("--sets", nargs="+", default=["main", "heldout"], choices=list(SETS), help="retrieval question sets")
    ap.add_argument("--modes", nargs="+", default=["dense", "hybrid"], choices=["dense", "hybrid"])
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--index", type=Path, default=Path("data/index"))
    ap.add_argument("--store", choices=["numpy", "chroma"], default=None)
    ap.add_argument("--answers", nargs="*", default=[], choices=["validation", "heldout"],
                    help="also run the LLM (all four conditions, with and without the graph)")
    ap.add_argument("--conditions", nargs="+", default=["dense", "hybrid", "rewrite", "agent"])
    ap.add_argument("--yes", action="store_true", help="really start the LLM runs (they cost money)")
    ap.add_argument("--force", action="store_true", help="overwrite an existing experiment folder")
    args = ap.parse_args()

    out = ROOT / "results" / "experiments" / args.name
    if out.exists() and any(out.iterdir()) and not args.force:
        raise SystemExit(f"{out} exists; choose another --name or pass --force")
    out.mkdir(parents=True, exist_ok=True)

    # cost check before anything else
    answer_jobs = []
    for s in args.answers:
        if s == "validation":
            n = len(json.loads((EVALSET_DIR / "splits.json").read_text(encoding="utf-8"))["validation"]["items"])
            answer_jobs.append((s, ["--split", "validation"], n))
        else:
            answer_jobs.append((s, ["--items", *map(str, SETS["heldout"])], len(load(SETS["heldout"]))))
    if answer_jobs:
        n_answers = sum(n for *_, n in answer_jobs) * len(args.conditions) * 2
        print(f"LLM runs: {n_answers} answers, about ${n_answers * COST_PER_ANSWER:.2f} with gpt-5.4-mini")
        if not args.yes:
            raise SystemExit("not started: add --yes to run them (or drop --answers for retrieval only)")

    files = [p for s in args.sets for p in SETS[s]]
    write_manifest(out / "manifest.json", args=vars(args), evalset_files=files, index_dir=args.index,
                   extra={"experiment": args.name})
    report = [f"# Experiment {args.name}: with and without the concept graph", "",
              "See manifest.json for the commit, prompt version, model, index and concept graph version.", ""]

    index = LawIndex.load(args.index, store=args.store)
    for s in args.sets:
        items = load(SETS[s])
        rows_by_mode = {}
        for mode in [m for base in args.modes for m in (base, base + "+kg")]:
            rows = evaluate(index, items, mode, args.k)
            rows_by_mode[mode] = rows
            path = out / f"retrieval_{s}_{mode}.jsonl"
            path.write_text("".join(json.dumps(r, ensure_ascii=False) + "\n" for r in rows), encoding="utf-8")
            print(f"{s:<8} {mode:<10} recall@{args.k} = {sum(r['recall'] for r in rows) / len(rows):.3f} (n={len(rows)})")
        _, md = compare_run([str(out / f"retrieval_{s}_{m}.jsonl") for m in rows_by_mode])
        covered, total = graph_coverage(items)
        report += [f"## Retrieval, {s} ({len(rows_by_mode[args.modes[0]])} questions with gold sections)", "",
                   f"The concept graph links to {covered} of the {total} gold sections of these questions "
                   f"({covered / max(total, 1):.0%}). A share near 100% means the graph was probably written with "
                   "these questions in mind: read the result as an upper bound.", "",
                   "Mean recall@8 per language set:", "", by_set_table(rows_by_mode), "",
                   "Paired differences (bootstrap 95% interval; p from McNemar or a sign-flip permutation test):", "",
                   md, ""]

    for s, pick, _ in answer_jobs:
        cmd = [sys.executable, "-m", "evaluation.eval_answers", *pick, "--kg", "both", "--conditions",
               *args.conditions, "--index", str(args.index), "--out", str(out), "--run", s]
        print("running:", " ".join(cmd))
        subprocess.run(cmd, cwd=ROOT, check=True)
        _, md = compare_run([str(out / f"answers_{s}.jsonl")])
        report += [f"## Answers, {s}", "", md, ""]

    (out / "report.md").write_text("\n".join(report), encoding="utf-8")
    print(f"\nwritten: {out / 'report.md'}")


if __name__ == "__main__":
    main()
