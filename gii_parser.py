#!/usr/bin/env python3
"""gesetze-im-internet.de XML -> Absatz-level JSONL chunks with cross-references.

    python gii_parser.py fetch                 # download a dated snapshot per law
    python gii_parser.py parse                 # parse the latest snapshot of each law
    python gii_parser.py parse --snapshot 2026-10-04

Layout:
    data/raw/<law>/<YYYY-MM-DD>/xml.zip + manifest.json   (never overwritten)
    data/processed/chunks.jsonl                           (one line per Absatz)
    data/processed/report.json                            (counts, unresolved refs)
"""
from __future__ import annotations

import argparse
import hashlib
import io
import json
import re
import urllib.request
import xml.etree.ElementTree as ET
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from laws import CORPUS, LAWS

BASE = "https://www.gesetze-im-internet.de"
DEFAULT_LAWS = CORPUS
# Full names as they appear in running text ("des Aufenthaltsgesetzes").
LAW_NAMES = {
    "Aufenthaltsgesetz": "AufenthG",
    "Beschäftigungsverordnung": "BeschV",
    "Aufenthaltsverordnung": "AufenthV",
    # frequent external targets, normalized so "Strafgesetzbuches"/"Strafgesetzbuchs" merge
    "Strafgesetzbuch": "StGB",
    "Asylgesetz": "AsylG",
    "Staatsangehörigkeitsgesetz": "StAG",
    "Bürgerlichen Gesetzbuch": "BGB",
    "Dritten Buches Sozialgesetzbuch": "SGB III",
    "Zweiten Buches Sozialgesetzbuch": "SGB II",
    "Zwölften Buches Sozialgesetzbuch": "SGB XII",
    "Schwarzarbeitsbekämpfungsgesetz": "SchwarzArbG",
    "Arbeitnehmerüberlassungsgesetz": "AÜG",
    "Freizügigkeitsgesetz": "FreizügG/EU",
}


# --------------------------------------------------------------------------
# Fetch
# --------------------------------------------------------------------------
def fetch(law: str, root: Path) -> Path:
    now = datetime.now(timezone.utc)
    snap = root / "raw" / law / now.strftime("%Y-%m-%d")
    if (snap / "xml.zip").exists():
        print(f"[{law}] snapshot {snap.name} already exists, skipping")
        return snap
    url = f"{BASE}/{LAWS[law]}/xml.zip"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0 (law-rag)"})
    data = urllib.request.urlopen(req, timeout=60).read()
    snap.mkdir(parents=True, exist_ok=True)
    (snap / "xml.zip").write_bytes(data)
    manifest = {
        "law": law,
        "url": url,
        "fetched_at": now.isoformat(timespec="seconds"),
        "sha256": hashlib.sha256(data).hexdigest(),
    }
    (snap / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"[{law}] saved {len(data):,} bytes -> {snap}")
    return snap


def find_snapshot(law: str, root: Path, snapshot: str | None) -> Path:
    base = root / "raw" / law
    if snapshot:
        return base / snapshot
    snaps = sorted(p for p in base.iterdir() if (p / "xml.zip").exists())
    if not snaps:
        raise FileNotFoundError(f"no snapshot for {law}; run `fetch` first")
    return snaps[-1]


# --------------------------------------------------------------------------
# Text rendering
# --------------------------------------------------------------------------
SKIP_TAGS = {"FnR", "Footnote", "Footnotes", "FnArea"}


def render(el: ET.Element, depth: int = 0) -> str:
    """Flatten an element to text; enumerations (DL/DT/DD) become '1. ...' lines."""
    parts = [el.text or ""]
    for ch in el:
        if ch.tag == "BR":
            parts.append("\n")
        elif ch.tag == "DL":
            parts.append("\n" + render_dl(ch, depth) + "\n")
        elif ch.tag not in SKIP_TAGS:
            parts.append(render(ch, depth))
        parts.append(ch.tail or "")
    return "".join(parts)


