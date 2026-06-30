import json

import pytest

pytest.importorskip("fastapi")
pytest.importorskip("langgraph")
from fastapi.testclient import TestClient

from webviz.server import app


def test_mock_multi_run_reaches_final_answer_with_coverage():
    client = TestClient(app)
    body = {"query": "Explain vector databases for RAG", "live": False,
            "toggles": {"multi": True, "retry": True, "max_iterations": True, "search": True}}
    events = []
    with client.stream("POST", "/run", json=body) as r:
        assert r.status_code == 200
        for line in r.iter_lines():
            if line.startswith("data:"):
                events.append(json.loads(line[5:].strip()))
    final = events[-1]
    assert final["kind"] == "done"
    assert final["state_snapshot"]["final_answer"]
    assert final["metrics"]["citation_coverage"] > 0
