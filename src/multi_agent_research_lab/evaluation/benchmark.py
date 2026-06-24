"""Benchmark utilities for comparing single-agent vs multi-agent runs."""

import re
from time import perf_counter
from typing import Callable

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def _total_cost(state: ResearchState) -> float:
    """Sum cost_usd from all agent_results metadata."""
    total = 0.0
    for result in state.agent_results:
        # cost stored by LLMClient via agent metadata (output_tokens * rate)
        tokens_out = result.metadata.get("output_tokens") or 0
        tokens_in = result.metadata.get("input_tokens") or 0
        # gpt-4o-mini pricing: $0.15/1M input, $0.60/1M output
        total += (tokens_in * 0.15 + tokens_out * 0.60) / 1_000_000
    return total


def _citation_coverage(state: ResearchState) -> float:
    """Fraction of source slots [1]..[N] that appear in the final answer."""
    if not state.final_answer or not state.sources:
        return 0.0
    n = len(state.sources)
    cited = sum(
        1 for i in range(1, n + 1) if re.search(rf"\[{i}\]", state.final_answer)
    )
    return round(cited / n, 2)


def _token_summary(state: ResearchState) -> str:
    total_in = sum(r.metadata.get("input_tokens") or 0 for r in state.agent_results)
    total_out = sum(r.metadata.get("output_tokens") or 0 for r in state.agent_results)
    agents = "→".join(r.agent.value for r in state.agent_results)
    return f"agents=[{agents}] in={total_in} out={total_out}"


def run_benchmark(
    run_name: str,
    query: str,
    runner: Runner,
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Run a single benchmark trial and return the state + rich metrics."""

    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started

    cost = _total_cost(state)
    coverage = _citation_coverage(state)
    notes = _token_summary(state)

    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=round(latency, 3),
        estimated_cost_usd=cost if cost > 0 else None,
        notes=f"citation_coverage={coverage} {notes}",
    )
    return state, metrics
