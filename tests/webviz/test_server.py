import json

import pytest

pytest.importorskip("fastapi")
from fastapi.testclient import TestClient

from webviz.server import app

client = TestClient(app)


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200
    assert "webviz" in r.text.lower()


def test_lessons_endpoint_returns_all():
    r = client.get("/lessons")
    assert r.status_code == 200
    ids = {item["id"] for item in r.json()}
    assert "retry-timeout" in ids and "benchmark" in ids


def test_run_sse_streams_events_to_done():
    pytest.importorskip("langgraph")
    body = {"query": "Explain vector databases", "live": False,
            "toggles": {"multi": True, "retry": True, "max_iterations": True, "search": True}}
    with client.stream("POST", "/run", json=body) as r:
        assert r.status_code == 200
        payloads = []
        for line in r.iter_lines():
            if line.startswith("data:"):
                payloads.append(json.loads(line[len("data:"):].strip()))
    assert payloads[-1]["kind"] == "done"
    assert payloads[-1]["metrics"]["citation_coverage"] > 0


def test_report_returns_markdown():
    pytest.importorskip("langgraph")
    body = {"query": "Explain vector databases",
            "toggles": {"multi": True, "retry": True, "max_iterations": True, "search": True}}
    r = client.post("/report", json=body)
    assert r.status_code == 200
    assert "# Benchmark Report" in r.text


# Change 4: /compare endpoint
def test_compare_returns_single_and_multi():
    pytest.importorskip("langgraph")
    body = {"query": "Explain vector databases",
            "toggles": {"multi": True, "retry": True, "max_iterations": True, "search": True}}
    r = client.post("/compare", json=body)
    assert r.status_code == 200
    data = r.json()
    assert "single" in data and "multi" in data
    assert data["multi"]["citation_coverage"] > 0
    assert data["single"]["citation_coverage"] == 0


def test_index_has_key_element_ids():
    html = client.get("/").text
    for el in ["id=\"query\"", "id=\"run\"", "id=\"graph\"", "id=\"clipboard\"",
               "id=\"lesson-panel\"", "id=\"trace-log\"", "id=\"metrics\"",
               "id=\"toggle-multi\"", "id=\"toggle-retry\"", "id=\"toggle-max_iterations\"",
               "id=\"toggle-search\"", "id=\"break-tracing\"", "id=\"export-report\"",
               "id=\"mode-live\"", "id=\"speed\""]:
        assert el in html, el


def test_appjs_wires_compare_and_break_tracing():
    """app.js must reference /compare endpoint and break_tracing flag."""
    import pathlib
    js = pathlib.Path("webviz/static/app.js").read_text()
    assert "/compare" in js, "app.js must call /compare"
    assert "break_tracing" in js, "app.js must pass break_tracing"
