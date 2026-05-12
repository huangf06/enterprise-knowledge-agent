from src.eval.datasets.hotpotqa import load_hotpotqa_subset


def test_hotpotqa_loader_returns_100():
    items = load_hotpotqa_subset(n=100, seed=42)
    assert len(items) == 100
    assert all("question" in x and "answer" in x for x in items)


def test_hotpotqa_loader_deterministic():
    a = load_hotpotqa_subset(n=100, seed=42)
    b = load_hotpotqa_subset(n=100, seed=42)
    assert a == b
