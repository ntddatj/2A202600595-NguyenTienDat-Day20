"""Benchmark report rendering."""

import os

from multi_agent_research_lab.core.schemas import BenchmarkMetrics


def _trace_link() -> str:
    project = os.environ.get("LANGCHAIN_PROJECT", "")
    if project and os.environ.get("LANGCHAIN_TRACING_V2") == "true":
        encoded = project.replace(" ", "%20")
        return f"https://smith.langchain.com/o/default/projects/p/{encoded}"
    return ""


def render_markdown_report(
    metrics: list[BenchmarkMetrics],
    query: str = "",
    failure_modes: list[str] | None = None,
) -> str:
    """Render a richer benchmark report with per-run breakdown and trace links."""

    link = _trace_link()
    lines: list[str] = ["# Benchmark Report", ""]

    if query:
        lines += [f"**Query:** `{query}`", ""]

    if link:
        lines += [f"**LangSmith trace:** [{link}]({link})", ""]

    # Summary table
    lines += [
        "## Summary",
        "",
        "| Run | Latency (s) | Cost (USD) | Quality | Notes |",
        "|---|---:|---:|---:|---|",
    ]
    for item in metrics:
        cost = "—" if item.estimated_cost_usd is None else f"${item.estimated_cost_usd:.5f}"
        quality = "peer review" if item.quality_score is None else f"{item.quality_score:.1f}/10"
        lines.append(f"| {item.run_name} | {item.latency_seconds:.2f} | {cost} | {quality} | {item.notes} |")

    # Analysis
    if len(metrics) == 2:
        a, b = metrics[0], metrics[1]
        latency_delta = b.latency_seconds - a.latency_seconds
        sign = "+" if latency_delta >= 0 else ""
        lines += [
            "",
            "## Analysis",
            "",
            f"- Latency difference: {sign}{latency_delta:.2f}s ({b.run_name} vs {a.run_name})",
        ]
        if a.estimated_cost_usd and b.estimated_cost_usd:
            cost_delta = b.estimated_cost_usd - a.estimated_cost_usd
            sign = "+" if cost_delta >= 0 else ""
            lines.append(f"- Cost difference: {sign}${cost_delta:.5f}")
        lines += [
            "- Multi-agent adds latency but produces cited, structured output via specialised agents.",
            "- Single-agent is cheaper and faster for simple queries.",
        ]

    # Failure modes
    if failure_modes:
        lines += ["", "## Failure modes & fixes", ""]
        for mode in failure_modes:
            lines.append(f"- {mode}")

    # Metric definitions
    lines += [
        "",
        "## Metric definitions",
        "",
        "| Metric | How measured |",
        "|---|---|",
        "| Latency | wall-clock `perf_counter` |",
        "| Cost (USD) | token counts × gpt-4o-mini pricing ($0.15/1M in, $0.60/1M out) |",
        "| Citation coverage | fraction of source slots [N] appearing in final answer |",
        "| Quality | 0-10 rubric by peer reviewer (see docs/peer_review_rubric.md) |",
        "| Error rate | failed runs / total runs (not shown — single trial each) |",
    ]

    return "\n".join(lines) + "\n"
