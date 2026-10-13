#!/usr/bin/env python3
"""Translate questions before retrieval with a local NLLB-200 model (evaluation experiment, no API).

    python -m evaluation.query_translate                  # translate every evalset question to German, cache the result
    python -m evaluation.query_translate --target arb_Arab # dialect / other languages -> Modern Standard Arabic

Used by eval_retrieval.py --translate. Translations are cached in results/translations_<target>.json,
so the model only runs once per question.

License: the NLLB-200 weights are CC-BY-NC 4.0 (non-commercial). This is an evaluation experiment,
not part of the app.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

MODEL = "facebook/nllb-200-distilled-600M"
CACHE_DIR = Path(__file__).resolve().parent.parent / "results"

# evalset "set" -> NLLB source language code; the dialects have their own codes in NLLB
# (tr-TR, it-IT and ar-EG are sets of the archived v1 evalset)
SRC = {
    "ko": "kor_Hang", "en": "eng_Latn", "de": "deu_Latn", "it": "ita_Latn", "tr-TR": "tur_Latn", "it-IT": "ita_Latn",
    "ar": "arb_Arab",      # Modern Standard Arabic
    "ar-SY": "apc_Arab",   # North Levantine Arabic
    "ar-EG": "arz_Arab",   # Egyptian Arabic
}


class Translator:
    def __init__(self, model: str = MODEL):
        from transformers import AutoModelForSeq2SeqLM, AutoTokenizer
        self.tok = AutoTokenizer.from_pretrained(model)
        self.model = AutoModelForSeq2SeqLM.from_pretrained(model)
        self.model.eval()

    def __call__(self, texts: list[str], src: str, tgt: str, batch: int = 8) -> list[str]:
        import torch
        out = []
        self.tok.src_lang = src
        for i in range(0, len(texts), batch):
            enc = self.tok(texts[i:i + batch], return_tensors="pt", padding=True, truncation=True, max_length=256)
            with torch.no_grad():
                gen = self.model.generate(**enc, forced_bos_token_id=self.tok.convert_tokens_to_ids(tgt),
                                          max_new_tokens=200, num_beams=4)
            out += self.tok.batch_decode(gen, skip_special_tokens=True)
        return out


def cache_path(tgt: str) -> Path:
    return CACHE_DIR / f"translations_{tgt}.json"


def translate_items(items: list[dict], tgt: str = "deu_Latn") -> dict[str, str]:
    """Return {question: translation} for all items, using and updating the cache."""
    path = cache_path(tgt)
    cache = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    todo: dict[str, list[str]] = {}
    for it in items:
        q, src = it["question"], SRC[it.get("set", it["lang"])]
        if q not in cache and src != tgt:
            todo.setdefault(src, []).append(q)
    if todo:
        tr = Translator()
        for src, qs in todo.items():
            qs = list(dict.fromkeys(qs))
            for q, t in zip(qs, tr(qs, src, tgt)):
                cache[q] = t
            print(f"translated {len(qs)} questions {src} -> {tgt}")
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(cache, ensure_ascii=False, indent=1), encoding="utf-8")
    return {it["question"]: cache.get(it["question"], it["question"]) for it in items}


def main() -> None:
    from evaluation.eval_retrieval import EVALSET_DIR
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--target", default="deu_Latn", help="NLLB target language code")
    args = ap.parse_args()
    items = [json.loads(l) for p in sorted(EVALSET_DIR.glob("*.jsonl"))
             for l in p.open(encoding="utf-8") if l.strip()]
    out = translate_items(items, args.target)
    print(f"{len(out)} questions, cache {cache_path(args.target)}")


if __name__ == "__main__":
    main()
