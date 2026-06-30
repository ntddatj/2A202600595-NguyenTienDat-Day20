# Backend Fix Report — webviz feat/webviz

## Change 1 — `scenarios.py`: `break_tracing` flag

**What:** Added `break_tracing: bool = False` to `RunConfig` (after `live`). Updated `build_run_config(toggles, live=False, break_tracing=False)` to accept and pass through the new parameter.

**Tests added:**
- `test_scenarios.py::test_break_tracing_defaults_false` — asserts `_cfg().break_tracing is False`
- `test_scenarios.py::test_break_tracing_passes_through` — asserts `build_run_config(DEF, break_tracing=True).break_tracing is True`

**RED → GREEN:** Both failed `AttributeError`/`TypeError` before the change; both pass after.

---

## Change 2 — `stream.py`: Real fail-open demo for `break_tracing`

**What:** Added `_force_tracing_failure()` context manager that sets `LANGCHAIN_TRACING_V2=true` and patches `langsmith.Client` to a `_Boom` class that raises `RuntimeError` on construction (restored in `finally`). In `run_stream` (multi path, inside `client_ctx`), when `cfg.break_tracing` is `True`: enters `_force_tracing_failure` → calls real `_tracing.trace_span(...)` → the span hits `_Boom()` → `trace_span`'s `except Exception: pass` swallows it → yields `StreamEvent(kind="warning", step=0, note="⚡ Lớp tracing vừa ném lỗi và bị nuốt (fail-open) — workflow vẫn chạy tiếp.")` → workflow continues normally.

**Tests added:**
- `test_stream.py::test_break_tracing_emits_warning_then_done` — confirms a `kind="warning"` event with "nuốt" in the note is present AND the final event is `kind="done"`.

**RED → GREEN:** Failed `TypeError: build_run_config() got unexpected keyword argument` before Change 1 was applied; GREEN after both changes.

---

## Change 3 — `stream.py`: Live mode honors the `search` toggle

**What:** Added `_live_search_patch(cfg)` context manager (exported from `stream.py`) that patches only `_researcher.SearchClient` and `_search_mod.SearchClient` to `FakeSearchClient(mode="empty")` while leaving `LLMClient` real. Updated `run_stream`: when `cfg.live` is `True`, select `_live_search_patch(cfg)` if `cfg.search_mode == "empty"`, else `nullcontext()`.

**Tests added:**
- `test_stream.py::test_live_search_off_patches_only_search_client` — imports `_live_search_patch` directly, checks that `_researcher.SearchClient()` returns a `FakeSearchClient` inside the context and is restored after exit.

**Cannot test:** Full live+search-off end-to-end requires a real OpenAI API key and Tavily key which are not present in this environment. The unit test on the context-selection helper covers the patch/restore logic.

**RED → GREEN:** Failed `ImportError: cannot import name '_live_search_patch'` before implementation; GREEN after.

---

## Change 4 — `server.py`: M3 fix + `break_tracing` + `/compare`

**What:**
- **M3 fix:** `_runner` now passes `search_mode="normal", llm_retry=True` in addition to existing healthy overrides so the exported report always compares two genuinely healthy runs.
- **`break_tracing` passthrough:** `RunRequest` has `break_tracing: bool = False`; `build_run_config(req.toggles, req.live, req.break_tracing)` is called in `/run`.
- **`/compare` endpoint:** `POST /compare` (body: `{query, toggles}`) runs healthy baseline and multi via `_runner`, wraps each in `time.perf_counter`, reuses `_cost`/`_coverage` from `benchmark.py` (no re-implementation), returns `{"single": {...}, "multi": {...}}` each with `latency_seconds`, `estimated_cost_usd`, `citation_coverage`, `agents`.

**Tests added:**
- `test_server.py::test_compare_returns_single_and_multi` — asserts 200, `"single"` and `"multi"` keys present, `multi.citation_coverage > 0`, `single.citation_coverage == 0`.

**RED → GREEN:** Failed `assert 404 == 200` before implementation; GREEN after.

---

## Full Suite Result

```
36 passed, 1 warning in 0.37s
```

31 pre-existing tests + 5 new tests, all green. No regressions.

---

## Untested / Notes

- **Live + search-off end-to-end:** No `OPENAI_API_KEY` or `TAVILY_API_KEY` in this environment. The context-selection helper `_live_search_patch` is unit-tested in isolation; full integration requires real credentials.
- **Live + break_tracing:** `break_tracing` is exercised in mock mode (test above). The same code path runs in live mode, but live is not tested without a key.
