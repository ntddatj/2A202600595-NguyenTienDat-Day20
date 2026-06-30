"""FastAPI app: serves the GUI and streams real workflow runs."""

from dataclasses import replace
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from sse_starlette.sse import EventSourceResponse

from multi_agent_research_lab.core.schemas import AgentName, AgentResult, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import (
    run_benchmark,
    _total_cost as _cost,
    _citation_coverage as _coverage,
)
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow

from webviz.contracts import StreamEvent
from webviz.fakes import FakeLLMClient
from webviz.lessons_loader import load_lessons
from webviz.scenarios import build_run_config
from webviz.stream import mock_clients, run_stream, _BASELINE_SYSTEM

STATIC = Path(__file__).parent / "static"

app = FastAPI(title="webviz teaching GUI")
# check_dir=False prevents crash at import time if static/ doesn't exist yet (Task 8 adds it).
app.mount("/static", StaticFiles(directory=str(STATIC), check_dir=False), name="static")


class RunRequest(BaseModel):
    query: str = Field(min_length=1)
    live: bool = False
    break_tracing: bool = False
    toggles: dict[str, bool] = Field(default_factory=dict)


class ReportRequest(BaseModel):
    query: str = Field(min_length=1)
    toggles: dict[str, bool] = Field(default_factory=dict)


class CompareRequest(BaseModel):
    query: str = Field(min_length=1)
    toggles: dict[str, bool] = Field(default_factory=dict)


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(STATIC / "index.html"))


@app.get("/lessons")
def lessons() -> list[dict]:
    return [lesson.model_dump() for lesson in load_lessons().values()]


@app.post("/run")
async def run(req: RunRequest) -> EventSourceResponse:
    cfg = build_run_config(req.toggles, req.live, req.break_tracing)  # live=True => run_stream uses REAL clients

    async def gen():
        if req.live:
            from multi_agent_research_lab.core.config import get_settings
            if not get_settings().openai_api_key:
                yield {"data": StreamEvent(kind="error", step=0,
                       note="Live mode cần OPENAI_API_KEY. Hãy tắt Live để chạy Mock offline.").model_dump_json()}
                return
        for event in run_stream(req.query, cfg):
            yield {"data": event.model_dump_json()}

    return EventSourceResponse(gen())


def _runner(cfg, runner_kind):
    # report compares HEALTHY baseline vs multi (no injected faults) for a fair benchmark
    healthy = replace(cfg, runner=runner_kind, withhold_research_notes=False,
                      max_iter_override=None, llm_fault=None,
                      search_mode="normal", llm_retry=True)

    def run_one(query: str) -> ResearchState:
        with mock_clients(healthy):
            if runner_kind == "baseline":
                state = ResearchState(request=ResearchQuery(query=query))
                resp = FakeLLMClient().complete(_BASELINE_SYSTEM, query)
                state.final_answer = resp.content
                state.agent_results.append(AgentResult(agent=AgentName.WRITER, content=resp.content or "",
                                           metadata={"input_tokens": resp.input_tokens,
                                                     "output_tokens": resp.output_tokens}))
                return state
            return MultiAgentWorkflow().run(ResearchState(request=ResearchQuery(query=query)))

    return run_one


@app.post("/report")
def report(req: ReportRequest) -> PlainTextResponse:
    cfg = build_run_config(req.toggles)
    _, baseline_m = run_benchmark("single-agent-baseline", req.query, _runner(cfg, "baseline"))
    _, multi_m = run_benchmark("multi-agent", req.query, _runner(cfg, "multi"))
    md = render_markdown_report([baseline_m, multi_m], query=req.query)
    return PlainTextResponse(md, media_type="text/markdown")


@app.post("/compare")
def compare(req: CompareRequest) -> dict:
    import time

    cfg = build_run_config(req.toggles)

    t0 = time.perf_counter()
    single_state = _runner(cfg, "baseline")(req.query)
    single_latency = time.perf_counter() - t0

    t0 = time.perf_counter()
    multi_state = _runner(cfg, "multi")(req.query)
    multi_latency = time.perf_counter() - t0

    return {
        "single": {
            "latency_seconds": round(single_latency, 3),
            "estimated_cost_usd": _cost(single_state),
            "citation_coverage": _coverage(single_state),
            "agents": len(single_state.agent_results),
        },
        "multi": {
            "latency_seconds": round(multi_latency, 3),
            "estimated_cost_usd": _cost(multi_state),
            "citation_coverage": _coverage(multi_state),
            "agents": len(multi_state.agent_results),
        },
    }
