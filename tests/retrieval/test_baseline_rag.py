"""Baseline RAG integration tests. Requires running Qdrant on localhost:6333."""

from __future__ import annotations

import socket

import pytest

from src.retrieval.embeddings import embed
from src.retrieval.index_gdocs import COLLECTION, index_gdocs
from src.retrieval.vector_store import VectorStore


def _qdrant_reachable() -> bool:
    try:
        with socket.create_connection(("localhost", 6333), timeout=1):
            return True
    except OSError:
        return False


pytestmark = pytest.mark.skipif(not _qdrant_reachable(), reason="Qdrant not running on localhost:6333")


@pytest.fixture(scope="module")
def indexed():
    n = index_gdocs()
    assert n == 50
    return n


def test_index_gdocs_inserts_all(indexed):
    vs = VectorStore(COLLECTION)
    assert vs.count() == 50


def test_baseline_search_returns_topk(indexed):
    vs = VectorStore(COLLECTION)
    q_vec = embed(["Q3 roadmap"])[0]
    hits = vs.search(q_vec, top_k=5)
    assert len(hits) == 5
    assert all(h["score"] > 0 for h in hits)
    scores = [h["score"] for h in hits]
    assert scores == sorted(scores, reverse=True)


def test_q3_roadmap_query_surfaces_q3_doc(indexed):
    vs = VectorStore(COLLECTION)
    q_vec = embed(["Q3 roadmap launch planning"])[0]
    hits = vs.search(q_vec, top_k=3)
    titles = " ".join(h["payload"]["title"].lower() for h in hits)
    assert "q3" in titles or "roadmap" in titles
