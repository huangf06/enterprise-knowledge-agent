#!/usr/bin/env python3
"""Baseline RAG smoke test: index GDocs corpus into Qdrant and run a sample query."""

from __future__ import annotations

import argparse

from src.retrieval.embeddings import embed
from src.retrieval.index_gdocs import COLLECTION, index_gdocs
from src.retrieval.vector_store import VectorStore


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--query", default="Q3 roadmap launch planning")
    parser.add_argument("--top-k", type=int, default=5)
    parser.add_argument("--skip-index", action="store_true", help="Skip re-indexing.")
    args = parser.parse_args()

    if not args.skip_index:
        n = index_gdocs()
        print(f"indexed {n} docs into Qdrant collection '{COLLECTION}'")

    vs = VectorStore(COLLECTION)
    q_vec = embed([args.query])[0]
    hits = vs.search(q_vec, top_k=args.top_k)
    print(f"\nQuery: {args.query!r}")
    print("-" * 72)
    for h in hits:
        print(f"  {h['score']:.3f}  {h['payload']['title']}")


if __name__ == "__main__":
    main()
