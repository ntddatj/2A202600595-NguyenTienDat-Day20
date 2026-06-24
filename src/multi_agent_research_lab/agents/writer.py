"""Writer agent."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a technical writer targeting {audience}. "
    "Write a clear, well-structured response to the query. "
    "Incorporate insights from the analysis and cite sources with [N] notation where relevant. "
    "Aim for around 400-600 words unless the topic demands more."
)


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer` with a cited, structured response."""

        sources_str = "\n".join(
            f"[{i + 1}] {d.title} — {d.url or 'no url'}"
            for i, d in enumerate(state.sources)
        )

        user_prompt = (
            f"Query: {state.request.query}\n\n"
            f"Research notes:\n{state.research_notes}\n\n"
            f"Analysis:\n{state.analysis_notes}\n\n"
            f"Available sources:\n{sources_str}"
        )

        system = _SYSTEM.format(audience=state.request.audience)
        llm = LLMClient()
        resp = llm.complete(system_prompt=system, user_prompt=user_prompt)
        state.final_answer = resp.content
        logger.info("WriterAgent produced final answer (%s tokens)", resp.output_tokens)

        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=resp.content,
                metadata={"output_tokens": resp.output_tokens},
            )
        )
        state.add_trace_event(
            "writer.complete",
            {"input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens},
        )
        return state
