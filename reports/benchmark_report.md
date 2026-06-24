# Benchmark Report

**Query:** `What is LangGraph and how does it compare to simple LLM chains for building AI agents?`

## Summary

| Run | Latency (s) | Cost (USD) | Quality | Notes |
|---|---:|---:|---:|---|
| single-agent-baseline | 8.39 | $0.00043 | peer review | citation_coverage=0.0 agents=[writer] in=64 out=707 |
| multi-agent-workflow | 33.42 | $0.00123 | peer review | citation_coverage=1.0 agents=[researcher→analyst→writer] in=0 out=2044 |

## Analysis

- Latency difference: +25.03s (multi-agent-workflow vs single-agent-baseline)
- Cost difference: +$0.00079
- Multi-agent adds latency but produces cited, structured output via specialised agents.
- Single-agent is cheaper and faster for simple queries.

## Failure modes & fixes

- Researcher returns 0 results (Tavily rate limit) → fix: add mock fallback in SearchClient
- Writer hallucinates citations [N] that don't exist → fix: validate citation index ≤ len(sources)
- Max iterations hit before Writer runs → fix: increase MAX_ITERATIONS or lock routing order
- LLM timeout during Analyst step → fix: tenacity retry in LLMClient handles this (3 attempts, exponential backoff)

## Metric definitions

| Metric | How measured |
|---|---|
| Latency | wall-clock `perf_counter` |
| Cost (USD) | token counts × gpt-4o-mini pricing ($0.15/1M in, $0.60/1M out) |
| Citation coverage | fraction of source slots [N] appearing in final answer |
| Quality | 0-10 rubric by peer reviewer (see docs/peer_review_rubric.md) |
| Error rate | failed runs / total runs (not shown — single trial each) |