def render_dl(dl: ET.Element, depth: int) -> str:
    lines, dt = [], ""
    for ch in dl:
        if ch.tag == "DT":
            dt = render(ch).strip()
        elif ch.tag == "DD":
            lines.append(f"{'  ' * depth}{dt} {clean(render(ch, depth + 1))}")
    return "\n".join(lines)


def clean(s: str) -> str:
    lines = [re.sub(r"[ \t\u00a0]+", " ", ln).rstrip() for ln in s.split("\n")]
    lines = [ln for ln in lines if ln.strip()]
    return "\n".join(lines).strip()


# --------------------------------------------------------------------------
# Cross-references
# --------------------------------------------------------------------------
_ABS = r"(?:Absatz|Absatzes|Absätze|Absätzen|Abs\.)"
_DETKW = r"(?:Satz|Satzes|Sätze|Sätzen|Nummer|Nummern|Nr\.|Buchstabe|Buchstaben|Halbsatz|Alternative)"
HEAD = re.compile(r"§§?\s*(?=\d)")
T_NUM = re.compile(r"\s*(\d+[a-z]?)\b")
T_ABS = re.compile(rf"\s*{_ABS}\s*(?=\d)")
# Separators never cross a line break: "Absatz 3,\n2. Aufenthaltserlaubnis" is a list item.
T_SEP = re.compile(r"[ \t]*(,|und|oder|sowie|bis)[ \t]+(?=\d)")
# "§ 25 Absatz 4 Satz 1 und Absatz 5" -> Absatz 5 of the same section
T_SEP_ABS = re.compile(rf"[ \t]*(?:,|und|oder|sowie|bzw\.)[ \t]+{_ABS}[ \t]+(?=\d)")
# Between two chains that share a law name: "§ 113 Absatz 1, § 115 des StGB"
CHAIN_GAP = re.compile(r"[ \t]*[,;]?[ \t]*(?:und|oder|sowie|bzw\.|in Verbindung mit|i\.[ \t]*V\.[ \t]*m\.)?"
                       r"[ \t]*(?:gegen[ \t]+)?(?:den|die|der|dem|des)?[ \t]*")
# EU-law articles: "Artikel 2 Absatz 18 der Verordnung (EU) ...", also genitive "des Artikels 14 Absatz 1",
# must not become bare Absatz refs
ARTIKEL = re.compile(rf"\bArt(?:ikel[sn]?|\.)\s+\d+[a-z]?"
                     rf"(?:\s+{_ABS}\s+\d+[a-z]?(?:\s*(?:,|und|oder|bis|sowie)\s+(?:{_ABS}\s+)?\d+[a-z]?)*)?")
T_DET = re.compile(rf"\s*{_DETKW}\s+(?:\d+[a-z]?|[a-z])\b")
T_DETKW = re.compile(rf"\s*{_DETKW}\b")
T_SAME = re.compile(r"\s+(?:dieses Gesetzes|dieser Verordnung)\b")
T_LAW = re.compile(
    r"\s+(?:des|der)\s+((?:[A-ZÄÖÜ][\w/\-]*\s+){0,3}?(?=[A-ZÄÖÜ])[\w\-]*?"
    r"(?:[Gg]esetzes|[Gg]esetzbuch(?:e?s)?|[Vv]erordnung|[Oo]rdnung)(?:/EU)?)"
)
T_ABBR = re.compile(r"\s+([A-ZÄÖÜ][A-Za-zÄÖÜäöü]*(?:G|V|GB|O))\b")
ABS_ALONE = re.compile(
    rf"\b{_ABS}\s+(\d+[a-z]?)\b"
    r"((?:[ \t]*(?:,|und|oder|bis)[ \t]+\d+[a-z]?\b(?!\s+(?:Jahr|Monat|Woche|Tag)))*)"
)
# "Absatz 3 der Richtlinie (EU) ..." / "Absatz 2 des Artikels 5" -> not this section
ABS_FOREIGN = re.compile(r"(?:\s+(?:Satz|Nummer|Nr\.)\s+\d+[a-z]?)*\s+(?:der|des)\s+(?:Richtlinie|Verordnung\s*\(|Artikels|Übereinkommens|Abkommens)")


