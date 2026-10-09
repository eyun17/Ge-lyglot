"""Run: python test_gii_parser.py   (or: pytest test_gii_parser.py)

Uses a synthetic XML in the gesetze-im-internet.de schema, not the real law text.
"""
import json
import tempfile
import zipfile
from pathlib import Path

from gii_parser import parse_law, parse_refs, resolve


def _targets(text, law="AufenthG", sec="99"):
    return [(r["law"], r["section"], r["absatz"], r.get("to")) for r in parse_refs(text, law, sec)]


def test_single_with_absatz_and_detail():
    assert _targets("nach § 18 Absatz 2 Nummer 1 erteilt") == [("AufenthG", "18", "2", None)]


def test_absatz_list_and_range():
    assert _targets("§ 16b Absatz 1, 5 oder 7") == [
        ("AufenthG", "16b", "1", None), ("AufenthG", "16b", "5", None), ("AufenthG", "16b", "7", None)]
    assert [t[2] for t in _targets("§ 5 Absatz 1 bis 3")] == ["1", "2", "3"]


def test_plural_sections_and_range():
    assert [t[1] for t in _targets("den §§ 18a, 18b und 19c")] == ["18a", "18b", "19c"]
    assert _targets("§§ 18 bis 19c") == [("AufenthG", "18", None, "19c")]


def test_plural_mixed():
    assert _targets("§§ 22, 23 Absatz 1 oder 2, den") == [
        ("AufenthG", "22", None, None), ("AufenthG", "23", "1", None), ("AufenthG", "23", "2", None)]


def test_satz_continuation_is_not_absatz():
    assert _targets("§ 18 Absatz 2 Satz 1 und 3") == [("AufenthG", "18", "2", None)]


def test_single_paragraph_sign_does_not_swallow_numbers():
    assert _targets("§ 18 und 3 Jahre") == [("AufenthG", "18", None, None)]


def test_other_law():
    assert _targets("§ 39 des Aufenthaltsgesetzes", law="BeschV") == [("AufenthG", "39", None, None)]
    assert _targets("§ 2 Absatz 1 des Freizügigkeitsgesetzes/EU")[0][0] == "FreizügG/EU"
    assert _targets("§ 7 des Dritten Buches Sozialgesetzbuch")[0][0] == "SGB III"
    assert _targets("§ 3 des Passgesetzes")[0][0] == "Passgesetzes"  # unknown laws keep the raw name
    assert _targets("§ 4 dieser Verordnung", law="BeschV")[0][0] == "BeschV"
    assert _targets("§ 60 der Ausländer")[0][0] == "AufenthG"


def test_bare_absatz_refers_to_own_section():
    assert _targets("Absatz 1 gilt entsprechend; die Absätze 2 bis 4", sec="18") == [
        ("AufenthG", "18", "1", None), ("AufenthG", "18", "2", None),
        ("AufenthG", "18", "3", None), ("AufenthG", "18", "4", None)]


# --- regressions found on the 2026-10-08 snapshot -----------------------------
def test_absatz_continuation_after_satz():
    assert _targets("§ 25 Abs. 4 Satz 1 und Abs. 5 jedoch") == [
        ("AufenthG", "25", "4", None), ("AufenthG", "25", "5", None)]
    assert _targets("§ 62 Absatz 3a Nummer 1, 5 und 6 sowie Absatz 3b Nummer 1 bis 4") == [
        ("AufenthG", "62", "3a", None), ("AufenthG", "62", "3b", None)]


def test_law_name_shared_across_chains():
    t = _targets("den §§ 176, 177 oder § 184b des Strafgesetzbuches, § 96 dieses Gesetzes")
    assert [x[0] for x in t] == ["StGB"] * 3 + ["AufenthG"]
    assert [x[0] for x in _targets("§ 129a in Verbindung mit § 129b Absatz 1 des Strafgesetzbuchs")] == ["StGB"] * 2
    assert [x[0] for x in _targets("des § 18g Absatz 4 und des § 81a des Aufenthaltsgesetzes", law="BeschV")] == ["AufenthG"] * 2
    t = _targets("§ 404 Absatz 1 oder Absatz 2 Nummer 2 bis 4, 6 bis 13 des Dritten Buches Sozialgesetzbuch")
    assert t == [("SGB III", "404", "1", None), ("SGB III", "404", "2", None)]


def test_list_item_after_newline_is_not_a_reference():
    assert _targets("§ 6 Absatz 1 Nummer 1 und Absatz 3,\n2. Aufenthaltserlaubnis") == [
        ("AufenthG", "6", "1", None), ("AufenthG", "6", "3", None)]


def test_eu_article_absatz_is_not_own_section():
    assert _targets("im Sinne von Artikel 2 Absatz 18 der Verordnung (EU) 2024/1351", sec="2") == []
    assert _targets("nach Absatz 3 der Richtlinie (EU) 2021/1883", sec="18g") == []
    # genitive "Artikels" (frequent in AsylG after the 2024 EU asylum reform)
    assert _targets("im Sinne des Artikels 14 Absatz 1 Buchstabe e der Verordnung (EU) 2024/1347",
                    law="AsylG", sec="3") == []
    assert _targets("des Artikels 18 Absatz 3 sowie des Artikels 30 Absatz 3 der Verordnung (EU) 2024/1348",
                    law="AsylG", sec="12c") == []
    assert _targets("die Voraussetzungen des Artikels 12 Absatz 2 oder Absatz 3 der Richtlinie", sec="60") == []


