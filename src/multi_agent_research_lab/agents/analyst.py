"""Analyst agent."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a critical analyst. Given research notes, extract the most important claims, "
    "compare different viewpoints, flag any weak or unsupported evidence, and summarise "
    "the overall strength of the findings. Structure your response with clear headings."
)


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes`."""

        user_prompt = (
            f"Research query: {state.request.query}\n\n"
            f"Research notes:\n{state.research_notes}"
        )

        llm = LLMClient()
        resp = llm.complete(system_prompt=_SYSTEM, user_prompt=user_prompt)
        state.analysis_notes = resp.content
        logger.info("AnalystAgent produced analysis (%s tokens)", resp.output_tokens)

        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=resp.content,
                metadata={"output_tokens": resp.output_tokens},
            )
        )
        state.add_trace_event(
            "analyst.complete",
            {"input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens},
        )
        return state
