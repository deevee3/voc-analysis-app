"""Theme classification and clustering for insights."""

from __future__ import annotations

import json
import logging
import re
from dataclasses import dataclass, field
from typing import Any, Sequence

from openai import AsyncOpenAI
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from voc_app.config import get_settings
from voc_app.models import Insight, InsightThemeLink, Theme

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class ThemeMatch:
    """A matched theme with confidence score."""

    theme_id: str
    theme_name: str
    confidence: float
    method: str  # "rule" or "llm"


@dataclass(slots=True)
class ClassificationResult:
    """Result of theme classification for an insight."""

    insight_id: str
    matches: list[ThemeMatch]
    success: bool
    error: str | None = None


class ThemeClassifier:
    """Classifies insights into themes using rules and LLM assistance."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        use_llm: bool = True,
        llm_model: str = "gpt-4",
        confidence_threshold: float = 0.6,
    ) -> None:
        self.session = session
        self.use_llm = use_llm
        self.llm_model = llm_model
        self.confidence_threshold = confidence_threshold
        self._themes_cache: list[Theme] | None = None

        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key) if use_llm else None

    async def classify_insight(self, insight: Insight) -> ClassificationResult:
        """Classify a single insight into themes."""
        try:
            themes = await self._load_themes()
            matches: list[ThemeMatch] = []

            # Rule-based matching
            rule_matches = self._apply_rules(insight, themes)
            matches.extend(rule_matches)

            # LLM-assisted classification if enabled
            if self.use_llm and self.client:
                llm_matches = await self._llm_classify(insight, themes)
                matches.extend(llm_matches)

            # Deduplicate and filter by confidence
            matches = self._deduplicate_matches(matches)
            matches = [m for m in matches if m.confidence >= self.confidence_threshold]

            return ClassificationResult(
                insight_id=str(insight.id),
                matches=matches,
                success=True,
            )

        except Exception as exc:
            logger.exception(f"Classification failed for insight {insight.id}: {exc}")
            return ClassificationResult(
                insight_id=str(insight.id),
                matches=[],
                success=False,
                error=str(exc),
            )

    async def classify_batch(self, insights: Sequence[Insight]) -> list[ClassificationResult]:
        """Classify multiple insights."""
        results = []
        for insight in insights:
            result = await self.classify_insight(insight)
            results.append(result)
        return results

    async def persist_classifications(
        self, results: Sequence[ClassificationResult]
    ) -> list[InsightThemeLink]:
        """Persist theme classifications to database."""
        links: list[InsightThemeLink] = []

        for result in results:
            if not result.success:
                continue

            for match in result.matches:
                link = InsightThemeLink(
                    insight_id=result.insight_id,
                    theme_id=match.theme_id,
                    weight=match.confidence,
                )
                links.append(link)

        if links:
            self.session.add_all(links)
            await self.session.flush()

        return links

    async def _load_themes(self) -> list[Theme]:
        """Load themes from database with caching."""
        if self._themes_cache is None:
            result = await self.session.execute(select(Theme))
            self._themes_cache = list(result.scalars().all())
        return self._themes_cache

    def _apply_rules(self, insight: Insight, themes: list[Theme]) -> list[ThemeMatch]:
        """Apply rule-based keyword matching."""
        matches: list[ThemeMatch] = []
        text = f"{insight.summary} {json.dumps(insight.pain_points or {})} {json.dumps(insight.feature_requests or {})}".lower()

        for theme in themes:
            # Simple keyword matching based on theme name
            keywords = self._extract_keywords(theme.name, theme.description)
            match_count = sum(1 for kw in keywords if kw in text)

            if match_count > 0:
                confidence = min(match_count * 0.3, 0.9)  # Cap at 0.9
                matches.append(
                    ThemeMatch(
                        theme_id=str(theme.id),
                        theme_name=theme.name,
                        confidence=confidence,
                        method="rule",
                    )
                )

        return matches

    def _extract_keywords(self, name: str, description: str | None) -> list[str]:
        """Extract keywords from theme name and description."""
        keywords = [name.lower()]

        if description:
            # Extract significant words from description
            words = re.findall(r"\b\w{4,}\b", description.lower())
            keywords.extend(words[:5])  # Take top 5 words

        return keywords

    async def _llm_classify(self, insight: Insight, themes: list[Theme]) -> list[ThemeMatch]:
        """Use LLM to classify insight into themes."""
        if not self.client:
            return []

        theme_list = "\n".join([f"- {t.name}: {t.description or 'N/A'}" for t in themes])

        prompt = f"""Classify the following customer insight into relevant themes.

Insight Summary: {insight.summary}

Available Themes:
{theme_list}

Return a JSON array of theme classifications with confidence scores (0-1).
Format: [{{"theme_name": "...", "confidence": 0.85}}, ...]

Only include themes with confidence >= 0.5."""

        try:
            response = await self.client.chat.completions.create(
                model=self.llm_model,
                messages=[
                    {"role": "system", "content": "You are a theme classification assistant."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.2,
                max_tokens=500,
            )

            content = response.choices[0].message.content
            classifications = json.loads(content)

            matches = []
            for item in classifications.get("classifications", []):
                theme_name = item.get("theme_name")
                confidence = item.get("confidence", 0.0)

                # Find matching theme
                matching_theme = next((t for t in themes if t.name == theme_name), None)
                if matching_theme and confidence >= 0.5:
                    matches.append(
                        ThemeMatch(
                            theme_id=str(matching_theme.id),
                            theme_name=theme_name,
                            confidence=confidence,
                            method="llm",
                        )
                    )

            return matches

        except Exception as exc:
            logger.error(f"LLM classification failed: {exc}")
            return []

    def _deduplicate_matches(self, matches: list[ThemeMatch]) -> list[ThemeMatch]:
        """Deduplicate theme matches, keeping highest confidence."""
        seen: dict[str, ThemeMatch] = {}

        for match in matches:
            if match.theme_id not in seen or match.confidence > seen[match.theme_id].confidence:
                seen[match.theme_id] = match

        return list(seen.values())


async def classify_insights(
    session: AsyncSession,
    insights: Sequence[Insight],
    *,
    use_llm: bool = True,
    confidence_threshold: float = 0.6,
) -> list[ClassificationResult]:
    """Convenience helper for classifying insights."""
    classifier = ThemeClassifier(
        session,
        use_llm=use_llm,
        confidence_threshold=confidence_threshold,
    )
    return await classifier.classify_batch(insights)
