"""Deterministic, offline, signature-compatible doubles for LLMClient / SearchClient."""

from dataclasses import dataclass

from multi_agent_research_lab.core.schemas import SourceDocument


@dataclass
class FakeLLMResponse:
    content: str | None
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


def _role_of(system_prompt: str) -> str:
    s = system_prompt.lower()
    if "research specialist" in s:
        return "researcher"
    if "critical analyst" in s:
        return "analyst"
    if "technical writer" in s:
        return "writer"
    return "baseline"


_CONTENT = {
    "researcher": "1. Fact A [1]\n2. Fact B [2]\n3. Fact C [3]",
    "analyst": "## Claims\n- Strong: A\n- Weak: B\n## Strength\nModerate.",
    "writer": "Answer grounded in sources [1][2][3]. Structured and cited.",
    "baseline": "A single-pass answer with no retrieved sources and no citations.",
}
# deterministic, stable per role (in_tokens, out_tokens)
_TOKENS = {
    "researcher": (120, 60),
    "analyst": (90, 70),
    "writer": (150, 110),
    "baseline": (40, 90),
}
_COST_IN = 0.15 / 1_000_000
_COST_OUT = 0.60 / 1_000_000


class FakeLLMClient:
    """Drop-in for LLMClient. Constructible with no args (agents call LLMClient())."""

    def __init__(
        self,
        fault: str | None = None,          # None | "fail_first" | "always_fail"
        retry: bool = True,
        withhold_roles: set[str] | None = None,
    ) -> None:
        self._fault = fault
        self._retry = retry
        self._withhold = withhold_roles or set()
        self._first = True

    def _respond(self, role: str) -> FakeLLMResponse:
        tin, tout = _TOKENS[role]
        content = None if role in self._withhold else _CONTENT[role]
        cost = tin * _COST_IN + tout * _COST_OUT
        return FakeLLMResponse(content=content, input_tokens=tin, output_tokens=tout, cost_usd=cost)

    def complete(self, system_prompt: str, user_prompt: str) -> FakeLLMResponse:
        role = _role_of(system_prompt)
        attempts = 3 if self._retry else 1
        last_exc: Exception | None = None
        for _ in range(attempts):
            should_fail = self._fault == "always_fail" or (self._fault == "fail_first" and self._first)
            if should_fail:
                self._first = False
                last_exc = RuntimeError("transient LLM error (mock)")
                continue
            return self._respond(role)
        assert last_exc is not None
        raise last_exc


_FIXED_DOCS = [
    SourceDocument(title="Source One", url="https://example.com/1", snippet="Snippet one.", metadata={"score": 0.9}),
    SourceDocument(title="Source Two", url="https://example.com/2", snippet="Snippet two.", metadata={"score": 0.8}),
    SourceDocument(title="Source Three", url="https://example.com/3", snippet="Snippet three.", metadata={"score": 0.7}),
]


class FakeSearchClient:
    """Drop-in for SearchClient. No retry layer exists in the real class — a fault is fatal."""

    def __init__(self, mode: str = "normal", fault: bool = False) -> None:
        self._mode = mode
        self._fault = fault

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        if self._fault:
            raise RuntimeError("search failed (mock, no retry layer)")
        if self._mode == "empty":
            return []
        return list(_FIXED_DOCS[:max_results])