def _law_abbr(name: str) -> str:
    for full, abbr in LAW_NAMES.items():
        if name.startswith(full):
            return abbr
    return name


def _upto(a: str, b: str) -> list[str]:
    """'1','3' -> ['2','3']; non-numeric ranges fall back to just the endpoint."""
    if a.isdigit() and b.isdigit() and 0 < int(b) - int(a) < 30:
        return [str(i) for i in range(int(a) + 1, int(b) + 1)]
    return [b]


def parse_refs(text: str, own_law: str, own_section: str) -> list[dict]:
    """Extract raw references. Ranges and existence checks happen in resolve()."""
    refs: list[dict] = []
    masked = list(text)

    chains: list[dict] = []
    last_end = -1
    for m in HEAD.finditer(text):
        if m.start() < last_end:
            continue
        plural = m.group().startswith("§§")
        pos, level, first, sep = m.end(), "sec", True, None
        items: list[dict] = []
        while True:
            start = pos
            if not first:
                msa = T_SEP_ABS.match(text, pos)
                if msa and items:
                    ma = T_NUM.match(text, msa.end())
                    items.append({"section": items[-1]["section"], "absatz": ma.group(1)})
                    pos, level = ma.end(), "abs"
                    while md := T_DET.match(text, pos):
                        pos, level = md.end(), "det"
                    continue
                ms = T_SEP.match(text, pos)
                if not ms:
                    break
                sep, start = ms.group(1), ms.end()
            mn = T_NUM.match(text, start)
            if not mn:
                break
            num, after = mn.group(1), mn.end()
            f_abs = T_ABS.match(text, after)
            f_det = T_DETKW.match(text, after)
            # Which level does this number belong to?
            if first or f_abs:
                lvl = "sec"
            elif level == "det":
                lvl = "abs" if f_det else "det"
            else:
                lvl = level
            if lvl == "sec" and not first and not plural and not f_abs:
                break  # "§ 18 und 3 ..." -> not a second section
            if lvl == "sec":
                if sep == "bis" and items and items[-1]["absatz"] is None:
                    items[-1]["to"] = num
                else:
                    items.append({"section": num, "absatz": None})
                pos = after
                if f_abs:
                    ma = T_NUM.match(text, f_abs.end())
                    items[-1]["absatz"] = ma.group(1)
                    pos, lvl = ma.end(), "abs"
            elif lvl == "abs":
                prev = items[-1]
                nums = _upto(prev["absatz"] or "", num) if sep == "bis" else [num]
                items += [{"section": prev["section"], "absatz": n} for n in nums]
                pos = after
            else:
                pos = after  # further Satz/Nummer: ignored
            level = lvl
            while md := T_DET.match(text, pos):
                pos, level = md.end(), "det"
            first, sep = False, None

        law = None
        if T_SAME.match(text, pos):
            law = own_law
        else:
            ml = T_LAW.match(text, pos) or T_ABBR.match(text, pos)
            if ml:
                law = _law_abbr(ml.group(1))
        chains.append({"start": m.start(), "end": pos, "law": law,
                       "plural": plural, "items": items})
        last_end = pos

    # A chain without its own law name takes the law of the chain right after it,
    # if only a connector stands between them ("§§ 10, 10a oder § 11 des SchwarzArbG").
    for i in range(len(chains) - 2, -1, -1):
        c, nxt = chains[i], chains[i + 1]
        if c["law"] is None and nxt["law"] is not None:
            gap = CHAIN_GAP.match(text, c["end"])
            if gap and gap.end() == nxt["start"]:
                c["law"] = nxt["law"]
    for c in chains:
        raw = text[c["start"]:c["end"]]
        for it in c["items"]:
            refs.append({**it, "law": c["law"] or own_law, "plural": c["plural"], "raw": raw})
        for i in range(c["start"], c["end"]):
            masked[i] = " "
    for m in ARTIKEL.finditer(text):
        for i in range(m.start(), m.end()):
            masked[i] = " "

    # Bare "Absatz 2" / "Absätze 1 bis 3" -> same section.
    masked_text = "".join(masked)
    for m in ABS_ALONE.finditer(masked_text):
        if ABS_FOREIGN.match(masked_text, m.end()):
            continue
        nums = [m.group(1)]
        for s, n in re.findall(r"(,|und|oder|bis)[ \t]+(\d+[a-z]?)", m.group(2)):
            nums += _upto(nums[-1], n) if s == "bis" else [n]
        for n in nums:
            refs.append({"section": own_section, "absatz": n, "law": own_law,
                         "plural": False, "raw": m.group()})
    return refs


