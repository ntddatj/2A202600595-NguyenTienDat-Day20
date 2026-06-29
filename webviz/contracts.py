"""Pydantic contracts shared by the backend and serialized to the browser."""

from typing import Any, Literal

from pydantic import BaseModel, Field


class EdgeTaken(BaseModel):
    source: str
    target: str
    # dashed = conditional edge out of supervisor; solid = worker loop-back to supervisor
    style: Literal["dashed", "solid"]


class StreamEvent(BaseModel):
    """One step of a workflow run, streamed to the UI as an SSE `data:` line."""

    kind: Literal["node", "baseline", "warning", "error", "done"]
    step: int
    active_node: str | None = None
    edge_taken: EdgeTaken | None = None
    state_snapshot: dict[str, Any] = Field(default_factory=dict)
    metrics: dict[str, Any] = Field(default_factory=dict)
    lane: dict[str, dict[str, Any]] = Field(
        default_factory=lambda: {"control": {}, "observability": {}}
    )
    note: str = ""


class GlossaryItem(BaseModel):
    term: str
    vi: str


class LessonOption(BaseModel):
    label: str
    code: str
    source_ref: str | None = None  # "path:lines" for real excerpts; None for counterfactuals
    narration: str


class Lesson(BaseModel):
    id: str
    title: str
    option_a: LessonOption
    option_b: LessonOption
    glossary: list[GlossaryItem] = Field(default_factory=list)
