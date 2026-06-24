"""Command-line entrypoint for the lab starter."""

import time
from typing import Annotated

import typer
from rich.console import Console
from rich.panel import Panel

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.errors import StudentTodoError
from multi_agent_research_lab.core.schemas import BenchmarkMetrics, ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.observability.tracing import configure_tracing
from multi_agent_research_lab.services.llm_client import LLMClient

app = typer.Typer(help="Multi-Agent Research Lab starter CLI")
console = Console()

_BASELINE_SYSTEM = (
    "You are a research assistant. Given a query, provide a thorough, well-structured answer "
    "with key facts and insights. Be concise but complete."
)


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)
    configure_tracing()


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a single-agent baseline using a real LLM call and record metrics."""

    _init()
    request = ResearchQuery(query=query)
    state = ResearchState(request=request)

    llm = LLMClient()
    t0 = time.perf_counter()
    response = llm.complete(system_prompt=_BASELINE_SYSTEM, user_prompt=request.query)
    latency = time.perf_counter() - t0

    state.final_answer = response.content
    metrics = BenchmarkMetrics(
        run_name="single-agent-baseline",
        latency_seconds=round(latency, 3),
        estimated_cost_usd=response.cost_usd,
        notes=f"input_tokens={response.input_tokens} output_tokens={response.output_tokens}",
    )

    console.print(Panel.fit(state.final_answer, title="Single-Agent Baseline"))
    console.print(Panel.fit(metrics.model_dump_json(indent=2), title="Benchmark Metrics"))


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the multi-agent workflow skeleton."""

    _init()
    state = ResearchState(request=ResearchQuery(query=query))
    workflow = MultiAgentWorkflow()
    try:
        result = workflow.run(state)
    except StudentTodoError as exc:
        console.print(Panel.fit(str(exc), title="Expected TODO", style="yellow"))
        raise typer.Exit(code=2) from exc
    console.print(result.model_dump_json(indent=2))


if __name__ == "__main__":
    app()
