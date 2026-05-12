"""BGE-M3 embedding wrapper. Singleton to amortize the ~1.5GB model load."""

from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

EMBED_MODEL = "BAAI/bge-m3"
EMBED_DIM = 1024


@lru_cache(maxsize=1)
def get_embedder() -> SentenceTransformer:
    return SentenceTransformer(EMBED_MODEL)


def embed(texts: list[str]) -> list[list[float]]:
    return get_embedder().encode(texts, normalize_embeddings=True).tolist()
