import pytest

pytest.importorskip("langgraph")

from webviz.scenarios import build_run_config
from webviz.stream import run_stream

DEF = {"multi": True, "retry": True, "max_iterations": True, "search": True}


def _run(**over):
    t = dict(DEF); t.update(over)
    return list(run_stream("Explain vector databases", build_run_config(t)))


def test_multi_healthy_run_emits_nodes_then_done():
    events = _run()
    kinds = [e.kind for e in events]
    assert kinds[-1] == "done"
    nodes = [e.active_node for e in events if e.kind == "node"]
    assert nodes[0] == "supervisor"
    worker_seq = [n for n in nodes if n in {"researcher", "analyst", "writer"}]
    assert worker_seq == ["researcher", "analyst", "writer"]
    final = events[-1]
    assert final.state_snapshot.get("final_answer")
    assert final.metrics["citation_coverage"] > 0


def test_baseline_emits_two_events():
    events = _run(multi=False)
    assert [e.kind for e in events] == ["baseline", "done"]


def test_search_off_gives_zero_coverage():
    events = _run(search=False)
    assert events[-1].metrics["citation_coverage"] == 0


def test_retry_off_surfaces_error_event_not_exception():
    events = _run(retry=False)
    assert any(e.kind == "error" for e in events)


def test_max_iter_off_hits_hard_cap_with_warning():
    events = _run(max_iterations=False)
    assert any(e.kind == "warning" for e in events)
    assert len([e for e in events if e.kind == "node"]) <= 20


def test_supervisor_edge_is_dashed_worker_edge_is_solid():
    events = _run()
    by_node = {e.active_node: e for e in events if e.kind == "node"}
    assert by_node["researcher"].edge_taken.style == "dashed"   # conditional out of supervisor
    solids = [e.edge_taken for e in events if e.edge_taken and e.edge_taken.style == "solid"]
    assert all(ed.target == "supervisor" for ed in solids)
