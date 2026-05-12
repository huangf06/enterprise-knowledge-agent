#!/usr/bin/env python3
"""W1 hard gate consolidation. Writes docs/w1_report.md.

Sections:
  1. Multi-source generator counts + determinism
  2. Cross-source entity overlap matrix (30 users by 6 sources)
  3. Nine cross-source injection patterns
  4. Reference baselines (HotpotQA 100, MS Marco 50) cached
  5. Baseline RAG: Qdrant gdocs collection + top-5 for the demo query

Exit code 0 if all gates pass.
"""

from __future__ import annotations

import json
import socket
import sys
from io import StringIO
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.data.entity_consistency import load_users  # noqa: E402
from src.data.generator import generate_all  # noqa: E402
from scripts.verify_synthetic import check_injections, overlap_matrix  # noqa: E402

SYNTH_DIR = REPO_ROOT / "data" / "synthetic"
REPORT_PATH = REPO_ROOT / "docs" / "w1_report.md"
HOTPOTQA_CACHE = REPO_ROOT / "data" / "reference_baselines" / "hotpotqa" / "subset_n100_seed42.json"
MSMARCO_CACHE = REPO_ROOT / "data" / "reference_baselines" / "ms_marco" / "subset_n50_seed42.json"
DEMO_QUERY = "Today's priorities for Sarah Chen"


def _qdrant_reachable() -> bool:
    try:
        with socket.create_connection(("localhost", 6333), timeout=1):
            return True
    except OSError:
        return False


def _section_generator(buf: StringIO) -> bool:
    print("## 1. Multi-source generator", file=buf)
    print("", file=buf)
    stats = generate_all(seed=42, output_dir=SYNTH_DIR, days=7)
    stats2 = generate_all(seed=42, output_dir=REPO_ROOT / ".w1_gate_replay", days=7)
    deterministic = True
    for source in ("slack", "jira", "calendar", "github", "gdocs", "email"):
        a = (SYNTH_DIR / source / f"{source}.json").read_text()
        b = (REPO_ROOT / ".w1_gate_replay" / source / f"{source}.json").read_text()
        if a != b:
            deterministic = False
    # Cleanup replay dir
    import shutil
    shutil.rmtree(REPO_ROOT / ".w1_gate_replay", ignore_errors=True)

    print("Generated under `data/synthetic/`, seed=42, days=7.", file=buf)
    print("", file=buf)
    print("| Source | Count |", file=buf)
    print("|---|---:|", file=buf)
    for key in sorted(stats.keys()):
        print(f"| {key} | {stats[key]} |", file=buf)
    print("", file=buf)
    print(f"Determinism (same seed -> byte-equal files across 6 sources): **{'PASS' if deterministic else 'FAIL'}**", file=buf)
    print("", file=buf)
    return deterministic and stats == stats2


def _section_overlap_matrix(buf: StringIO) -> bool:
    print("## 2. Entity overlap matrix (30 users by 6 sources)", file=buf)
    print("", file=buf)
    users = load_users()
    payloads = {
        s: json.loads((SYNTH_DIR / s / f"{s}.json").read_text())
        for s in ("slack", "jira", "calendar", "github", "gdocs", "email")
    }
    rows = overlap_matrix(payloads, users)
    print("| User | Slack | Jira | Calendar | GitHub | GDocs | Email |", file=buf)
    print("|---|---:|---:|---:|---:|---:|---:|", file=buf)
    all_30 = True
    for name, counts in rows:
        present = all(counts[s] > 0 for s in ("slack", "jira", "calendar", "github", "gdocs", "email"))
        if not present:
            all_30 = False
        print(
            f"| {name} | {counts['slack']} | {counts['jira']} | {counts['calendar']} | "
            f"{counts['github']} | {counts['gdocs']} | {counts['email']} |",
            file=buf,
        )
    print("", file=buf)
    print(f"Full 30 / 30 / 30 / 30 / 30 / 30 overlap: **{'PASS' if all_30 else 'FAIL'}**", file=buf)
    print("", file=buf)
    return all_30


def _section_injections(buf: StringIO) -> bool:
    print("## 3. Nine cross-source injection patterns", file=buf)
    print("", file=buf)
    users = load_users()
    payloads = {
        s: json.loads((SYNTH_DIR / s / f"{s}.json").read_text())
        for s in ("slack", "jira", "calendar", "github", "gdocs", "email")
    }
    checks = check_injections(payloads, users)
    all_pass = True
    for label, ok, detail in checks:
        tag = "PASS" if ok else "FAIL"
        if not ok:
            all_pass = False
        suffix = f" ({detail})" if detail else ""
        print(f"- **[{tag}]** {label}{suffix}", file=buf)
    print("", file=buf)
    return all_pass


