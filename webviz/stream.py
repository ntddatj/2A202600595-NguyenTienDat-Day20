"""Run the REAL workflow with mock clients monkeypatched in, yielding StreamEvents."""

import contextlib
from collections.abc import Iterator
from functools import partial

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.services.llm_client import LLMClient  # real client for Live mode
# Reuse the lab's OWN metric functions (DRY) so the live panel, the exported
# report, and src all compute cost/coverage identically. They are underscore-
# private but importing within the package is acceptable given src/ is read-only.
from multi_agent_research_lab.evaluation.benchmark import (
    _citation_coverage as _coverage,
    _total_cost as _cost,
)

from webviz.contracts import EdgeTaken, StreamEvent
from webviz.fakes import FakeLLMClient, FakeSearchClient
from webviz.scenarios import RunConfig

# Modules where the names are actually looked up at call time.
import multi_agent_research_lab.agents.analyst as _analyst
import multi_agent_research_lab.agents.researcher as _researcher
import multi_agent_research_lab.agents.writer as _writer
import multi_agent_research_lab.services.llm_client as _llm_mod
import multi_agent_research_lab.services.search_client as _search_mod

_WORKERS = {"researcher", "analyst", "writer"}

_BASELINE_SYSTEM = (
    "You are a research assistant. Given a query, provide a thorough, well-structured answer "
    "with key facts and insights. Be concise but complete."
)


def _llm_factory(cfg: RunConfig):
    return partial(FakeLLMClient, fault=cfg.llm_fault, retry=cfg.llm_retry)


def _search_factory(cfg: RunConfig):
    return partial(FakeSearchClient, mode=cfg.search_mode, fault=cfg.search_fault)


@contextlib.contextmanager
def mock_clients(cfg: RunConfig) -> Iterator[None]:
    """Patch every place LLMClient/SearchClient is resolved, then restore in finally."""
    llm = _llm_factory(cfg)
    search = _search_factory(cfg)
    saved: list[tuple[object, str, object]] = []

    def patch(mod: object, name: str, value: object) -> None:
        if hasattr(mod, name):
            saved.append((mod, name, getattr(mod, name)))
            setattr(mod, name, value)

    settings = get_settings()
    saved_max = settings.max_iterations
    try:
        patch(_researcher, "LLMClient", llm)
        patch(_researcher, "SearchClient", search)
        patch(_analyst, "LLMClient", llm)
        patch(_writer, "LLMClient", llm)
        patch(_llm_mod, "LLMClient", llm)
        patch(_search_mod, "SearchClient", search)
        if cfg.max_iter_override is not None:
            settings.max_iterations = cfg.max_iter_override  # pydantic: no validate_assignment
        if cfg.withhold_research_notes:
            _orig_run = _researcher.ResearcherAgent.run
            def _looping_run(self, state):
                state = _orig_run(self, state)
                state.research_notes = None  # force supervisor to keep routing to researcher
                return state
            patch(_researcher.ResearcherAgent, "run", _looping_run)
        yield
    finally:
        for mod, name, old in saved:
            setattr(mod, name, old)
        settings.max_iterations = saved_max


def _metrics(state: ResearchState) -> dict:
    return {
        "estimated_cost_usd": _cost(state),
        "citation_coverage": _coverage(state),
        "agents": [r.agent.value for r in state.agent_results],
        "sources": len(state.sources),
    }


def _snapshot(state: ResearchState) -> dict:
    return {
        "request": {"query": state.request.query},
        "iteration": state.iteration,
        "route_history": list(state.route_history),
        "sources": [s.model_dump() for s in state.sources],
        "research_notes": state.research_notes,
        "analysis_notes": state.analysis_notes,
        "final_answer": state.final_answer,
        "errors": list(state.errors),
    }


def _lane(state: ResearchState) -> dict:
    return {
        "control": {"route_history": list(state.route_history), "iteration": state.iteration},
        "observability": {"trace": list(state.trace)},
    }


def _edge_for(node: str, state: ResearchState) -> EdgeTaken | None:
    if node == "supervisor":
        # a supervisor tick that came back from a worker is a solid loop-back
        if len(state.route_history) >= 2:
            return EdgeTaken(source=state.route_history[-2], target="supervisor", style="solid")
        return None
    if node in _WORKERS:
        return EdgeTaken(source="supervisor", target=node, style="dashed")
    return None


def _run_baseline(query: str, cfg: RunConfig) -> Iterator[StreamEvent]:
    state = ResearchState(request=ResearchQuery(query=query))
    yield StreamEvent(kind="baseline", step=0, active_node="baseline",
                      state_snapshot=_snapshot(state), note="Một lần gọi LLM duy nhất (single-agent).")
    client = LLMClient() if cfg.live else FakeLLMClient(fault=cfg.llm_fault, retry=cfg.llm_retry)
    resp = client.complete(_BASELINE_SYSTEM, query)
    state.final_answer = resp.content
    state.agent_results.append(AgentResult(agent=AgentName.WRITER, content=resp.content or "",
                                           metadata={"input_tokens": resp.input_tokens,
                                                     "output_tokens": resp.output_tokens}))
    yield StreamEvent(kind="done", step=1, active_node="baseline",
                      state_snapshot=_snapshot(state), metrics=_metrics(state),
                      lane=_lane(state), note="Baseline xong: không có sources nên coverage = 0.")


def run_stream(query: str, cfg: RunConfig) -> Iterator[StreamEvent]:
    """Yield one StreamEvent per node; wrap any runtime error as a kind='error' event."""
    if cfg.runner == "baseline":
        try:
            yield from _run_baseline(query, cfg)
        except Exception as exc:  # noqa: BLE001 - never let the server 500
            yield StreamEvent(kind="error", step=0, note=f"Baseline lỗi: {exc}")
        return

    step = 0
    last_state: ResearchState | None = None
    # Live mode: skip all monkeypatching so the REAL OpenAI/Tavily clients are used.
    client_ctx = contextlib.nullcontext() if cfg.live else mock_clients(cfg)
    try:
        with client_ctx:
            compiled = MultiAgentWorkflow().build()
            state = ResearchState(request=ResearchQuery(query=query))
            for chunk in compiled.stream({"research_state": state}):
                for node, payload in chunk.items():
                    rs: ResearchState = payload["research_state"]
                    last_state = rs
                    step += 1
                    if step > cfg.hard_cap:
                        yield StreamEvent(
                            kind="warning", step=step, active_node=node,
                            state_snapshot=_snapshot(rs), metrics=_metrics(rs), lane=_lane(rs),
                            note=f"Đã chạm trần cứng {cfg.hard_cap} bước — dừng để tránh vòng lặp vô hạn "
                                 "(guardrail / hàng rào an toàn của backend).",
                        )
                        return
                    yield StreamEvent(
                        kind="node", step=step, active_node=node, edge_taken=_edge_for(node, rs),
                        state_snapshot=_snapshot(rs), metrics=_metrics(rs), lane=_lane(rs),
                        note=f"Node {node} vừa chạy (iteration {rs.iteration}).",
                    )
    except Exception as exc:  # noqa: BLE001
        yield StreamEvent(kind="error", step=step + 1, note=f"Run lỗi: {exc}",
                          state_snapshot=_snapshot(last_state) if last_state else {})
        return

    final_state = last_state if last_state is not None else ResearchState(request=ResearchQuery(query=query))
    yield StreamEvent(kind="done", step=step + 1, active_node=None,
                      state_snapshot=_snapshot(final_state), metrics=_metrics(final_state),
                      lane=_lane(final_state), note="Workflow hoàn tất.")
