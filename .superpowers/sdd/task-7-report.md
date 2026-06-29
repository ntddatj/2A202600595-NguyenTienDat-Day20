# Task 7 Report — `webviz/server.py`: FastAPI Routes

## Routes Implemented
- `GET /` — serves `webviz/static/index.html` via `FileResponse`
- `GET /static/*` — static file mount (with `check_dir=False` to survive missing dir at import)
- `GET /lessons` — returns all 9 lessons as JSON list via `load_lessons()`
- `POST /run` — SSE streaming via `EventSourceResponse`; calls `build_run_config(req.toggles, req.live)`; Live mode without `OPENAI_API_KEY` yields `kind="error"` event, never a 500
- `POST /report` — calls real `render_markdown_report` over two `run_benchmark` trials (baseline + multi) built from fakes; returns `text/markdown`

## TDD RED/GREEN

### RED (Step 7.2)
```
$ .venv/bin/python3 -m pytest tests/webviz/test_server.py -q
ERROR collecting tests/webviz/test_server.py
ImportError: No module named 'webviz.server'
```

### GREEN (Step 7.4)
```
$ .venv/bin/python3 -m pytest tests/webviz/test_server.py -v
collected 4 items
tests/webviz/test_server.py::test_index_served PASSED
tests/webviz/test_server.py::test_lessons_endpoint_returns_all PASSED
tests/webviz/test_server.py::test_run_sse_streams_events_to_done PASSED
tests/webviz/test_server.py::test_report_returns_markdown PASSED
4 passed in 0.32s
```

### Full suite
```
$ .venv/bin/python3 -m pytest tests/webviz -q
29 passed, 1 warning in 0.35s
```
(29 = existing 25 + 4 new server tests; 1 deprecation warning: httpx vs httpx2)

## Files Changed
- `tests/webviz/test_server.py` — new, exact code from brief
- `webviz/server.py` — new, follows brief with one adaptation (see Self-Review)
- `webviz/static/index.html` — minimal HTML stub so `GET /` returns 200 (Task 8 replaces this)

## Self-Review

### Adaptation: `check_dir=False` on StaticFiles
The brief code: `StaticFiles(directory=str(STATIC))` — this crashes at import time when `webviz/static/` doesn't exist (`RuntimeError: Directory ... does not exist`). The constraint says "The server must not crash on a bad/missing static dir at import time." Used `check_dir=False` to satisfy this. When the directory does exist (as it does now with the stub), serving works normally.

### Stub `index.html`
The brief's `test_index_served` checks `status_code == 200` and `"webviz" in r.text.lower()`. The constraint notes this test "belongs to Task 8", but the test file code in the brief includes it. Resolution: created a minimal placeholder `index.html` with "webviz" in it so the test passes now; Task 8 will replace it with the real frontend.

### No `tests/webviz/__init__.py`
Confirmed absent (consistent with existing test files in this dir).

### `POST /run` live guard
`get_settings().openai_api_key` checked before streaming; falsy value yields `kind="error"` SSE event and returns immediately — no 500.

## Concerns
None blocking. Minor: the `StarletteDeprecationWarning` about `httpx` vs `httpx2` appears in all test runs — it's from the installed `fastapi` package's `TestClient` re-export, not from our code. Not actionable in this task.
