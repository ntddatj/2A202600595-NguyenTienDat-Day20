"""Search client abstraction for ResearcherAgent."""

import logging

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import SourceDocument

logger = logging.getLogger(__name__)


class SearchClient:
    """Search client backed by Tavily."""

    def __init__(self) -> None:
        from tavily import TavilyClient  # lazy import

        settings = get_settings()
        self._client = TavilyClient(api_key=settings.tavily_api_key)

    def search(self, query: str, max_results: int = 5) -> list[SourceDocument]:
        """Search for documents relevant to a query using Tavily."""

        logger.info("SearchClient.search query=%r max_results=%d", query, max_results)
        response = self._client.search(query, max_results=max_results)

        docs: list[SourceDocument] = []
        for item in response.get("results", []):
            docs.append(
                SourceDocument(
                    title=item.get("title", ""),
                    url=item.get("url"),
                    snippet=item.get("content", ""),
                    metadata={"score": item.get("score")},
                )
            )

        logger.info("SearchClient.search returned %d results", len(docs))
        return docs