def resolve(chunks: list[dict]) -> list[dict]:
    """Expand ranges, check that targets exist, dedupe. Returns unresolved refs."""
    idx: dict[str, dict[str, set]] = {}
    order: dict[str, list[str]] = {}
    for c in chunks:
        secs = idx.setdefault(c["law"], {})
        if c["section"] not in secs:
            secs[c["section"]] = set()
            order.setdefault(c["law"], []).append(c["section"])
        secs[c["section"]].add(c["absatz"])

    unresolved = []
    for c in chunks:
        out, seen = [], set()
        for r in c.pop("_refs"):
            law, s, a = r["law"], r["section"], r["absatz"]
            if law not in idx:
                cands = [(s, a, "external")]
            else:
                secs = idx[law]
                if "to" in r:
                    o = order[law]
                    if s in secs and r["to"] in secs:
                        names = o[o.index(s): o.index(r["to"]) + 1]
                    else:
                        names = [s, r["to"]]
                    pairs = [(n, None) for n in names]
                else:
                    # "§§ 16b Absatz 1 und 18a": 18a was read as an Absatz -> fix.
                    if a and r["plural"] and a not in secs.get(s, ()) and a in secs:
                        s, a = a, None
                    pairs = [(s, a)]
                cands = []
                for s2, a2 in pairs:
                    ok = s2 in secs and (a2 is None or a2 in secs[s2])
                    cands.append((s2, a2, "ok" if ok else "unresolved"))
            for s2, a2, status in cands:
                if law == c["law"] and s2 == c["section"] and a2 in (None, c["absatz"]):
                    continue  # self-reference
                key = (law, s2, a2)
                if key in seen:
                    continue
                seen.add(key)
                out.append({"law": law, "section": s2, "absatz": a2, "status": status})
                if status == "unresolved":
                    unresolved.append({"chunk": c["id"], "raw": r["raw"],
                                       "target": f"{law} § {s2} Abs. {a2}"})
        c["cross_refs"] = out
    return unresolved


# --------------------------------------------------------------------------
# Parse
# --------------------------------------------------------------------------
ABS_RE = re.compile(r"^\((\d+[a-z]?)\)\s*")
ENBEZ_RE = re.compile(r"§\s*(\d+[a-z]?)")


