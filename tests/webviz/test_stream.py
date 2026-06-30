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


# Change 2: break_tracing emits warning then completes with done
def test_break_tracing_emits_warning_then_done():
    cfg = build_run_config(DEF, break_tracing=True)
    events = list(run_stream("Explain vector databases", cfg))
    kinds = [e.kind for e in events]
    warning_events = [e for e in events if e.kind == "warning"]
    # must have a tracing-fail warning
    assert any("nuốt" in e.note or "fail-open" in e.note or "fail_open" in e.note
               for e in warning_events), f"No tracing warning found; warnings: {[e.note for e in warning_events]}"
    # and workflow must still complete
    assert kinds[-1] == "done", f"Last event kind was {kinds[-1]}"


# Change 3: live+search-off context helper patches only SearchClient
def test_live_search_off_patches_only_search_client():
    import multi_agent_research_lab.agents.researcher as _researcher_mod
    import multi_agent_research_lab.services.search_client as _search_mod
    from webviz.stream import _live_search_patch
    from webviz.fakes import FakeSearchClient

    cfg = build_run_config({**DEF, "search": False}, live=True)
    orig_researcher_search = _researcher_mod.SearchClient
    orig_service_search = _search_mod.SearchClient

    with _live_search_patch(cfg):
        # SearchClient should now be a FakeSearchClient factory
        patched = _researcher_mod.SearchClient()
        assert isinstance(patched, FakeSearchClient), f"Expected FakeSearchClient, got {type(patched)}"

    # restored after exit
    assert _researcher_mod.SearchClient is orig_researcher_search
    assert _search_mod.SearchClient is orig_service_search
