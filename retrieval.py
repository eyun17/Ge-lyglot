#!/usr/bin/env python3
"""Index and search over chunks.jsonl: dense (bge-m3), BM25, hybrid (RRF).

    python retrieval.py build                          # embeds data/processed/chunks.jsonl
    python retrieval.py build --store chroma           # same, plus a Chroma vector store
    python retrieval.py to-chroma                      # Chroma from an existing emb.npy (no re-embedding)
    python retrieval.py search "Blaue Karte Gehalt"    # --mode dense|bm25|hybrid, --k 8, --law BeschV

Dense search runs on one of two vector stores; BM25 always runs in memory.
    numpy   exact cosine over emb.npy (brute force; fine for ~1k chunks)
    chroma  ChromaDB persistent collection (HNSW index, metadata filters)

Index layout (data/index/): chunks.jsonl, emb.npy, meta.json, chroma/ (only with --store chroma)
"""
from __future__ import annotations

import argparse
import json
import re
from pathlib import Path

import numpy as np
from rank_bm25 import BM25Okapi

from laws import CORPUS

MODEL = "BAAI/bge-m3"
RRF_K = 60
COLLECTION = "statutes"
_TOKEN = re.compile(r"\w+")


def tokenize(s: str) -> list[str]:
    return _TOKEN.findall(s.lower())


def index_text(c: dict) -> str:
    """Text that gets embedded / BM25-indexed: citation header + title + body."""
    head = f"{c['law']} § {c['section']}" + (f" Abs. {c['absatz']}" if c.get("absatz") else "")
    return f"{head} {c.get('title', '')}\n{c['text']}"


class STEmbedder:
    def __init__(self, model: str = MODEL, max_len: int = 1024):
        from sentence_transformers import SentenceTransformer
        self.name = model
        self.m = SentenceTransformer(model)
        self.m.max_seq_length = max_len  # keeps CPU indexing feasible

    def encode(self, texts: list[str]) -> np.ndarray:
        v = self.m.encode(texts, normalize_embeddings=True, batch_size=16,
                          show_progress_bar=len(texts) > 50)
        return np.asarray(v, dtype=np.float32)


# --------------------------------------------------------------------------
# Vector stores: same interface, so the rest of the code does not care which one
# --------------------------------------------------------------------------
class NumpyStore:
    """Exact search: one matrix product over all chunk embeddings."""
    name = "numpy"

    def __init__(self, emb: np.ndarray, chunks: list[dict]):
        self.emb, self.laws = emb, np.array([c["law"] for c in chunks])

    def query(self, vec: np.ndarray, n: int, law: str | None = None) -> list[int]:
        sims = self.emb @ vec
        if law:
            sims = np.where(self.laws == law, sims, -np.inf)
        order = np.argsort(-sims)[:n]
        return [int(i) for i in order if np.isfinite(sims[i])]


class ChromaStore:
    """ChromaDB collection holding the same embeddings plus filterable metadata."""
    name = "chroma"

    def __init__(self, path: Path, chunks: list[dict]):
        import chromadb
        self.client = chromadb.PersistentClient(path=str(path))
        self.col = self.client.get_collection(COLLECTION, embedding_function=None)
        self.pos = {c["id"]: i for i, c in enumerate(chunks)}

    @staticmethod
    def write(path: Path, chunks: list[dict], emb: np.ndarray, batch: int = 500) -> None:
        import chromadb
        client = chromadb.PersistentClient(path=str(path))
        if COLLECTION in [c.name for c in client.list_collections()]:
            client.delete_collection(COLLECTION)  # rebuild from scratch, never mix snapshots
        col = client.create_collection(COLLECTION, configuration={"hnsw": {"space": "cosine"}},
                                       embedding_function=None)
        for s in range(0, len(chunks), batch):
            part = chunks[s:s + batch]
            col.add(ids=[c["id"] for c in part],
                    embeddings=emb[s:s + batch].tolist(),
                    documents=[c["text"] for c in part],
                    # Chroma metadata must be str/int/float/bool: no None, no lists
                    metadatas=[{"law": c["law"], "section": c["section"], "absatz": c["absatz"] or "",
                                "title": c.get("title", ""), "snapshot": c.get("snapshot") or ""}
                               for c in part])

    def query(self, vec: np.ndarray, n: int, law: str | None = None) -> list[int]:
        n = min(n, self.col.count())
        r = self.col.query(query_embeddings=[vec.tolist()], n_results=n,
                           where={"law": law} if law else None, include=[])
        return [self.pos[i] for i in r["ids"][0]]


