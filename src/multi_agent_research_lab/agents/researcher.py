"""Researcher agent."""

import logging

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.search_client import SearchClient

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a research specialist. Given a query and a list of source snippets, "
    "write concise research notes that capture the most important facts, figures, "
    "and references. Number each key point."
)


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""

        search = SearchClient()
        docs = search.search(state.request.query, max_results=state.request.max_sources)
        state.sources = docs
        logger.info("ResearcherAgent fetched %d sources", len(docs))

        snippets = "\n\n".join(
            f"[{i + 1}] {d.title}\n{d.snippet}" for i, d in enumerate(docs)
        )
        user_prompt = f"Query: {state.request.query}\n\nSources:\n{snippets}"

        llm = LLMClient()
        resp = llm.complete(system_prompt=_SYSTEM, user_prompt=user_prompt)
        state.research_notes = resp.content

        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=resp.content,
                metadata={"sources": len(docs), "output_tokens": resp.output_tokens},
            )
        )
        state.add_trace_event(
            "researcher.complete",
            {"sources": len(docs), "input_tokens": resp.input_tokens, "output_tokens": resp.output_tokens},
        )
        return state
