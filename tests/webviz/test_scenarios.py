from webviz.scenarios import build_run_config, RunConfig, HARD_CAP

DEF = {"multi": True, "retry": True, "max_iterations": True, "search": True}


def _cfg(**over):
    t = dict(DEF); t.update(over)
    return build_run_config(t)


def test_defaults_are_healthy_multi():
    c = _cfg()
    assert isinstance(c, RunConfig)
    assert c.runner == "multi" and c.llm_retry and c.llm_fault is None
    assert c.search_mode == "normal" and not c.withhold_research_notes
    assert c.max_iter_override is None and c.hard_cap == HARD_CAP == 20


def test_multi_off_is_baseline():
    assert _cfg(multi=False).runner == "baseline"


def test_retry_off_injects_fatal_fault():
    c = _cfg(retry=False)
    assert c.llm_retry is False and c.llm_fault == "fail_first"


def test_search_off_is_empty():
    assert _cfg(search=False).search_mode == "empty"


def test_max_iter_off_forces_loop_and_high_override():
    c = _cfg(max_iterations=False)
    assert c.withhold_research_notes is True and c.max_iter_override == 9999


def test_live_defaults_off_and_passes_through():
    assert _cfg().live is False
    assert build_run_config(DEF, live=True).live is True