# --------------------------------------------------------------------------
# Index
# --------------------------------------------------------------------------
class LawIndex:
    def __init__(self, chunks: list[dict], emb: np.ndarray, embedder=None, store=None):
        self.chunks, self.emb, self._embedder = chunks, emb, embedder
        self.store = store or NumpyStore(emb, chunks)
        self.bm25 = BM25Okapi([tokenize(index_text(c)) for c in chunks])
        self.by_sec: dict[tuple[str, str], list[int]] = {}
        for i, c in enumerate(chunks):
            self.by_sec.setdefault((c["law"].lower(), c["section"]), []).append(i)

    # ---- persistence -----------------------------------------------------
    @classmethod
    def build(cls, chunks_path: Path, out: Path, embedder=None, store: str = "numpy") -> "LawIndex":
        chunks = [json.loads(l) for l in chunks_path.open(encoding="utf-8") if l.strip()]
        embedder = embedder or STEmbedder()
        emb = embedder.encode([index_text(c) for c in chunks])
        out.mkdir(parents=True, exist_ok=True)
        np.save(out / "emb.npy", emb)  # always kept: exact baseline + used by the agent
        with (out / "chunks.jsonl").open("w", encoding="utf-8") as f:
            for c in chunks:
                f.write(json.dumps(c, ensure_ascii=False) + "\n")
        if store == "chroma":
            ChromaStore.write(out / "chroma", chunks, emb)
        meta = {"model": getattr(embedder, "name", "custom"), "chunks": len(chunks), "store": store,
                "snapshots": sorted({f"{c['law']}:{c.get('snapshot')}" for c in chunks})}
        (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
        return cls.load(out, embedder)

    @staticmethod
    def to_chroma(out: Path) -> None:
        """Add a Chroma store to an index that was built with numpy, reusing emb.npy."""
        chunks = [json.loads(l) for l in (out / "chunks.jsonl").open(encoding="utf-8")]
        ChromaStore.write(out / "chroma", chunks, np.load(out / "emb.npy"))
        meta = json.loads((out / "meta.json").read_text())
        meta["store"] = "chroma"
        (out / "meta.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")

    @classmethod
    def load(cls, out: Path, embedder=None, store: str | None = None) -> "LawIndex":
        chunks = [json.loads(l) for l in (out / "chunks.jsonl").open(encoding="utf-8")]
        emb = np.load(out / "emb.npy")
        meta = json.loads((out / "meta.json").read_text()) if (out / "meta.json").exists() else {}
        store = store or meta.get("store", "numpy")
        if store == "chroma":
            vs = ChromaStore(out / "chroma", chunks)
        elif store == "numpy":
            vs = NumpyStore(emb, chunks)
        else:
            raise ValueError(f"unknown store: {store}")
        return cls(chunks, emb, embedder, vs)

    @property
    def embedder(self):
        if self._embedder is None:
            self._embedder = STEmbedder()
        return self._embedder

    # ---- search ----------------------------------------------------------
    def _dense(self, query: str, n: int, law: str | None = None) -> list[int]:
        return self.store.query(self.embedder.encode([query])[0], n, law)

    def _bm25(self, query: str, n: int, law: str | None = None) -> list[int]:
        scores = self.bm25.get_scores(tokenize(query))
        order = [int(i) for i in np.argsort(-scores) if scores[i] > 0]
        if law:
            order = [i for i in order if self.chunks[i]["law"] == law]
        return order[:n]

    def search(self, query: str, k: int = 8, mode: str = "hybrid", pool: int = 50,
               law: str | None = None) -> list[dict]:
        """law: optional metadata filter, e.g. "BeschV"."""
        if mode == "dense":
            ranked = self._dense(query, k, law)
        elif mode == "bm25":
            ranked = self._bm25(query, k, law)
        elif mode == "hybrid":
            rrf: dict[int, float] = {}
            for lst in (self._dense(query, pool, law), self._bm25(query, pool, law)):
                for rank, i in enumerate(lst):
                    rrf[i] = rrf.get(i, 0.0) + 1.0 / (RRF_K + rank + 1)
            ranked = sorted(rrf, key=rrf.get, reverse=True)[:k]
        else:
            raise ValueError(f"unknown mode: {mode}")
        return [{"rank": r + 1, **self.chunks[i]} for r, i in enumerate(ranked)]

    def get_section(self, law: str, section: str, absatz: str | None = None) -> list[dict]:
        """Direct lookup, e.g. get_section('AufenthG', '18a') or (..., '18a', '2')."""
        section = section.replace("§", "").strip()
        hits = [self.chunks[i] for i in self.by_sec.get((law.lower(), section), [])]
        return [c for c in hits if absatz is None or c["absatz"] == str(absatz)]


def cite(c: dict) -> str:
    return f"{c['law']} § {c['section']}" + (f" Abs. {c['absatz']}" if c.get("absatz") else "")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("cmd", choices=["build", "to-chroma", "search"])
    ap.add_argument("query", nargs="?")
    ap.add_argument("--chunks", type=Path, default=Path("data/processed/chunks.jsonl"))
    ap.add_argument("--index", type=Path, default=Path("data/index"))
    ap.add_argument("--store", choices=["numpy", "chroma"], default=None,
                    help="build: which vector store to create (default numpy); "
                         "search: override the one recorded in meta.json")
    ap.add_argument("--mode", default="hybrid", choices=["dense", "bm25", "hybrid"])
    ap.add_argument("--law", choices=CORPUS, help="metadata filter")
    ap.add_argument("--k", type=int, default=8)
    args = ap.parse_args()
    if args.cmd == "build":
        idx = LawIndex.build(args.chunks, args.index, store=args.store or "numpy")
        print(f"indexed {len(idx.chunks)} chunks -> {args.index} (vector store: {idx.store.name})")
    elif args.cmd == "to-chroma":
        LawIndex.to_chroma(args.index)
        print(f"Chroma store written to {args.index / 'chroma'}; meta.json now uses it")
    else:
        idx = LawIndex.load(args.index, store=args.store)
        print(f"vector store: {idx.store.name}")
        for h in idx.search(args.query, args.k, args.mode, law=args.law):
            print(f"{h['rank']:>2}. [{cite(h)}] {h['title']}\n    {h['text'][:160]!r}")


if __name__ == "__main__":
    main()
