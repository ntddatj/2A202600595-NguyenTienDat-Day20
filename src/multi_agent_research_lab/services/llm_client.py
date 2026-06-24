"""LLM client abstraction.

Production note: agents should depend on this interface instead of importing an SDK directly.
"""

import logging
from dataclasses import dataclass

from tenacity import retry, stop_after_attempt, wait_exponential

from multi_agent_research_lab.core.config import get_settings

logger = logging.getLogger(__name__)

# Approximate cost per 1M tokens for gpt-4o-mini
_COST_PER_1M_INPUT = 0.15
_COST_PER_1M_OUTPUT = 0.60


@dataclass(frozen=True)
class LLMResponse:
    content: str
    input_tokens: int | None = None
    output_tokens: int | None = None
    cost_usd: float | None = None


class LLMClient:
    """Provider-agnostic LLM client backed by OpenAI."""

    def __init__(self) -> None:
        from openai import OpenAI  # imported lazily to avoid hard dep when mocking

        settings = get_settings()
        self._model = settings.openai_model
        self._client = OpenAI(api_key=settings.openai_api_key)

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    def complete(self, system_prompt: str, user_prompt: str) -> LLMResponse:
        """Return a model completion with retry, timeout, and token logging."""

        response = self._client.chat.completions.create(
            model=self._model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            timeout=get_settings().timeout_seconds,
        )

        choice = response.choices[0]
        usage = response.usage
        input_tokens = usage.prompt_tokens if usage else None
        output_tokens = usage.completion_tokens if usage else None

        cost: float | None = None
        if input_tokens is not None and output_tokens is not None:
            cost = (input_tokens * _COST_PER_1M_INPUT + output_tokens * _COST_PER_1M_OUTPUT) / 1_000_000

        logger.info(
            "LLMClient.complete model=%s input_tokens=%s output_tokens=%s cost_usd=%.6f",
            self._model,
            input_tokens,
            output_tokens,
            cost or 0.0,
        )

        return LLMResponse(
            content=choice.message.content or "",
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost,
        )
