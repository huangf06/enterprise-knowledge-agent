"""Qdrant wrapper for BGE-M3-dim collections."""

from __future__ import annotations

import os
from typing import Any

from qdrant_client import QdrantClient
from qdrant_client.models import Distance, PointStruct, VectorParams

from src.retrieval.embeddings import EMBED_DIM


class VectorStore:
    def __init__(self, collection: str, dim: int = EMBED_DIM, host: str | None = None, port: int | None = None):
        self.host = host or os.environ.get("QDRANT_HOST", "localhost")
        self.port = int(port if port is not None else os.environ.get("QDRANT_PORT", 6333))
        self.client = QdrantClient(host=self.host, port=self.port)
        self.collection = collection
        if not self.client.collection_exists(collection):
            self.client.create_collection(
                collection_name=collection,
                vectors_config=VectorParams(size=dim, distance=Distance.COSINE),
            )

    def reset(self) -> None:
        if self.client.collection_exists(self.collection):
            self.client.delete_collection(self.collection)
        self.client.create_collection(
            collection_name=self.collection,
            vectors_config=VectorParams(size=EMBED_DIM, distance=Distance.COSINE),
        )

    def upsert(self, ids: list[int | str], vectors: list[list[float]], payloads: list[dict[str, Any]]) -> None:
        points = [
            PointStruct(id=pid, vector=v, payload=p)
            for pid, v, p in zip(ids, vectors, payloads, strict=True)
        ]
        self.client.upsert(collection_name=self.collection, points=points, wait=True)

    def search(self, query_vector: list[float], top_k: int = 5) -> list[dict[str, Any]]:
        hits = self.client.query_points(
            collection_name=self.collection, query=query_vector, limit=top_k
        ).points
        return [{"id": h.id, "score": h.score, "payload": h.payload} for h in hits]

    def count(self) -> int:
        return self.client.get_collection(self.collection).points_count or 0
