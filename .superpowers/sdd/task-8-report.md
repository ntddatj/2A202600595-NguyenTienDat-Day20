# Task 8 Report — Frontend `webviz/static/` (Layout A)

## Files Created / Modified

- `tests/webviz/test_server.py` — added `test_index_has_key_element_ids` (8.1)
- `webviz/static/index.html` — replaced 7-line stub with full Layout A markup (8.3)
- `webviz/static/style.css` — created from brief verbatim (8.4)
- `webviz/static/app.js` — created from brief verbatim (8.5)

## Page-load Test Evidence

**RED (before static files):**
```
FAILED tests/webviz/test_server.py::test_index_has_key_element_ids
AssertionError: id="query"
```

**GREEN (after writing the three files):**
```
. [100%]
1 passed
```

## Full Suite Result

```
30 passed, 1 warning in 0.34s
```
(The warning is a deprecation note about `httpx` vs `httpx2` from the FastAPI test client — unrelated to this task.)

## Self-Review

All 15 element `id`s asserted by the test are present in `index.html` verbatim from the brief:
`query`, `run`, `graph`, `clipboard`, `lesson-panel`, `trace-log`, `metrics`,
`toggle-multi`, `toggle-retry`, `toggle-max_iterations`, `toggle-search`,
`break-tracing`, `export-report`, `mode-live`, `speed`.

The three static files match the brief exactly — no deviations.

## Concerns (behavior not unit-tested)

The following behaviors require manual verification (§8.7):

1. **Toggle → lesson jump (before Run):** The `change` event listener on each toggle calls `showLesson` immediately. This is correct in JS but untested by the server-side test suite — a browser-based e2e test (Playwright/Puppeteer) would be needed to automate it.

2. **SSE stream rendering:** `applyEvent` parses `StreamEvent` payloads and updates DOM. Correctness depends on the event schema from `webviz/stream.py` matching the field names (`active_node`, `edge_taken`, `state_snapshot`, `lane`, `metrics`, `kind`, `note`). No JS unit tests exist.

3. **Export download:** The `POST /report` → `Blob` → `<a>.click()` path requires a real browser (no headless test). The `/report` endpoint is tested via TestClient.

4. **Graph animation:** The CSS `@keyframes dash` animation on `.edge.active` is visual-only and cannot be asserted by pytest.

5. **Glossary chips:** `glossInline` does regex replacement; no unit test guards against term collision or regex escaping edge cases for unusual lesson terms.