def _section_reference_baselines(buf: StringIO) -> bool:
    print("## 4. Reference baselines (retrieval component sanity check, W4)", file=buf)
    print("", file=buf)
    hp_ok = HOTPOTQA_CACHE.exists()
    ms_ok = MSMARCO_CACHE.exists()
    hp_size = HOTPOTQA_CACHE.stat().st_size if hp_ok else 0
    ms_size = MSMARCO_CACHE.stat().st_size if ms_ok else 0
    hp_count = len(json.loads(HOTPOTQA_CACHE.read_text())) if hp_ok else 0
    ms_count = len(json.loads(MSMARCO_CACHE.read_text())) if ms_ok else 0
    print(f"- HotpotQA distractor subset (n=100, seed=42): **{'PASS' if hp_ok and hp_count == 100 else 'FAIL'}**", file=buf)
    print(f"  - cache: `{HOTPOTQA_CACHE.relative_to(REPO_ROOT)}` ({hp_size:,} bytes, {hp_count} items)", file=buf)
    print(f"- MS Marco passage subset (n=50, seed=42): **{'PASS' if ms_ok and ms_count == 50 else 'FAIL'}**", file=buf)
    print(f"  - cache: `{MSMARCO_CACHE.relative_to(REPO_ROOT)}` ({ms_size:,} bytes, {ms_count} items)", file=buf)
    print("", file=buf)
    return hp_ok and hp_count == 100 and ms_ok and ms_count == 50


def _section_baseline_rag(buf: StringIO) -> bool:
    print("## 5. Baseline RAG over GDocs corpus", file=buf)
    print("", file=buf)
    if not _qdrant_reachable():
        print("- **[FAIL]** Qdrant not reachable on `localhost:6333`. Run `docker compose up -d qdrant`.", file=buf)
        print("", file=buf)
        return False
    from src.retrieval.embeddings import embed
    from src.retrieval.index_gdocs import COLLECTION, index_gdocs
    from src.retrieval.vector_store import VectorStore

    n = index_gdocs()
    vs = VectorStore(COLLECTION)
    count = vs.count()
    ok_count = count == 50 and n == 50
    print(f"- Qdrant collection `{COLLECTION}` indexed: **{'PASS' if ok_count else 'FAIL'}** (count={count})", file=buf)
    print("", file=buf)
    print(f"Top-5 for demo query: `{DEMO_QUERY}`", file=buf)
    print("", file=buf)
    print("| Rank | Score | Title |", file=buf)
    print("|---:|---:|---|", file=buf)
    q_vec = embed([DEMO_QUERY])[0]
    hits = vs.search(q_vec, top_k=5)
    for i, h in enumerate(hits, start=1):
        print(f"| {i} | {h['score']:.3f} | {h['payload']['title']} |", file=buf)
    print("", file=buf)
    return ok_count and len(hits) == 5


def main() -> int:
    buf = StringIO()
    print("# W1 hard gate report", file=buf)
    print("", file=buf)
    print(
        "Multi-source synthetic data + retrieval baseline + reference benchmark subsets. "
        "Per design Section 8 W1 gate criteria.",
        file=buf,
    )
    print("", file=buf)

    results: list[tuple[str, bool]] = []
    results.append(("Generator", _section_generator(buf)))
    results.append(("Overlap matrix", _section_overlap_matrix(buf)))
    results.append(("Injections", _section_injections(buf)))
    results.append(("Reference baselines", _section_reference_baselines(buf)))
    results.append(("Baseline RAG", _section_baseline_rag(buf)))

    print("## Summary", file=buf)
    print("", file=buf)
    for name, ok in results:
        tag = "PASS" if ok else "FAIL"
        print(f"- **[{tag}]** {name}", file=buf)
    overall = all(ok for _, ok in results)
    print("", file=buf)
    print(f"### W1 hard gate: **{'PASS' if overall else 'FAIL'}**", file=buf)
    print("", file=buf)

    REPORT_PATH.parent.mkdir(parents=True, exist_ok=True)
    REPORT_PATH.write_text(buf.getvalue())
    sys.stdout.write(buf.getvalue())
    return 0 if overall else 1


if __name__ == "__main__":
    raise SystemExit(main())
