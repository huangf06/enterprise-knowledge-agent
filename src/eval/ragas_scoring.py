"""F2 RAGAS 4-metric integration.

Wires ragas 0.4 metrics into the eval pipeline:
  - faithfulness:       does the answer entail from the retrieved contexts? (hallucination)
  - answer_relevancy:   does the answer address the user_input?
  - context_precision:  do the contexts contain the reference information?
  - context_recall:     do the contexts cover the full reference?

RAGAS's default LLM is OpenAI; we wire our DeepSeek client via the Anthropic-
compatible endpoint so the daily eval still runs free. Embeddings use BGE-M3
locally so no remote embedding spend either.

Cost note: each metric runs 1-3 LLM calls per scenario internally. A full
4-metric run on 30 scenarios is ~$0.20-0.40 of DeepSeek inference - acceptable
at sprint boundaries but not for daily fast-tier eval.
"""

from __future__ import annotations

import os
from typing import Any

from src.eval.scenarios import Scenario


def _build_llm():
    """Wrap our DeepSeek client as a Langchain-compatible LLM for RAGAS."""
    from langchain_anthropic import ChatAnthropic
    from ragas.llms import LangchainLLMWrapper

    api_key = os.environ.get("DEEPSEEK_API_KEY")
    base_url = os.environ.get("ANTHROPIC_BASE_URL", "https://api.deepseek.com/anthropic")
    model = os.environ.get("LLM_MODEL", "deepseek-v4-pro[1m]")
    llm = ChatAnthropic(
        model_name=model,
        anthropic_api_key=api_key,
        anthropic_api_url=base_url,
        max_tokens=8192,
    )
    return LangchainLLMWrapper(llm)


def _build_embeddings():
    """Wrap BGE-M3 (sentence-transformers) as Langchain embeddings for RAGAS."""
    from langchain_huggingface import HuggingFaceEmbeddings
    from ragas.embeddings import LangchainEmbeddingsWrapper

    return LangchainEmbeddingsWrapper(HuggingFaceEmbeddings(model_name="BAAI/bge-m3"))


def _row_to_sample(scenario: Scenario, row: dict[str, Any]) -> dict[str, Any]:
    """Convert an eval row + scenario into the schema RAGAS expects."""
    tool_history = row.get("tool_history", [])
    contexts = [
        f"[{h.get('tool', '?')}] {h.get('result', '')}"
        for h in tool_history
        if h.get("result")
    ]
    reference = " | ".join(
        list(scenario.expected_topics or [])
        + [scenario.expected_action or ""]
    )
    return {
        "user_input": scenario.question,
        "response": row.get("answer", ""),
        "retrieved_contexts": contexts,
        "reference": reference,
    }


def score_rows(
    rows: list[dict[str, Any]],
    scenarios_by_id: dict[str, Scenario],
    metrics: list[str] | None = None,
) -> dict[str, Any]:
    """Run RAGAS 4-metric eval over a list of (eval row, scenario) pairs.

    Returns: {"per_scenario": [{"id": ..., "metrics": {...}}], "averages": {...}}
    """
    from datasets import Dataset
    from ragas import evaluate
    from ragas.metrics import (
        answer_relevancy,
        context_precision,
        context_recall,
        faithfulness,
    )

    metric_map = {
        "faithfulness": faithfulness,
        "answer_relevancy": answer_relevancy,
        "context_precision": context_precision,
        "context_recall": context_recall,
    }
    metric_names = metrics or list(metric_map)
    chosen = [metric_map[m] for m in metric_names if m in metric_map]

    samples: list[dict[str, Any]] = []
    ids: list[str] = []
    for r in rows:
        if not r.get("ok"):
            continue
        sc = scenarios_by_id.get(r["scenario_id"])
        if sc is None:
            continue
        samples.append(_row_to_sample(sc, r))
        ids.append(r["scenario_id"])

    if not samples:
        return {"per_scenario": [], "averages": {}, "n": 0}

    ds = Dataset.from_list(samples)
    llm = _build_llm()
    emb = _build_embeddings()
    from ragas import RunConfig

    run_config = RunConfig(timeout=600, max_retries=3, max_workers=2)
    result = evaluate(
        ds,
        metrics=chosen,
        llm=llm,
        embeddings=emb,
        run_config=run_config,
        raise_exceptions=False,
    )

    df = result.to_pandas()
    per_scenario = []
    for i, sid in enumerate(ids):
        row_metrics: dict[str, float] = {}
        for m_name in metric_names:
            if m_name in df.columns:
                val = df.iloc[i][m_name]
                try:
                    row_metrics[m_name] = round(float(val), 4)
                except (TypeError, ValueError):
                    row_metrics[m_name] = float("nan")
        per_scenario.append({"id": sid, "metrics": row_metrics})

    averages: dict[str, float] = {}
    for m_name in metric_names:
        if m_name in df.columns:
            try:
                averages[m_name] = round(float(df[m_name].astype(float).mean(skipna=True)), 4)
            except Exception:
                pass
    return {"per_scenario": per_scenario, "averages": averages, "n": len(samples)}


__all__ = ["score_rows"]
