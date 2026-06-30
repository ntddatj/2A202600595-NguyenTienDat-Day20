# Frontend Fix Report

## Changes Made

### `webviz/static/app.js`

**Change A — break-tracing triggers a real run:**
- Extracted the `$("run")` click handler body into a new `async function runWorkflow(opts = {})`.
- `runWorkflow` builds the request body as `{ query, live, break_tracing: opts.break_tracing || false, toggles }` and streams/renders exactly as before.
- `$("run")` now calls `runWorkflow()` (no opts).
- The `$("break-tracing")` handler keeps showing the banner + `fail-open` lesson AND additionally calls `runWorkflow({ break_tracing: true })`.

**Change B — compare bars populated after each run:**
- At the end of `runWorkflow`, after the SSE stream loop finishes, a `POST /compare` call is made with `{ query, toggles }`.
- `bar-single` and `bar-multi` widths are set proportionally: `lat / maxLat * 100` percent.
- Label text for `#label-single` and `#label-multi` is updated to show coverage and agent count, e.g. `single (cov 0, 1 agent)` and `multi (cov 1.0, 3 agents)`.
- The entire `/compare` fetch is wrapped in `try/catch` so any failure is silently swallowed and never breaks the run rendering.

### `webviz/static/index.html`

- Added `id="label-single"` to the `<span>single latency</span>` element.
- Added `id="label-multi"` to the `<span>multi latency</span>` element.
- All pre-existing element IDs preserved unchanged.

### `tests/webviz/test_server.py`

- Added `test_appjs_wires_compare_and_break_tracing`: reads `webviz/static/app.js` and asserts it contains `"/compare"` and `"break_tracing"`.

## Test Result

```
37 passed, 1 warning in 0.37s
```

All 37 tests green, including the new `test_appjs_wires_compare_and_break_tracing` and the existing `test_index_has_key_element_ids`.

## Manual Verification Checklist

These behaviors require browser testing and cannot be covered by unit tests:

1. **break-tracing button triggers a real run:**
   - Click "⚡ gây lỗi tracing".
   - Verify: the `#tracing-banner` becomes visible AND the `fail-open` lesson opens in the lesson panel.
   - Verify: the trace log (`#trace-list`) clears and new events stream in.
   - Verify: at least one log entry appears with yellow text (the `warning` kind event from `break_tracing: true`).
   - Verify: the last entry in the trace log is `[done]` — the workflow completed despite the tracing fault.

2. **Compare bars fill after a run:**
   - Click "▶ Run" (or the break-tracing button) and wait for the run to complete.
   - Verify: `#bar-single` and `#bar-multi` show visible coloured bars (neither is 0-width when both latencies are non-zero).
   - Verify: the wider bar reaches 100% and the narrower bar is proportionally shorter.
   - Verify: the label for `#label-single` reads something like `single (cov 0, 1 agent)`.
   - Verify: the label for `#label-multi` reads something like `multi (cov 1.0, 3 agents)`.
   - Verify: the existing `#bar-cov` and `#bar-cost` bars still update normally during the run (regression check).
