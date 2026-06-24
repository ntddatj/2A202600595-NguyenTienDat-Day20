from multi_agent_research_lab.agents import SupervisorAgent
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState


def test_supervisor_routes_to_researcher_when_no_notes() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    result = SupervisorAgent().run(state)
    assert result.route_history[-1] == "researcher"


def test_supervisor_routes_to_analyst_after_research() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.research_notes = "Some notes"
    result = SupervisorAgent().run(state)
    assert result.route_history[-1] == "analyst"


def test_supervisor_routes_to_writer_after_analysis() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.research_notes = "Some notes"
    state.analysis_notes = "Some analysis"
    result = SupervisorAgent().run(state)
    assert result.route_history[-1] == "writer"


def test_supervisor_routes_done_when_complete() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.research_notes = "notes"
    state.analysis_notes = "analysis"
    state.final_answer = "answer"
    result = SupervisorAgent().run(state)
    assert result.route_history[-1] == "done"


def test_supervisor_forces_done_at_max_iterations() -> None:
    state = ResearchState(request=ResearchQuery(query="Explain multi-agent systems"))
    state.iteration = 100  # far above any max_iterations setting
    result = SupervisorAgent().run(state)
    assert result.route_history[-1] == "done"
