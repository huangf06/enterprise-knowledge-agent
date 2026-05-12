from src.eval.datasets.ms_marco import load_msmarco_subset


def test_msmarco_loader_returns_50():
    items = load_msmarco_subset(n=50, seed=42)
    assert len(items) == 50
    assert all("query" in x and "passages" in x for x in items)
    assert all(len(x["relevant_passage_indices"]) >= 1 for x in items)


def test_msmarco_loader_deterministic():
    a = load_msmarco_subset(n=50, seed=42)
    b = load_msmarco_subset(n=50, seed=42)
    assert a == b