XML = """<?xml version="1.0" encoding="UTF-8"?>
<dokumente builddate="20261001212121" doknr="BJNR0000000">
<norm doknr="BJNR0000000"><metadaten><jurabk>AufenthG 2004</jurabk><amtabk>AufenthG</amtabk>
<standangabe checked="ja"><standtyp>Neuf</standtyp><standkommentar>Neugefasst</standkommentar></standangabe>
<standangabe checked="ja"><standtyp>Stand</standtyp><standkommentar>Zuletzt geändert durch Art. 1 G v. 1.1.2026</standkommentar></standangabe>
</metadaten><textdaten/></norm>
<norm><metadaten><enbez>Inhaltsübersicht</enbez></metadaten><textdaten><text><Content><P>x</P></Content></text></textdaten></norm>
<norm><metadaten><gliederungseinheit><gliederungskennzahl>020</gliederungskennzahl><gliederungsbez>Kapitel 2</gliederungsbez><gliederungstitel>Einreise</gliederungstitel></gliederungseinheit></metadaten></norm>
<norm><metadaten><gliederungseinheit><gliederungskennzahl>020040</gliederungskennzahl><gliederungsbez>Abschnitt 4</gliederungsbez><gliederungstitel>Erwerb</gliederungstitel></gliederungseinheit></metadaten></norm>
<norm><metadaten><enbez>§ 18</enbez><titel format="parat">Grundsatz</titel></metadaten><textdaten><text format="XML"><Content>
<P>(1) Erster Absatz. Näheres regeln die §§ 18a und 18b.</P>
<P>(2) Die Erteilung setzt voraus, dass
<DL Type="arabic"><DT>1.</DT><DD Font="normal"><LA Size="normal">ein Angebot vorliegt,</LA></DD>
<DT>2.</DT><DD Font="normal"><LA Size="normal">die Zustimmung nach § 39 vorliegt; Absatz 1 bleibt unberührt.</LA></DD></DL></P>
</Content></text></textdaten></norm>
<norm><metadaten><enbez>§ 18a</enbez><titel>Berufsausbildung</titel></metadaten><textdaten><text><Content>
<P>Fachkräften wird nach § 18 Absatz 2 und § 77 ein Titel erteilt.</P></Content></text></textdaten></norm>
<norm><metadaten><enbez>§ 18b</enbez><titel>Akademisch</titel></metadaten><textdaten><text><Content>
<P>(1) Siehe §§ 18 bis 18b dieses Gesetzes und § 2 des Asylgesetzes.</P></Content></text></textdaten></norm>
<norm><metadaten><enbez>§ 19</enbez></metadaten><textdaten><text><Content><P>(weggefallen)</P></Content></text></textdaten></norm>
<norm><metadaten><enbez>§ 39</enbez><titel>Zustimmung</titel></metadaten><textdaten><text><Content>
<P>(1) Text.</P>
<P>(1) Doppelt nummeriert.</P></Content></text></textdaten></norm>
<norm><metadaten><enbez>Anlage</enbez></metadaten><textdaten><text><Content><P>y</P></Content></text></textdaten></norm>
</dokumente>"""


def test_end_to_end():
    with tempfile.TemporaryDirectory() as d:
        snap = Path(d) / "2026-10-04"
        snap.mkdir()
        with zipfile.ZipFile(snap / "xml.zip", "w") as z:
            z.writestr("BJNR0000000.xml", XML)
        (snap / "manifest.json").write_text(json.dumps({"fetched_at": "2026-10-04T10:00:00+00:00"}))
        chunks, stats = parse_law("AufenthG", snap)
        unresolved = resolve(chunks)

    by_id = {c["id"]: c for c in chunks}
    assert list(by_id) == ["AufenthG-18-1", "AufenthG-18-2", "AufenthG-18a", "AufenthG-18b-1", "AufenthG-39-1",
                          "AufenthG-39-1_2"]  # official text numbers two Absätze "(1)"
    assert stats["repealed"] == 1 and stats["duplicate_absatz"] == ["AufenthG-39-1"]
    assert by_id["AufenthG-39-1_2"]["absatz"] == "1"
    c = by_id["AufenthG-18-2"]
    assert c["gliederung"] == ["Kapitel 2 Einreise", "Abschnitt 4 Erwerb"]
    assert c["title"] == "Grundsatz" and c["stand"].startswith("Zuletzt geändert")
    assert c["fetched_at"] == "2026-10-04T10:00:00+00:00"
    assert "1. ein Angebot vorliegt," in c["text"] and not c["text"].startswith("(2)")
    refs = lambda i: [(r["section"], r["absatz"], r["status"]) for r in by_id[i]["cross_refs"]]
    assert refs("AufenthG-18-1") == [("18a", None, "ok"), ("18b", None, "ok")]
    assert refs("AufenthG-18-2") == [("39", None, "ok"), ("18", "1", "ok")]
    assert refs("AufenthG-18a") == [("18", "2", "ok"), ("77", None, "unresolved")]
    # range expanded over document order, self-reference dropped, external law kept
    assert refs("AufenthG-18b-1") == [("18", None, "ok"), ("18a", None, "ok"), ("2", None, "external")]
    assert len(unresolved) == 1 and unresolved[0]["chunk"] == "AufenthG-18a"


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
