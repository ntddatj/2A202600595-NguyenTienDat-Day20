"""Pure mapping from UI toggles to a RunConfig. No I/O, no monkeypatching here."""

from dataclasses import dataclass
from typing import Literal

HARD_CAP = 20  # backend never streams more than this many steps, whatever the toggles say


@dataclass(frozen=True)
class RunConfig:
    runner: Literal["multi", "baseline"]
    llm_retry: bool
    llm_fault: str | None              # None | "fail_first" | "always_fail"
    search_mode: Literal["normal", "empty"]
    search_fault: bool
    withhold_research_notes: bool      # True => researcher's LLM returns content=None => loop
    max_iter_override: int | None      # None => leave settings.max_iterations untouched
    hard_cap: int = HARD_CAP
    live: bool = False                 # True => skip monkeypatch, use REAL OpenAI/Tavily clients
    break_tracing: bool = False        # True => demo real trace_span fail-open in run_stream


def build_run_config(toggles: dict[str, bool], live: bool = False, break_tracing: bool = False) -> RunConfig:
    multi = bool(toggles.get("multi", True))
    retry = bool(toggles.get("retry", True))
    max_iterations = bool(toggles.get("max_iterations", True))
    search = bool(toggles.get("search", True))

    return RunConfig(
        runner="multi" if multi else "baseline",
        llm_retry=retry,
        llm_fault=None if retry else "fail_first",
        search_mode="normal" if search else "empty",
        search_fault=False,
        withhold_research_notes=not max_iterations,
        max_iter_override=None if max_iterations else 9999,
        live=live,
        break_tracing=break_tracing,
    )
