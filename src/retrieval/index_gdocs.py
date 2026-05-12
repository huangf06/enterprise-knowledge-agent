"""Index the synthetic GDocs corpus into Qdrant.

W1 sets up the baseline RAG: BGE-M3 + Qdrant cosine. W2+ adds the reranker
and the full per-source tool layer.
"""

from __future__ import annotations

import json
from pathlib import Path

from src.retrieval.embeddings import embed
from src.retrieval.vector_store import VectorStore

DEFAULT_PATH = Path("data/synthetic/gdocs/gdocs.json")
COLLECTION = "gdocs"


def index_gdocs(gdocs_path: Path = DEFAULT_PATH, *, reset: bool = True) -> int:
    data = json.loads(Path(gdocs_path).read_text())
    docs = data["docs"]
    vs = VectorStore(COLLECTION)
    if reset:
        vs.reset()
    texts = [f"{d['title']}\n\n{d['content']}" for d in docs]
    vectors = embed(texts)
    ids = list(range(1, len(docs) + 1))
    payloads = [
        {
            "doc_id": d["doc_id"],
            "title": d["title"],
            "owner": d["owner"],
            "acl": d.get("acl", []),
            "preview": d["content"][:200],
        }
        for d in docs
    ]
    vs.upsert(ids, vectors, payloads)
    return len(docs)


if __name__ == "__main__":  # pragma: no cover
    n = index_gdocs()
    print(f"indexed {n} docs into Qdrant collection '{COLLECTION}'")
