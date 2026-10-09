#!/usr/bin/env python3
"""Gradio front end for rag.answer(). English UI with a German gloss below each element.

    python app.py                 # http://127.0.0.1:7860
    python app.py --share         # temporary public link

Needs data/index (python retrieval.py build) and OPENAI_API_KEY (see rag.py).
"""
from __future__ import annotations

import argparse
import html
import json
import re
from pathlib import Path

import gradio as gr

from laws import TOPIC, TOPIC_DE, corpus_names
from rag import CITE_RE

# The German gloss is always shown: German is the language of the statutes themselves.
# (Planned: an option to switch the main UI language; the German gloss stays.)
DE_STYLE = "color: var(--body-text-color-subdued); font-size: 0.82em; opacity: 0.8;"


def de(text: str) -> str:
    """German line shown, light and small, under the English one."""
    return f'<span style="{DE_STYLE}">{text}</span>'


def bi(en: str, de_text: str) -> str:
    return f"{en}<br>{de(de_text)}"


# Dropdown options stay short (English); their German meaning goes in the info line below.
CONDITION_LABELS = {
    "agent": "4 · Agent (LangGraph)",
    "rewrite": "3 · Hybrid + German rewrite",
    "hybrid": "2 · Hybrid (BM25 + bge-m3)",
    "dense": "1 · Dense only",
}
CONDITION_INFO_DE = ("Suchbedingung — 4: Agent (Teilfragen, Querverweise, erneute Suche) · "
                     "3: Hybrid + Umformulierung ins Deutsche · 2: Hybrid · 1: nur dichte Suche")
STATUS_LABELS = {
    "answer": ("✅ Answer", "Antwort"),
    "refuse_out_of_scope": ("⛔ Out of scope", "Außerhalb des Anwendungsbereichs"),
    "explain_without_judgment": ("⚖️ Requirements only, no individual judgment", "Nur Voraussetzungen, keine Einzelfallbeurteilung"),
}


DISCLAIMER_EN = (
    "**Disclaimer.** GesetzPolyglot is a research prototype, meant only as an aid for understanding "
    "German statutes. Answers are generated automatically and can be incomplete, outdated or wrong, "
    "even when they cite a statute. This is not legal or tax advice and does not replace the "
    "Ausländerbehörde, the BAMF, asylum procedure counselling, a lawyer or a tax advisor. Always check "
    "the cited original text, and for your own case consult a qualified professional. Deadlines in "
    "asylum procedures can be very short: if you have received a decision, get advice immediately. "
    "To the extent permitted by law, the author accepts no "
    "liability for decisions or actions based on these answers, for overreliance on them, or for any "
    "misuse of this tool.")
DISCLAIMER_DE = (
    "<b>Haftungsausschluss.</b> GesetzPolyglot ist ein Forschungsprototyp und dient nur als Hilfe zum "
    "Verständnis deutscher Gesetze. Die Antworten werden automatisch erzeugt und können unvollständig, "
    "veraltet oder falsch sein, auch wenn sie eine Vorschrift zitieren. Dies ist keine Rechts- oder "
    "Steuerberatung und ersetzt weder die Ausländerbehörde noch das BAMF, eine Asylverfahrensberatung oder "
    "eine anwaltliche oder steuerliche Beratung. Prüfen Sie stets den zitierten Originaltext und lassen Sie "
    "sich in Ihrem Einzelfall fachkundig beraten. Fristen im Asylverfahren können sehr kurz sein: Wenn Sie "
    "einen Bescheid erhalten haben, lassen Sie sich sofort beraten. "
    "Soweit gesetzlich zulässig, übernimmt der Autor keine Haftung für Entscheidungen oder Handlungen auf "
    "Grundlage dieser Antworten, für übermäßiges Vertrauen in sie oder für eine missbräuchliche Verwendung "
    "dieses Werkzeugs.")


def linkify(text: str, retrieved: list[dict], valid: set[str]) -> str:
    """Turn valid citations into links to gesetze-im-internet.de; flag invalid ones."""
    urls = {(c["law"], c["section"]): c["source_url"] for c in retrieved}

    def sub(m: re.Match) -> str:
        law, sec, absatz = m.groups()
        label = f"{law} § {sec}" + (f" Abs. {absatz}" if absatz else "")
        if label in valid and (law, sec) in urls:
            return f"[[{label}]]({urls[(law, sec)]})"
        return f"**[{label} ⚠️ not in retrieved text / nicht im Suchergebnis]**"

    return CITE_RE.sub(sub, text)


