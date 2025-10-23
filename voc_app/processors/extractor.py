"""GPT-5 powered insight extraction with batching and retry logic."""

from __future__ import annotations

import asyncio
import json
import logging
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional, Sequence

from openai import AsyncOpenAI, RateLimitError
from pydantic import ValidationError

from voc_app.config import get_settings
from voc_app.models import Feedback
from voc_app.processors.prompts import (
    build_extraction_messages,
    format_batch_extraction_prompt,
    format_single_extraction_prompt,
)
from voc_app.processors.schemas import InsightExtraction

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ExtractionCost:
    """Track API usage costs."""

    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    estimated_cost_usd: float = 0.0


@dataclass(slots=True)
class ExtractionResult:
    """Result of extracting insights from feedback."""

    feedback_id: str
    extraction: InsightExtraction | None
    success: bool
    error: str | None = None
    retry_count: int = 0
    cost: ExtractionCost = field(default_factory=ExtractionCost)


@dataclass(slots=True)
class BatchExtractionSummary:
    """Aggregate results from batch processing."""

    results: list[ExtractionResult]
    total_cost: ExtractionCost
    success_count: int
    failure_count: int
    total_duration_seconds: float


class InsightExtractor:
    """Extracts structured insights from customer feedback using GPT-5."""

    def __init__(
        self,
        *,
        model: str = "gpt-5",
        max_retries: int = 3,
        batch_size: int = 5,
        rate_limit_delay: float = 1.0,
        api_key: str | None = None,
    ) -> None:
        settings = get_settings()
        self.model = model
        self.max_retries = max_retries
        self.batch_size = batch_size
        self.rate_limit_delay = rate_limit_delay
        self.client = AsyncOpenAI(api_key=api_key or settings.openai_api_key)

        # Pricing per 1K tokens (approximate GPT-4 rates)
        self.prompt_token_cost = 0.03 / 1000
        self.completion_token_cost = 0.06 / 1000

    async def extract_single(self, feedback: Feedback) -> ExtractionResult:
        """Extract insights from a single feedback item."""
        start_time = datetime.utcnow()

        prompt = format_single_extraction_prompt(
            content=feedback.clean_content or feedback.raw_content,
            source=str(feedback.data_source_id),
            platform=feedback.extra_metadata.get("platform", "unknown") if feedback.extra_metadata else "unknown",
            posted_at=feedback.posted_at.isoformat() if feedback.posted_at else "unknown",
            url=feedback.url,
        )

        for attempt in range(self.max_retries):
            try:
                response = await self._call_openai(prompt)
                extraction = InsightExtraction.model_validate_json(response["content"])
                cost = self._calculate_cost(response["usage"])

                return ExtractionResult(
                    feedback_id=str(feedback.id),
                    extraction=extraction,
                    success=True,
                    retry_count=attempt,
                    cost=cost,
                )

            except RateLimitError:
                logger.warning(f"Rate limit hit on attempt {attempt + 1}, retrying...")
                await asyncio.sleep(self.rate_limit_delay * (2**attempt))

            except (ValidationError, json.JSONDecodeError) as exc:
                logger.error(f"Parsing failed for feedback {feedback.id}: {exc}")
                return ExtractionResult(
                    feedback_id=str(feedback.id),
                    extraction=None,
                    success=False,
                    error=f"Parsing error: {str(exc)}",
                    retry_count=attempt,
                )

            except Exception as exc:
                logger.exception(f"Extraction failed for feedback {feedback.id}: {exc}")
                if attempt == self.max_retries - 1:
                    return ExtractionResult(
                        feedback_id=str(feedback.id),
                        extraction=None,
                        success=False,
                        error=str(exc),
                        retry_count=attempt,
                    )
                await asyncio.sleep(self.rate_limit_delay)

        return ExtractionResult(
            feedback_id=str(feedback.id),
            extraction=None,
            success=False,
            error="Max retries exceeded",
            retry_count=self.max_retries,
        )

    async def extract_batch(self, feedback_items: Sequence[Feedback]) -> BatchExtractionSummary:
        """Extract insights from multiple feedback items with batching."""
        start_time = datetime.utcnow()
        all_results: list[ExtractionResult] = []
        total_cost = ExtractionCost()

        # Process in batches
        for i in range(0, len(feedback_items), self.batch_size):
            batch = feedback_items[i : i + self.batch_size]
            batch_results = await asyncio.gather(
                *[self.extract_single(feedback) for feedback in batch],
                return_exceptions=True,
            )

            for result in batch_results:
                if isinstance(result, Exception):
                    logger.error(f"Batch extraction error: {result}")
                    continue

                all_results.append(result)
                total_cost.prompt_tokens += result.cost.prompt_tokens
                total_cost.completion_tokens += result.cost.completion_tokens
                total_cost.total_tokens += result.cost.total_tokens
                total_cost.estimated_cost_usd += result.cost.estimated_cost_usd

            # Rate limit pause between batches
            if i + self.batch_size < len(feedback_items):
                await asyncio.sleep(self.rate_limit_delay)

        end_time = datetime.utcnow()
        duration = (end_time - start_time).total_seconds()

        success_count = sum(1 for r in all_results if r.success)
        failure_count = len(all_results) - success_count

        return BatchExtractionSummary(
            results=all_results,
            total_cost=total_cost,
            success_count=success_count,
            failure_count=failure_count,
            total_duration_seconds=duration,
        )

    async def _call_openai(self, prompt: str) -> dict[str, Any]:
        """Call OpenAI API with structured output."""
        messages = build_extraction_messages(prompt)

        response = await self.client.chat.completions.create(
            model=self.model,
            messages=messages,
            response_format={"type": "json_object"},
            max_completion_tokens=2000,
        )

        choice = response.choices[0]
        usage = response.usage

        return {
            "content": choice.message.content,
            "usage": {
                "prompt_tokens": usage.prompt_tokens,
                "completion_tokens": usage.completion_tokens,
                "total_tokens": usage.total_tokens,
            },
        }

    def _calculate_cost(self, usage: dict[str, int]) -> ExtractionCost:
        """Calculate API cost from token usage."""
        prompt_cost = usage["prompt_tokens"] * self.prompt_token_cost
        completion_cost = usage["completion_tokens"] * self.completion_token_cost

        return ExtractionCost(
            prompt_tokens=usage["prompt_tokens"],
            completion_tokens=usage["completion_tokens"],
            total_tokens=usage["total_tokens"],
            estimated_cost_usd=prompt_cost + completion_cost,
        )


async def extract_insights(
    feedback_items: Sequence[Feedback],
    *,
    model: str = "gpt-5",
    max_retries: int = 3,
    batch_size: int = 5,
) -> BatchExtractionSummary:
    """Convenience helper for batch extraction."""
    extractor = InsightExtractor(
        model=model,
        max_retries=max_retries,
        batch_size=batch_size,
    )
    return await extractor.extract_batch(feedback_items)