def parse_law(law: str, snap: Path) -> tuple[list[dict], dict]:
    manifest = {}
    if (snap / "manifest.json").exists():
        manifest = json.loads((snap / "manifest.json").read_text(encoding="utf-8"))
    with zipfile.ZipFile(snap / "xml.zip") as z:
        name = next(n for n in z.namelist() if n.lower().endswith(".xml"))
        root = ET.parse(io.BytesIO(z.read(name))).getroot()

    norms = root.findall("norm")
    stand = "; ".join(
        clean(sa.findtext("standkommentar") or "")
        for sa in norms[0].findall("metadaten/standangabe")
        if sa.findtext("standtyp") == "Stand"
    )
    common = {
        "stand": stand,
        "builddate": root.get("builddate") or norms[0].get("builddate"),
        "fetched_at": manifest.get("fetched_at"),
        "snapshot": snap.name,
    }

    chunks, path, stats = [], [], {"repealed": 0, "skipped_enbez": [], "duplicate_absatz": []}
    seen_ids: set[str] = set()
    for norm in norms:
        meta = norm.find("metadaten")
        gl = meta.find("gliederungseinheit")
        if gl is not None:
            depth = max(len(gl.findtext("gliederungskennzahl") or "") // 3, 1)
            label = clean(f"{gl.findtext('gliederungsbez') or ''} "
                          f"{gl.findtext('gliederungstitel') or ''}".replace("\n", " "))
            path = path[: depth - 1] + [label]
            continue
        enbez = (meta.findtext("enbez") or "").strip()
        if not enbez.startswith("§"):
            continue  # Inhaltsübersicht, Eingangsformel, Anlagen
        m = ENBEZ_RE.fullmatch(enbez)
        if not m:
            stats["skipped_enbez"].append(enbez)  # e.g. "§§ 13 bis 15"
            continue
        section = m.group(1)
        titel = meta.find("titel")
        title = clean(render(titel)).replace("\n", " ") if titel is not None else ""
        content = norm.find("textdaten/text/Content")
        if content is None:
            continue

        absaetze: list[list] = []
        for child in content:
            txt = clean(render(child))
            if not txt:
                continue
            ma = ABS_RE.match(txt) if child.tag == "P" else None
            if ma:
                absaetze.append([ma.group(1), txt[ma.end():]])
            elif absaetze:
                absaetze[-1][1] += "\n" + txt
            else:
                absaetze.append([None, txt])

        gone = [bool(re.fullmatch(r"\(?weggefallen\)?|-", t.strip())) for _, t in absaetze]
        if all(gone):
            stats["repealed"] += 1
            continue
        stats["repealed_absaetze"] = stats.get("repealed_absaetze", 0) + sum(gone)
        for (absatz, text), g in zip(absaetze, gone):
            if g:
                continue  # single repealed Absatz, e.g. "(4) (weggefallen)"
            cid = f"{law}-{section}" + (f"-{absatz}" if absatz else "")
            if cid in seen_ids:
                # the official text sometimes numbers two Absätze alike (AsylG § 31 has two "(3)")
                stats["duplicate_absatz"].append(cid)
                n = 2
                while f"{cid}_{n}" in seen_ids:
                    n += 1
                cid = f"{cid}_{n}"
            seen_ids.add(cid)
            chunks.append({
                "id": cid,
                "law": law,
                "section": section,
                "absatz": absatz,
                "title": title,
                "gliederung": list(path),
                "text": text,
                **common,
                "source_url": f"{BASE}/{LAWS[law]}/__{section}.html",
                "_refs": parse_refs(text, law, section),
            })
    stats.update(chunks=len(chunks), sections=len({c["section"] for c in chunks}))
    return chunks, stats


def run_parse(laws: list[str], root: Path, snapshot: str | None) -> None:
    chunks, report = [], {"laws": {}}
    for law in laws:
        snap = find_snapshot(law, root, snapshot)
        cs, stats = parse_law(law, snap)
        chunks += cs
        report["laws"][law] = {"snapshot": snap.name, **stats}
    unresolved = resolve(chunks)
    counts: dict[str, int] = {}
    for c in chunks:
        for r in c["cross_refs"]:
            counts[r["status"]] = counts.get(r["status"], 0) + 1
    report["cross_refs"] = counts
    report["unresolved"] = unresolved

    out = root / "processed"
    out.mkdir(parents=True, exist_ok=True)
    with (out / "chunks.jsonl").open("w", encoding="utf-8") as f:
        for c in chunks:
            f.write(json.dumps(c, ensure_ascii=False) + "\n")
    (out / "report.json").write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    for law, s in report["laws"].items():
        print(f"[{law}] {s['sections']} sections, {s['chunks']} chunks, "
              f"{s['repealed']} repealed, snapshot {s['snapshot']}")
    print(f"cross_refs: {counts} | unresolved listed in {out / 'report.json'}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["fetch", "parse"])
    ap.add_argument("--laws", nargs="+", default=DEFAULT_LAWS, choices=list(LAWS))
    ap.add_argument("--data", type=Path, default=Path("data"))
    ap.add_argument("--snapshot", help="YYYY-MM-DD; default: latest")
    args = ap.parse_args()
    if args.cmd == "fetch":
        for law in args.laws:
            fetch(law, args.data)
    else:
        run_parse(args.laws, args.data, args.snapshot)


if __name__ == "__main__":
    main()
