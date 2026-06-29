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