def describe_trace(trace: list[dict]) -> str:
    """Readable step list: what the pipeline did, in order."""
    lines = []
    for t in trace:
        s = t["step"]
        if s == "detect_lang":
            lines.append(f"Detected language `{t['lang']}`" + "<br>" + de("Sprache der Frage erkannt"))
        elif s == "rewrite":
            lines.append("Rewrote into German queries: " + "; ".join(f"`{q}`" for q in t["queries"])
                         + "<br>" + de("Frage in deutsche juristische Suchanfragen umformuliert"))
        elif s == "plan":
            lines.append("Planned sub-questions: " + "; ".join(t["sub_questions"])
                         + "<br>queries: " + "; ".join(f"`{q}`" for q in t["queries"])
                         + "<br>" + de("In Teilfragen zerlegt, je Teilfrage eine deutsche Suchanfrage"))
        elif s == "retrieve":
            extra = f" (round {t['round']})" if "round" in t else ""
            found = t.get("new") or t.get("hits") or []
            lines.append(f"Searched{extra}: {len(found)} new — " + ", ".join(found)
                         + "<br>" + de("Gesucht und neue Vorschriften gefunden"))
        elif s == "follow_cross_refs":
            got = ", ".join(f"{a['chunk']} ← {a['from']}" for a in t["added"]) or "nothing new"
            lines.append(f"Followed cross-references: {got}" + "<br>"
                         + de("Vorschriften nachgeladen, auf die die gefundenen verweisen"))
        elif s == "check":
            if t["sufficient"]:
                lines.append("Checked: enough to answer" + "<br>" + de("Genug für eine Antwort"))
            else:
                lines.append("Checked: missing → search again for "
                             + "; ".join(f"`{q}`" for q in t["missing_queries"])
                             + "<br>" + de("Nicht genug: erneute Suche nach dem Fehlenden"))
        elif s == "context":
            lines.append(f"Gave {len(t['chunks'])} statute excerpts to the answer step"
                         + "<br>" + de("Vorschriften für die Antwort ausgewählt"))
        elif s == "validate":
            bad = f", ⚠️ invalid: {', '.join(t['invalid'])}" if t["invalid"] else ""
            lines.append(f"Wrote the answer and checked citations: {len(t['valid'])} valid{bad}"
                         + "<br>" + de("Antwort erstellt und geprüft, ob die Zitate im Suchergebnis stehen"))
    return "\n".join(f"{i}. {l}" for i, l in enumerate(lines, 1))


def render(r: dict) -> tuple[str, str, str, dict]:
    st_en, st_de = STATUS_LABELS.get(r["status"], (r["status"], r["status"]))
    head = bi(f"**{st_en}** · language `{r['lang']}` · {r['llm_calls']} LLM calls · "
              f"{r['latency_s']} s · `{r['model']}`",
              f"{st_de} · Sprache `{r['lang']}` · {r['llm_calls']} LLM-Aufrufe · {r['latency_s']} s")
    body = linkify(r["answer"], r["retrieved"], set(r["citations"]))
    warn = ""
    if r["invalid_citations"]:
        cites = ", ".join(r["invalid_citations"])
        warn = "\n\n> " + bi(f"⚠️ Some citations are not in the retrieved statutes: {cites}. "
                             "Do not rely on those parts.",
                             f"Einige Zitate stehen nicht in den gefundenen Vorschriften: {cites}. Verlassen Sie sich auf diese Teile nicht.")
    footer = "\n\n---\n" + r["footer"].replace("\n", "  \n")
    answer_md = f"{head}\n\n{body}{warn}{footer}"

    cited = {(c.split(" § ")[0], c.split(" § ")[1].split(" Abs. ")[0]) for c in r["citations"]}
    parts = []
    for c in r["retrieved"]:
        label = f"{c['law']} § {c['section']}" + (f" Abs. {c['absatz']}" if c["absatz"] else "")
        mark = "📌 " if (c["law"], c["section"]) in cited else ""
        text = html.escape(c["text"]).replace("\n", "<br>")
        via = c.get("via") or ""
        via_html = ""
        if via.startswith("cross-ref"):
            via_html = f" <i>↪ {html.escape(via)}</i> {de('· per Querverweis ergänzt')}"
        elif via:
            via_html = f" <i>🔎 {html.escape(via)}</i>"
        parts.append(f"<details><summary>{mark}<b>{c['rank']}. {label}</b> {html.escape(c['title'])}"
                     f"{via_html}</summary><p>{text}</p><p><a href='{c['source_url']}' target='_blank'>"
                     f"Open on gesetze-im-internet.de</a> {de('· Originaltext')}</p></details>")
    sources_html = "\n".join(parts) or bi("No results", "Keine Ergebnisse")
    return answer_md, sources_html, describe_trace(r["trace"]), {"trace": r["trace"], "condition": r["condition"]}


