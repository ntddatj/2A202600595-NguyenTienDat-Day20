"""LangGraph multi-agent workflow."""

import logging
from typing import TypedDict

from langgraph.graph import END, StateGraph

from multi_agent_research_lab.agents.analyst import AnalystAgent
from multi_agent_research_lab.agents.researcher import ResearcherAgent
from multi_agent_research_lab.agents.supervisor import SupervisorAgent
from multi_agent_research_lab.agents.writer import WriterAgent
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)


class _GraphState(TypedDict):
    """Thin wrapper so LangGraph manages a single Pydantic object."""
    research_state: ResearchState


def _route(state: _GraphState) -> str:
    last = state["research_state"].route_history[-1]
    return END if last == "done" else last


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph."""

    def build(self) -> object:
        """Create a compiled LangGraph graph with supervisor + worker nodes."""

        supervisor = SupervisorAgent()
        researcher = ResearcherAgent()
        analyst = AnalystAgent()
        writer = WriterAgent()

        def supervisor_node(state: _GraphState) -> _GraphState:
            return {"research_state": supervisor.run(state["research_state"])}

        def researcher_node(state: _GraphState) -> _GraphState:
            return {"research_state": researcher.run(state["research_state"])}

        def analyst_node(state: _GraphState) -> _GraphState:
            return {"research_state": analyst.run(state["research_state"])}

        def writer_node(state: _GraphState) -> _GraphState:
            return {"research_state": writer.run(state["research_state"])}

        graph: StateGraph = StateGraph(_GraphState)
        graph.add_node("supervisor", supervisor_node)
        graph.add_node("researcher", researcher_node)
        graph.add_node("analyst", analyst_node)
        graph.add_node("writer", writer_node)

        graph.set_entry_point("supervisor")
        graph.add_conditional_edges(
            "supervisor",
            _route,
            {"researcher": "researcher", "analyst": "analyst", "writer": "writer", END: END},
        )
        graph.add_edge("researcher", "supervisor")
        graph.add_edge("analyst", "supervisor")
        graph.add_edge("writer", "supervisor")

        return graph.compile()

    def run(self, state: ResearchState) -> ResearchState:
        """Invoke the compiled graph and return the final ResearchState."""

        compiled = self.build()
        result: _GraphState = compiled.invoke({"research_state": state})
        final: ResearchState = result["research_state"]
        logger.info(
            "Workflow complete. route_history=%s agents_run=%d",
            final.route_history,
            len(final.agent_results),
        )
        return final
