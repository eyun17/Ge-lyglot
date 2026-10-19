#!/usr/bin/env python3
"""Build the folder for a Hugging Face Space (free CPU hardware) from this repository.

    python deploy/make_space.py                 # writes dist/hf_space/
    hf upload <user>/<space-name> dist/hf_space . --repo-type space

The Space runs app.py in its default mode: every user enters their own API key, so the operator pays nothing
for LLM calls. Free accounts can host Gradio Spaces only on ZeroGPU hardware; app.py then embeds questions on the
GPU (use_zero_gpu), which counts against the visitor's daily ZeroGPU quota, not the operator's. Copied: app.py, the gesetzpolyglot package, the example questions and the search index (numpy store
only: 52 MB instead of 212 MB with Chroma, same results at this corpus size). Never copied: .env, results/,
raw statute downloads, the evaluation code.
"""
from __future__ import annotations

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "dist" / "hf_space"

SPACE_README = """---
title: GesetzPolyglot
emoji: ⚖️
colorFrom: yellow
colorTo: red
sdk: gradio
sdk_version: {gradio}
python_version: "3.12"
app_file: app.py
pinned: false
short_description: German residence, work and tax law in your language
---

# GesetzPolyglot

Multilingual question answering over German federal statutes (residence, work, EU free movement, asylum,
citizenship, registration, income tax, social insurance), with citations checked against the retrieved text.

**Bring your own API key** (OpenAI, Claude or Google Gemini): your key is used only for your questions in your
browser session and is not stored. Your question and the statute excerpts found for it are sent to the provider
you choose.

**Not legal or tax advice.** See the disclaimer in the app. Statute texts: consolidated versions from
gesetze-im-internet.de (not the official version; only the Bundesgesetzblatt is binding).

Code, evaluation and documentation: https://github.com/eyun17/Ge-lyglot
"""

# Free Gradio Spaces run on ZeroGPU, which supports torch 2.8 to 2.13 (not newer) and Python 3.10 / 3.12.
# Gradio itself is installed by the Space (sdk_version); `spaces` provides the @spaces.GPU decorator.
REQUIREMENTS = """torch==2.13.0
spaces
numpy
rank_bm25
sentence-transformers
openai
anthropic
langgraph
"""


def main() -> None:
    import gradio
    if OUT.exists():
        shutil.rmtree(OUT)
    (OUT / "data" / "index").mkdir(parents=True)
    (OUT / "evalset").mkdir()
    shutil.copy2(ROOT / "app.py", OUT / "app.py")
    shutil.copytree(ROOT / "gesetzpolyglot", OUT / "gesetzpolyglot",
                    ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
    shutil.copy2(ROOT / "evalset" / "en.jsonl", OUT / "evalset" / "en.jsonl")  # example questions in the app
    for f in ("chunks.jsonl", "emb.npy"):
        shutil.copy2(ROOT / "data" / "index" / f, OUT / "data" / "index" / f)
    meta = json.loads((ROOT / "data" / "index" / "meta.json").read_text(encoding="utf-8"))
    meta["store"] = "numpy"
    (OUT / "data" / "index" / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    (OUT / "README.md").write_text(SPACE_README.format(gradio=gradio.__version__), encoding="utf-8")
    (OUT / "requirements.txt").write_text(REQUIREMENTS, encoding="utf-8")

    leaked = [p for p in OUT.rglob("*") if p.name == ".env" or "sk-" in (p.read_text(errors="ignore") if
              p.is_file() and p.suffix in (".py", ".md", ".txt", ".json") and p.stat().st_size < 2_000_000 else "")]
    if leaked:
        raise SystemExit(f"refusing: something that looks like a secret is in {leaked}")
    size = sum(p.stat().st_size for p in OUT.rglob("*") if p.is_file()) / 1e6
    print(f"written {OUT} ({size:.0f} MB). Upload with:\n  hf upload <user>/<space-name> {OUT} . --repo-type space")


if __name__ == "__main__":
    main()
