# Task 9 Report — README + End-to-End Smoke Test

## What was written

### 9.1 `tests/webviz/test_smoke.py`
Verbatim from brief: `test_mock_multi_run_reaches_final_answer_with_coverage`.
- Uses `pytest.importorskip("fastapi")` and `pytest.importorskip("langgraph")` guards.
- Creates a `TestClient` inside the test function (avoids module-level state issues).
- POSTs to `/run` with `live=False` and all 4 toggles enabled.
- Collects all SSE `data:` lines, asserts the final event has `kind == "done"`, non-empty `final_answer`, and `citation_coverage > 0`.

### 9.2 Smoke test result
```
PASSED tests/webviz/test_smoke.py::test_mock_multi_run_reaches_final_answer_with_coverage
1 passed, 1 warning in 0.28s
```
The warning is a third-party deprecation from `starlette.testclient` about `httpx` → `httpx2`; it does not affect correctness.

### 9.3 `webviz/README.md`
Verbatim from brief:
- Install command: `pip install -e ".[viz,llm]"`
- Run command: `python -m webviz` → http://127.0.0.1:8000 (with optional `--host`/`--port`)
- Mock mode default description (offline, deterministic, no key)
- Live mode description (requires `OPENAI_API_KEY`/`TAVILY_API_KEY`, graceful on missing key)
- Học gì section: 4 toggles, node/edge/lane/badge clicks, tracing button, export button
- Test command: `python -m pytest tests/webviz -q`

## Full suite result
```
31 passed, 1 warning in 0.36s
```
(30 pre-existing + 1 new smoke test; no skips, no failures)

## Concerns
- The `StarletteDeprecationWarning` from `httpx` is cosmetic and upstream; harmless for now but will require `httpx2` when `starlette` drops the old client.
- No `tests/webviz/__init__.py` created (per global constraints).
- No `src/` or `rebuild-practice/` files were modified.
