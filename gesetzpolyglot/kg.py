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


# Every country name in a question has one of three roles (see nationalities()):
#   place     where something happens, not anyone's nationality: a destination ("네덜란드에 여행", "travel to the
#             Netherlands", "nach Italien", "إلى هولندا"), a place of work or study ("프랑스에서 일하다가",
#             "네덜란드에서 일할"), or a company or institution ("스위스회사", "스페인 본사")
#   relative  the nationality of a family member ("미국인 배우자", "my American spouse", "엄마는 덴마크 사람")
#   asker     everything else ("포르투갈 사람인데", "Ich bin Serbe", "I'm moving from Italy")
# Korean "X에서 왔다" (came from X) stays an origin, so it counts for the asker.
_PLACE_BEFORE = re.compile(r"(?:\b(?:to|into|in|visit|visiting|nach|ins|im|a|per|verso)|إلى|الى|في)\s+(?:the\s+|die\s+|den\s+)?$")
_PLACE_AFTER_KO = re.compile(r"^\S*?(?:에서(?!\s*(?:왔|온))|에|로|으로)(?:\s|도|서는|는|의|$)")
_INSTITUTION_AFTER_KO = re.compile(r"^\S*?\s?(?:회사|기업|본사|지사|대학|정부|은행)")


def _is_place(text: str, start: int, end: int) -> bool:
    before, after = text[max(0, start - 20):start], text[end:end + 8]
    if _PLACE_BEFORE.search(before):
        return True
    if not re.search(r"[가-힣]", text[start:end]):
        return False
    return bool(_PLACE_AFTER_KO.match(after) or _INSTITUTION_AFTER_KO.match(after))


# A country right next to a relative describes that person, not the asker: "미국인 배우자", "my American spouse",
# "mein amerikanischer Ehepartner", "il mio coniuge americano", "جوزي أمريكاني".
_RELATIVES = ("배우자", "아내", "남편", "부인", "와이프", "부모", "자녀", "아이", "아들", "딸", "엄마", "아빠",
              "어머니", "아버지", "형제", "자매",
              "spouse", "wife", "husband", "partner", "parent", "child", "son", "daughter", "mother", "father",
              "mom", "dad", "brother", "sister",
              "ehepartner", "ehefrau", "ehemann", "frau", "mann", "kind", "eltern", "sohn", "tochter", "mutter",
              "vater", "bruder", "schwester",
              "coniuge", "moglie", "marito", "figli", "figlio", "figlia", "genitor", "madre", "padre", "fratello",
              "sorella",
              "زوج", "زوجت", "مرت", "جوز", "ابن", "بنت", "أولاد", "أهل", "أم", "أب", "والد", "أخ", "أخت", "امي", "ابوي")


def _is_relative(text: str, start: int, end: int) -> bool:
    """True if one of the two words before or after the country name is a relative. Korean and Arabic words
    carry particles and prefixes (배우자도, زوجي), so they match by prefix; Latin-script words must be the
    relative itself or its plural ("son" must not match "sono")."""
    before = re.findall(r"\w+", text[max(0, start - 30):start])[-2:]
    after = re.findall(r"\w+", text[end:end + 30])[:2]
    for w in before + after:
        for r in _RELATIVES:
            if re.match(r"[a-z]", r):
                if w in (r, r + "s", r + "e", r + "en", r + "n", r + "er") or (len(r) >= 6 and w.startswith(r)):
                    return True
            elif w.startswith(r):
                return True
    return False


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

    def nationalities(self, text: str) -> tuple[list[str], list[str]]:
        """Country groups of the asker and of family members named in the text; places are left out."""
        t = text.lower()
        asker, relative = [], []
        for (g, _), pats in self._country_pats.items():
            for p in pats:
                for m in p.finditer(t):
                    if _is_place(t, m.start(), m.end()):
                        continue
                    (relative if _is_relative(t, m.start(), m.end()) else asker).append(g)
        return list(dict.fromkeys(asker)), list(dict.fromkeys(relative))

    def match(self, text: str) -> tuple[list[str], list[str]]:
        """Concept ids and the asker's country groups found in the text, in a stable order."""
        t = text.lower()
        concepts = [cid for cid, pats in self._concept_pats.items() if any(p.search(t) for p in pats)]
        return concepts, self.nationalities(text)[0]

    def plan(self, text: str) -> tuple[list[tuple[str, str, str | None]], set[tuple[str, str]]]:
        """Sections to add, best first, and sections to remove from the ranking.

        Order, most specific first: sections a concept adds only together with a nationality group or another
        concept ("spouse" + EU citizen -> FreizügG/EU § 3), then the concepts' own sections, then the groups'.
        A concept's "instead_of" names sections that do not apply once that group is named (an EU citizen's spouse
        is not covered by AufenthG § 30): they are neither added nor kept in the ranking."""
        concepts, asker = self.match(text)
        relative = self.nationalities(text)[1]
        # A family member's nationality matters for family law (an EU citizen's spouse falls under FreizügG/EU),
        # so conditional links look at both; the groups' own sections (e.g. the privileges of AufenthV § 41) apply
        # to the asker only, except EU free movement, which an EU family member brings along.
        family = list(dict.fromkeys(asker + relative))
        groups = list(dict.fromkeys(asker + [g for g in relative if g == "eu"]))
        specific, general, removed = [], [], set()
        for cid in concepts:
            c = self.concepts[cid]
            for g, secs in c.get("with_group", {}).items():
                if g in family:
                    specific += secs
                    removed |= {parse_section(x)[:2] for x in c.get("instead_of", {}).get(g, [])}
            for other, secs in c.get("with_concept", {}).items():
                if other in concepts:
                    specific += secs
            general += c["sections"]
        for g in groups:
            general += self.groups[g]["sections"]
        out = [parse_section(x) for x in dict.fromkeys(specific + general)]
        return [x for x in out if x[:2] not in removed], removed

    def sections(self, text: str) -> list[tuple[str, str, str | None]]:
        return self.plan(text)[0]


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
    removed = graph.plan(question)[1]
    step = {"step": "concept_graph", "concepts": concepts, "groups": groups,
            "relative_groups": graph.nationalities(question)[1], "added": [],
            "removed": sorted({cite(h) for h in ranked if (h["law"], h["section"]) in removed})}
    ranked = [h for h in ranked if (h["law"], h["section"]) not in removed]
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
