"""Concept graph retrieval: match concepts and nationalities in the question, add the sections they point to.

    python -m gesetzpolyglot.kg "저는 포르투갈 사람인데 독일 지사로 파견되면 어떤 체류허가가 필요한가요?"

kg_search() fuses the normal ranking (dense or hybrid) with the sections from the concept graph via RRF,
so a concept can bring in a section that the embedding never finds (BMG § 17 for "Anmeldung"), while
questions without a known concept keep their ranking. The data lives in concepts.py.
"""
from __future__ import annotations

import argparse
import hashlib
import re
from pathlib import Path

import numpy as np

from .concepts import CONCEPTS, COUNTRY_GROUPS
from .retrieval import RRF_K, LawIndex, cite

SECTION_RE = re.compile(r"^(\S+(?: [IVX]+)?) § (\d+[a-z]?)(?: Abs\. (\d+[a-z]?))?$")
ABSATZ_PER_SECTION = 2  # a whole § brings in its Absätze closest to the question


def parse_section(s: str) -> tuple[str, str, str | None]:
    m = SECTION_RE.match(s)
    if not m:
        raise ValueError(f"bad section: {s!r} (expected 'AufenthG § 18a Abs. 1')")
    return m.group(1), m.group(2), m.group(3)


# A country named as a destination or location is not the asker's nationality: "네덜란드에 여행",
# "travel to the Netherlands", "nach Italien", "in Italia", "إلى هولندا". Origins ("이탈리아에서 이사",
# "von Italien", "from Italy") still count, like nationalities ("포르투갈 사람", "Ich bin Serbe").
_PLACE_BEFORE = re.compile(r"(?:\b(?:to|into|in|visit|visiting|nach|ins|im|a|per|verso)|إلى|الى|في)\s+(?:the\s+|die\s+|den\s+)?$")
_PLACE_AFTER_KO = re.compile(r"^\S*?(?:에|로|으로)(?:\s|도|서는|는|$)")


def _is_place(text: str, start: int, end: int) -> bool:
    before, after = text[max(0, start - 20):start], text[end:end + 6]
    if _PLACE_BEFORE.search(before):
        return True
    return bool(re.search(r"[가-힣]", text[start:end]) and _PLACE_AFTER_KO.match(after))


def _pattern(alias: str) -> re.Pattern:
    """Latin-script aliases must start a word; Korean and Arabic ones may sit inside a word."""
    a = re.escape(alias.lower())
    return re.compile(r"(?<!\w)" + a if re.search(r"[a-zà-ÿ]", alias.lower()) else a)


class ConceptGraph:
    def __init__(self, concepts: dict = CONCEPTS, groups: dict = COUNTRY_GROUPS):
        self.concepts, self.groups = concepts, groups
        self._concept_pats = {cid: [_pattern(a) for lang in ("ko", "en", "de", "ar", "it") for a in c.get(lang, [])]
                              for cid, c in concepts.items()}
        self._country_pats = {(g, code): [_pattern(a) for a in aliases]
                              for g, grp in groups.items() for code, aliases in grp["countries"].items()}

    def match(self, text: str) -> tuple[list[str], list[str]]:
        """Concept ids and country-group names found in the text, in a stable order."""
        t = text.lower()
        concepts = [cid for cid, pats in self._concept_pats.items() if any(p.search(t) for p in pats)]
        groups = list(dict.fromkeys(
            g for (g, _), pats in self._country_pats.items()
            if any(not _is_place(t, m.start(), m.end()) for p in pats for m in p.finditer(t))))
        return concepts, groups

    def sections(self, text: str) -> list[tuple[str, str, str | None]]:
        """Sections to add for this question: country groups first (they decide which law applies),
        then concepts, then sections a concept adds only together with a group or another concept."""
        concepts, groups = self.match(text)
        out: list[str] = []
        for g in groups:
            out += self.groups[g]["sections"]
        for cid in concepts:
            c = self.concepts[cid]
            out += c["sections"]
            for g, secs in c.get("with_group", {}).items():
                if g in groups:
                    out += secs
            for other, secs in c.get("with_concept", {}).items():
                if other in concepts:
                    out += secs
        return [parse_section(s) for s in dict.fromkeys(out)]


def kg_chunks(index: LawIndex, graph: ConceptGraph, query: str) -> list[int]:
    """Chunk positions for the concept graph's sections; for a whole § the Absätze closest to the query."""
    pos = {c["id"]: i for i, c in enumerate(index.chunks)}
    qvec = None
    out: list[int] = []
    for law, sec, absatz in graph.sections(query):
        hits = [pos[c["id"]] for c in index.get_section(law, sec, absatz)]
        if absatz is None and len(hits) > ABSATZ_PER_SECTION:
            if qvec is None:
                qvec = index.embedder.encode([query])[0]
            sims = index.emb[hits] @ qvec
            hits = [hits[i] for i in np.argsort(-sims)[:ABSATZ_PER_SECTION]]
        out += [h for h in hits if h not in out]
    return out


def concepts_version() -> str:
    """Short hash of concepts.py, recorded with every result so a run can be tied to one state of the graph."""
    return hashlib.sha256((Path(__file__).parent / "concepts.py").read_bytes()).hexdigest()[:12]


def fuse_kg(index: LawIndex, graph: ConceptGraph, question: str, ranked: list[dict], k: int) -> tuple[list[dict], dict]:
    """Fuse a ranking (best first; longer than k is better) with the concept graph's chunks for the question.
    Returns the top k and a trace step. With no matching concept the ranking is only cut to k, so a question the
    graph does not know is treated exactly as without the graph."""
    concepts, groups = graph.match(question)
    extra = kg_chunks(index, graph, question)
    step = {"step": "concept_graph", "concepts": concepts, "groups": groups, "added": []}
    if not extra:
        return [{**h, "rank": r + 1} for r, h in enumerate(ranked[:k])], step
    pos = {c["id"]: i for i, c in enumerate(index.chunks)}
    by_pos = {pos[h["id"]]: h for h in ranked}
    score: dict[int, float] = {}
    for ranking in ([pos[h["id"]] for h in ranked], extra):
        for rank, i in enumerate(ranking):
            score[i] = score.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)
    top = sorted(score, key=score.get, reverse=True)[:k]
    out = []
    for r, i in enumerate(top):
        h = {**by_pos.get(i, index.chunks[i]), "rank": r + 1}
        if i in extra:
            h["via"] = h.get("via") or "concept graph"
            if i not in by_pos:  # brought in by the graph alone
                step["added"].append(cite(h))
        out.append(h)
    return out, step


def kg_search(index: LawIndex, graph: ConceptGraph, query: str, k: int = 8, mode: str = "dense",
              pool: int = 50) -> list[dict]:
    """The normal ranking fused with the concept graph's sections (RRF); unchanged if no concept matches."""
    return fuse_kg(index, graph, query, index.search(query, pool, mode=mode), k)[0]


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("query")
    ap.add_argument("--index", type=Path, default=Path("data/index"))
    ap.add_argument("--mode", default="dense", choices=["dense", "hybrid"])
    ap.add_argument("--k", type=int, default=8)
    args = ap.parse_args()
    graph = ConceptGraph()
    concepts, groups = graph.match(args.query)
    print("concepts:", ", ".join(concepts) or "-", "| country groups:", ", ".join(groups) or "-")
    for h in kg_search(LawIndex.load(args.index), graph, args.query, args.k, args.mode):
        print(f"{h['rank']:>2}. [{cite(h)}] {h['title']}" + ("   ← concept graph" if h.get("via") else ""))


if __name__ == "__main__":
    main()
