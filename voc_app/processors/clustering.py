"""Clustering for emerging theme discovery using embeddings."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Optional, Sequence

import numpy as np
from openai import AsyncOpenAI
from sklearn.cluster import DBSCAN
from sqlalchemy.ext.asyncio import AsyncSession

from voc_app.config import get_settings
from voc_app.models import Insight, Theme

logger = logging.getLogger(__name__)


@dataclass(slots=True)
class Cluster:
    """Represents a discovered theme cluster."""

    cluster_id: int
    insights: list[str]  # insight IDs
    centroid: list[float]
    size: int
    sample_texts: list[str]


@dataclass(slots=True)
class ClusteringSummary:
    """Summary of clustering results."""

    clusters: list[Cluster]
    noise_count: int
    total_insights: int


class ThemeClusterer:
    """Discovers emerging themes through embedding-based clustering."""

    def __init__(
        self,
        *,
        embedding_model: str = "text-embedding-3-small",
        min_cluster_size: int = 3,
        eps: float = 0.3,
        metric: str = "cosine",
    ) -> None:
        settings = get_settings()
        self.client = AsyncOpenAI(api_key=settings.openai_api_key)
        self.embedding_model = embedding_model
        self.min_cluster_size = min_cluster_size
        self.eps = eps
        self.metric = metric

    async def discover_themes(
        self, insights: Sequence[Insight]
    ) -> ClusteringSummary:
        """Discover themes from insights using clustering."""
        if len(insights) < self.min_cluster_size:
            logger.warning(f"Not enough insights for clustering: {len(insights)}")
            return ClusteringSummary(clusters=[], noise_count=0, total_insights=len(insights))

        # Generate embeddings
        texts = [self._prepare_text(insight) for insight in insights]
        embeddings = await self._generate_embeddings(texts)

        if not embeddings:
            return ClusteringSummary(clusters=[], noise_count=0, total_insights=len(insights))

        # Perform clustering
        clustering = DBSCAN(
            eps=self.eps,
            min_samples=self.min_cluster_size,
            metric=self.metric,
        )
        labels = clustering.fit_predict(embeddings)

        # Group insights by cluster
        clusters = self._build_clusters(insights, texts, embeddings, labels)

        noise_count = sum(1 for label in labels if label == -1)

        return ClusteringSummary(
            clusters=clusters,
            noise_count=noise_count,
            total_insights=len(insights),
        )

    async def suggest_theme_names(
        self, cluster: Cluster, existing_themes: list[str]
    ) -> dict[str, str]:
        """Use LLM to suggest theme name and description for a cluster."""
        sample_text = "\n".join(cluster.sample_texts[:5])

        prompt = f"""Based on the following customer feedback samples, suggest a theme name and description.

Existing Themes (avoid duplicates):
{', '.join(existing_themes)}

Sample Feedback:
{sample_text}

Return JSON with:
- theme_name: concise name (2-4 words)
- description: brief description (1-2 sentences)
- confidence: your confidence this is a cohesive theme (0-1)"""

        try:
            response = await self.client.chat.completions.create(
                model="gpt-4",
                messages=[
                    {"role": "system", "content": "You are a theme discovery assistant."},
                    {"role": "user", "content": prompt},
                ],
                response_format={"type": "json_object"},
                temperature=0.3,
                max_tokens=300,
            )

            content = response.choices[0].message.content
            return eval(content)  # Safe since it's from OpenAI

        except Exception as exc:
            logger.error(f"Theme name suggestion failed: {exc}")
            return {
                "theme_name": f"Emerging Theme {cluster.cluster_id}",
                "description": "Automatically discovered theme",
                "confidence": 0.5,
            }

    def _prepare_text(self, insight: Insight) -> str:
        """Prepare text for embedding."""
        parts = [insight.summary]

        if insight.pain_points:
            parts.extend([pp.get("description", "") for pp in insight.pain_points])

        if insight.feature_requests:
            parts.extend([fr.get("description", "") for fr in insight.feature_requests])

        return " ".join(parts).strip()

    async def _generate_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Generate embeddings for texts."""
        try:
            # OpenAI API supports batch embedding
            response = await self.client.embeddings.create(
                model=self.embedding_model,
                input=texts,
            )

            embeddings = [item.embedding for item in response.data]
            return embeddings

        except Exception as exc:
            logger.exception(f"Embedding generation failed: {exc}")
            return []

    def _build_clusters(
        self,
        insights: Sequence[Insight],
        texts: list[str],
        embeddings: list[list[float]],
        labels: list[int],
    ) -> list[Cluster]:
        """Build cluster objects from clustering results."""
        clusters_dict: dict[int, list[tuple[Insight, str, list[float]]]] = {}

        for insight, text, embedding, label in zip(insights, texts, embeddings, labels):
            if label == -1:  # Noise
                continue

            if label not in clusters_dict:
                clusters_dict[label] = []

            clusters_dict[label].append((insight, text, embedding))

        clusters = []
        for cluster_id, items in clusters_dict.items():
            insight_ids = [str(item[0].id) for item in items]
            sample_texts = [item[1] for item in items]
            embeddings_array = np.array([item[2] for item in items])
            centroid = embeddings_array.mean(axis=0).tolist()

            clusters.append(
                Cluster(
                    cluster_id=cluster_id,
                    insights=insight_ids,
                    centroid=centroid,
                    size=len(items),
                    sample_texts=sample_texts[:10],  # Keep top 10 samples
                )
            )

        return clusters


async def discover_emerging_themes(
    insights: Sequence[Insight],
    *,
    min_cluster_size: int = 3,
    eps: float = 0.3,
) -> ClusteringSummary:
    """Convenience helper for theme discovery."""
    clusterer = ThemeClusterer(
        min_cluster_size=min_cluster_size,
        eps=eps,
    )
    return await clusterer.discover_themes(insights)
