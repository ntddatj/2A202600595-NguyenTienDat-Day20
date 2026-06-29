"""Load + validate lesson JSON files against the Lesson contract."""

import json
from functools import lru_cache
from pathlib import Path

from webviz.contracts import Lesson

LESSON_DIR = Path(__file__).parent / "lessons"
LESSON_IDS = [
    "abstraction",
    "retry-timeout",
    "max-iterations",
    "search-grounding",
    "route-by-state",
    "control-vs-observability",
    "langgraph-edges",
    "fail-open",
    "benchmark",
]


@lru_cache(maxsize=1)
def load_lessons() -> dict[str, Lesson]:
    out: dict[str, Lesson] = {}
    for lid in LESSON_IDS:
        data = json.loads((LESSON_DIR / f"{lid}.json").read_text(encoding="utf-8"))
        lesson = Lesson.model_validate(data)
        assert lesson.id == lid, f"{lid}.json id mismatch: {lesson.id}"
        out[lid] = lesson
    return out
