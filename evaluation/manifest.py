"""What a run depended on, written next to its results so it can be reported and repeated.

    manifest(args=vars(args), evalset_files=[...], index_dir=Path("data/index"))

Records the command, the git commit (and whether the working tree had uncommitted changes), the prompt
version, the LLM, the index (model, chunk count, statute snapshots), the concept graph version, hashes of the
evaluation files, and package versions.
"""
from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
import sys
import time
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PACKAGES = ("sentence-transformers", "torch", "chromadb", "rank-bm25", "openai", "anthropic", "langgraph", "numpy")


def _git() -> dict:
    def run(*cmd: str) -> str:
        try:
            return subprocess.run(["git", *cmd], cwd=ROOT, capture_output=True, text=True, check=True).stdout.strip()
        except (OSError, subprocess.CalledProcessError):
            return ""
    return {"commit": run("rev-parse", "HEAD"), "dirty": bool(run("status", "--porcelain"))}


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


def _versions() -> dict:
    out = {}
    for p in PACKAGES:
        try:
            out[p] = metadata.version(p)
        except metadata.PackageNotFoundError:
            pass
    return out


def manifest(args: dict | None = None, evalset_files: list[Path] = (), index_dir: Path | None = None,
             extra: dict | None = None) -> dict:
    from gesetzpolyglot.kg import concepts_version
    m = {
        "created": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "command": " ".join(sys.argv),
        "args": {k: (str(v) if isinstance(v, Path) else v) for k, v in (args or {}).items()},
        "git": _git(),
        "prompt_version": os.environ.get("PROMPT_VERSION") or _default_prompt_version(),
        "llm": {"provider": os.environ.get("LLM_PROVIDER", "openai"),
                "model": os.environ.get("LLM_MODEL") or os.environ.get("OLLAMA_MODEL") or None},
        "concepts_version": concepts_version(),
        "evalset_files": {str(Path(p).resolve().relative_to(ROOT)): _sha(Path(p)) for p in evalset_files},
        "python": platform.python_version(),
        "packages": _versions(),
    }
    if index_dir and (Path(index_dir) / "meta.json").exists():
        meta = json.loads((Path(index_dir) / "meta.json").read_text(encoding="utf-8"))
        snaps = meta.pop("snapshots", [])
        m["index"] = {**meta, "dir": str(index_dir), "snapshots": snaps,
                      "snapshots_sha": hashlib.sha256("\n".join(snaps).encode()).hexdigest()[:12]}
    if extra:
        m.update(extra)
    return m


def _default_prompt_version() -> str:
    from gesetzpolyglot.prompts import PROMPT_VERSION
    return PROMPT_VERSION


def write_manifest(path: Path, **kwargs) -> dict:
    m = manifest(**kwargs)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(m, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return m