def load_examples(path: Path, n: int = 8) -> list[list[str]]:
    if not path.exists():
        return [["Can non-EU students work in Germany while studying?"]]
    items = [json.loads(l) for l in path.open(encoding="utf-8") if l.strip()]
    per_type: dict[str, list] = {}
    for it in items:
        per_type.setdefault(it["type"], []).append([it["question"]])
    k = max(n // max(len(per_type), 1), 1)  # a few of each type
    return [q for qs in per_type.values() for q in qs[:k]]


def build_ui(answer_fn, examples: list[list[str]]) -> gr.Blocks:
    def run(question: str, condition_label: str):
        question = (question or "").strip()
        if not question:
            return bi("Please enter a question.", "Bitte geben Sie eine Frage ein."), "", "", {}
        condition = next(k for k, v in CONDITION_LABELS.items() if v == condition_label)
        try:
            return render(answer_fn(question, condition))
        except Exception as e:  # show errors in the UI instead of a blank box
            return bi(f"❌ Error: `{type(e).__name__}: {e}`", "Ein Fehler ist aufgetreten."), "", "", {}

    with gr.Blocks(title="GesetzPolyglot") as demo:
        gr.Markdown(
            "## GesetzPolyglot\n"
            + f"Ask about German {TOPIC} in your language."
            + "<br>" + de(f"Fragen zum deutschen {TOPIC_DE} in Ihrer Sprache") + "\n\n"
            + bi(f"Answers are based on the statutory text of {corpus_names()}. "
                 "Ask in English, German, Korean, Turkish, Arabic or Italian. **This is not legal advice.**",
                 f"Die Antworten beruhen auf dem Gesetzestext von {corpus_names('und')}. Fragen sind auf "
                 "Englisch, Deutsch, Koreanisch, Türkisch, Arabisch oder Italienisch möglich. "
                 "<b>Keine Rechtsberatung.</b>"))
        with gr.Accordion("⚠️ Disclaimer — please read / Haftungsausschluss — bitte lesen", open=True):
            gr.Markdown(bi(DISCLAIMER_EN, DISCLAIMER_DE))
        with gr.Row():
            with gr.Column(scale=3):
                q = gr.Textbox(label="Question", info="Frage", lines=3,
                               placeholder="e.g. How long after receiving an EU Blue Card can I get "
                                           "a settlement permit?  /  z. B. Wie lange nach Erhalt der Blauen Karte EU "
                                           "kann ich eine Niederlassungserlaubnis bekommen?")
            with gr.Column(scale=1):
                cond = gr.Dropdown(list(CONDITION_LABELS.values()), value=CONDITION_LABELS["agent"],
                                   label="Retrieval condition", info=CONDITION_INFO_DE)
                btn = gr.Button("Ask / Fragen", variant="primary")
        out = gr.Markdown()
        with gr.Accordion("Retrieved statutes (📌 = cited) / Gefundene Vorschriften (📌 = zitiert)", open=False):
            src = gr.HTML()
        with gr.Accordion("What the system did / Verarbeitungsschritte", open=False):
            steps = gr.Markdown()
            with gr.Accordion("Raw trace (JSON)", open=False):
                tr = gr.JSON()
        gr.Examples(examples, inputs=q, label="Example questions from the eval set / Beispielfragen aus dem Evaluationsset")
        gr.Markdown("---\n" + bi(DISCLAIMER_EN, DISCLAIMER_DE))
        btn.click(run, [q, cond], [out, src, steps, tr])
        q.submit(run, [q, cond], [out, src, steps, tr])
    return demo


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--index", default="data/index")
    ap.add_argument("--evalset", default="evalset_draft_en.jsonl", help="file for example questions")
    ap.add_argument("--share", action="store_true")
    ap.add_argument("--port", type=int, default=7860)
    args = ap.parse_args()

    if not (Path(args.index) / "emb.npy").exists():
        raise SystemExit(f"index not found in {args.index}: run `python retrieval.py build` first")
    import rag
    from retrieval import LawIndex
    print("loading index and embedding model ...")
    idx = LawIndex.load(Path(args.index))
    idx.embedder  # load bge-m3 now, not on the first question
    rag._PIPELINE = rag.RAG(idx, rag.llm_from_env())
    print(f"ready: {len(idx.chunks)} chunks, vector store {idx.store.name}, model {rag._PIPELINE.llm.name}")

    demo = build_ui(lambda qq, c: rag.answer(qq, c, args.index), load_examples(Path(args.evalset)))
    demo.launch(share=args.share, server_port=args.port)


if __name__ == "__main__":
    main()
