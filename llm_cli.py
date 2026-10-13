"""Choosing the LLM from the terminal: --provider and --model for every script that calls an LLM.

    python app.py --provider ollama                    # local model (OLLAMA_MODEL, default qwen3:8b)
    python app.py --provider openai --model gpt-5.4    # OpenAI API
    python eval_answers.py --split validation --provider ollama --model llama3:8b

Command-line options win over the environment, which wins over .env.
This module has no heavy imports, so scripts can apply it before importing rag (prompts are chosen at import).
"""
from __future__ import annotations

import argparse
import os
from pathlib import Path

PROVIDERS = ("openai", "anthropic", "ollama")
# per provider: the environment variable that holds its model name, and the default model
MODEL_VAR = {"openai": ("LLM_MODEL", "gpt-5.4-mini"),
             "anthropic": ("LLM_MODEL", "claude-sonnet-5-5"),
             "ollama": ("OLLAMA_MODEL", "qwen3:8b")}


def load_dotenv(path: Path | None = None) -> None:
    """Read KEY=VALUE lines from .env (next to this file) into os.environ.
    Variables already set in the shell win. No extra dependency needed."""
    path = path or Path(__file__).resolve().parent / ".env"
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, val = line.removeprefix("export ").split("=", 1)
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in "'\"":
            val = val[1:-1]
        elif " #" in val:
            val = val.split(" #", 1)[0].rstrip()
        os.environ.setdefault(key.strip(), val)


def add_llm_args(ap: argparse.ArgumentParser) -> None:
    g = ap.add_argument_group("LLM")
    g.add_argument("--provider", choices=PROVIDERS, help="overrides LLM_PROVIDER: openai (API), anthropic (API) "
                                                        "or ollama (local)")
    g.add_argument("--model", help="model for the chosen provider, e.g. gpt-5.4-mini or qwen3:8b")


def apply_llm_args(args: argparse.Namespace) -> None:
    """Put --provider / --model into the environment, where llm_from_env() reads them."""
    load_dotenv()
    if getattr(args, "provider", None):
        os.environ["LLM_PROVIDER"] = args.provider
    if getattr(args, "model", None):
        provider = os.environ.get("LLM_PROVIDER", "openai").lower()
        os.environ[MODEL_VAR.get(provider, ("LLM_MODEL", ""))[0]] = args.model


def model_for(provider: str) -> str:
    var, default = MODEL_VAR[provider]
    return os.environ.get(var) or default
