"""Supervisor / router agent."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def run(self, state: ResearchState) -> ResearchState:
        """Choose next route based on what is missing in state.

        Routing order: researcher → analyst → writer → done.
        Falls back to done when max_iterations is reached.
        """
        settings = get_settings()

        if state.iteration >= settings.max_iterations:
            next_agent = "done"
            logger.warning("Max iterations (%d) reached, forcing done.", settings.max_iterations)
        elif state.research_notes is None:
            next_agent = "researcher"
        elif state.analysis_notes is None:
            next_agent = "analyst"
        elif state.final_answer is None:
            next_agent = "writer"
        else:
            next_agent = "done"

        logger.info("Supervisor routing → %s (iteration %d)", next_agent, state.iteration)
        state.record_route(next_agent)
        state.add_trace_event("supervisor.route", {"next": next_agent, "iteration": state.iteration})
        return state
