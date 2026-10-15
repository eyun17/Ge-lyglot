#!/usr/bin/env python3
"""Paired comparison of evaluation results: the same questions under two variants (e.g. with and without the
concept graph), with bootstrap confidence intervals and significance tests.

    python -m evaluation.compare results/kg/retrieval_chroma_dense.jsonl results/kg/retrieval_chroma_dense+kg.jsonl
    python -m evaluation.compare results/answers_val_kg.jsonl                # pairs X with X+kg automatically
    python -m evaluation.compare results/answers_a.jsonl=v3 results/answers_b.jsonl=v4 --pairs v3/rewrite:v4/rewrite

Reads per-question rows written by eval_retrieval.py (variant = mode) or eval_answers.py (variant = condition,
plus "+kg" when the concept graph was on). An optional "=tag" after a file prefixes its variants ("v3/rewrite").
Rows are paired by (set, id); only questions present in both variants are compared.

For each metric: mean A, mean B, the difference B - A with a 95% paired bootstrap interval, how many questions
got better / worse / stayed, and a p-value: exact McNemar for yes/no metrics (status_ok, all_found), a paired
sign-flip permutation test for the others. Deterministic (fixed seed), so a report can be regenerated exactly.
"""
from __future__ import annotations

import argparse
import json
import math
import random
from collections import defaultdict
from pathlib import Path

BINARY = {"status_ok", "all_found"}
LOWER_IS_BETTER = {"invalid"}  # invalid citations: fewer is better, so "better" counts questions where B has fewer
METRICS = {"retrieval": ["recall", "all_found"], "answers": ["recall@8", "recall_ctx", "status_ok", "invalid"]}
SEED, RESAMPLES = 20261014, 10_000


def load(spec: str) -> tuple[str, dict[str, dict[tuple, dict]]]:
    """-> (kind, {variant: {(set, id): row}})"""
    path, _, tag = spec.partition("=")
    rows = [json.loads(l) for l in Path(path).open(encoding="utf-8") if l.strip()]
    kind = "retrieval" if rows and "mode" in rows[0] else "answers"
    out: dict[str, dict] = defaultdict(dict)
    for r in rows:
        v = r["mode"] if kind == "retrieval" else r["condition"] + ("+kg" if r.get("kg") else "")
        if tag:
            v = f"{tag}/{v}"
        r = dict(r, invalid=len(r["invalid"])) if kind == "answers" else r
        out[v][(r.get("set"), r["id"])] = r
    return kind, out


def bootstrap_ci(diffs: list[float], rng: random.Random) -> tuple[float, float]:
    n = len(diffs)
    means = sorted(sum(diffs[rng.randrange(n)] for _ in range(n)) / n for _ in range(RESAMPLES))
    return means[int(0.025 * RESAMPLES)], means[int(0.975 * RESAMPLES) - 1]


def mcnemar_p(a: list[float], b: list[float]) -> float:
    """Exact two-sided McNemar test on the discordant pairs."""
    up = sum(1 for x, y in zip(a, b) if y > x)
    down = sum(1 for x, y in zip(a, b) if y < x)
    n = up + down
    if n == 0:
        return 1.0
    k = min(up, down)
    p = sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return min(1.0, 2 * p)


def permutation_p(diffs: list[float], rng: random.Random) -> float:
    """Paired sign-flip test: how often a random sign pattern gives a mean difference at least as large."""
    obs = abs(sum(diffs))
    if obs == 0:
        return 1.0
    hits = sum(abs(sum(d if rng.random() < 0.5 else -d for d in diffs)) >= obs - 1e-12 for _ in range(RESAMPLES))
    return (hits + 1) / (RESAMPLES + 1)


def compare(a: dict[tuple, dict], b: dict[tuple, dict], metrics: list[str]) -> list[dict]:
    keys = sorted(set(a) & set(b))
    out = []
    for m in metrics:
        pairs = [(a[k][m], b[k][m]) for k in keys if a[k].get(m) is not None and b[k].get(m) is not None]
        if not pairs:
            continue
        xa, xb = [float(x) for x, _ in pairs], [float(y) for _, y in pairs]
        diffs = [y - x for x, y in zip(xa, xb)]
        rng = random.Random(SEED)
        lo, hi = bootstrap_ci(diffs, rng)
        out.append({
            "metric": m, "n": len(pairs), "mean_a": sum(xa) / len(xa), "mean_b": sum(xb) / len(xb),
            "diff": sum(diffs) / len(diffs), "ci_low": lo, "ci_high": hi,
            "better": sum((d < 0) if m in LOWER_IS_BETTER else (d > 0) for d in diffs),
            "worse": sum((d > 0) if m in LOWER_IS_BETTER else (d < 0) for d in diffs),
            "same": sum(d == 0 for d in diffs),
            "p": mcnemar_p(xa, xb) if m in BINARY else permutation_p(diffs, random.Random(SEED + 1)),
            "test": "McNemar (exact)" if m in BINARY else "sign-flip permutation",
        })
    return out


def auto_pairs(variants: list[str]) -> list[tuple[str, str]]:
    return [(v, v + "+kg") for v in variants if not v.endswith("+kg") and v + "+kg" in variants]


def markdown(results: list[tuple[str, str, list[dict]]]) -> str:
    lines = ["| A | B | metric | n | A | B | B − A [95% CI] | better / worse / same | p |",
             "|---|---|---|---|---|---|---|---|---|"]
    for va, vb, rows in results:
        for r in rows:
            lines.append(f"| {va} | {vb} | {r['metric']} | {r['n']} | {r['mean_a']:.3f} | {r['mean_b']:.3f} | "
                         f"{r['diff']:+.3f} [{r['ci_low']:+.3f}, {r['ci_high']:+.3f}] | "
                         f"{r['better']} / {r['worse']} / {r['same']} | {r['p']:.3g} |")
    return "\n".join(lines)


def run(specs: list[str], pairs: list[str] | None = None) -> tuple[list, str]:
    kind, merged = None, {}
    for s in specs:
        k, variants = load(s)
        if kind and k != kind:
            raise SystemExit("cannot compare retrieval and answer results with each other")
        kind = k
        for v, rows in variants.items():
            merged.setdefault(v, {}).update(rows)
    if pairs:
        todo = [tuple(p.split(":", 1)) for p in pairs]
    elif len(specs) == 2 and len(merged) == 2 and not auto_pairs(list(merged)):
        todo = [tuple(merged)]
    else:
        todo = auto_pairs(list(merged))
    if not todo:
        raise SystemExit(f"nothing to pair; variants found: {', '.join(merged)} (use --pairs a:b)")
    for va, vb in todo:
        for v in (va, vb):
            if v not in merged:
                raise SystemExit(f"variant {v!r} not found; have: {', '.join(merged)}")
    results = [(va, vb, compare(merged[va], merged[vb], METRICS[kind])) for va, vb in todo]
    return results, markdown(results)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("files", nargs="+", help="result .jsonl files, optionally file=tag")
    ap.add_argument("--pairs", nargs="+", help="variant pairs a:b (default: every X with X+kg)")
    ap.add_argument("--out", type=Path, help="also write the table as markdown and the numbers as JSON")
    args = ap.parse_args()
    results, md = run(args.files, args.pairs)
    print(md)
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.with_suffix(".md").write_text(md + "\n", encoding="utf-8")
        args.out.with_suffix(".json").write_text(json.dumps(
            [{"a": va, "b": vb, "metrics": rows} for va, vb, rows in results], indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
