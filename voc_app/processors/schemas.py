"""Pydantic schemas for GPT-5 extraction responses."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field, field_validator


class SentimentAnalysis(BaseModel):
    """Structured sentiment assessment."""

    score: float = Field(..., ge=-1.0, le=1.0, description="Sentiment score between -1 (negative) and 1 (positive)")
    label: str = Field(..., description="Categorical label: positive, negative, neutral, or mixed")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence score for sentiment classification")

    @field_validator("label")
    @classmethod
    def validate_label(cls, v: str) -> str:
        allowed = {"positive", "negative", "neutral", "mixed"}
        if v.lower() not in allowed:
            raise ValueError(f"Label must be one of {allowed}")
        return v.lower()


class PainPoint(BaseModel):
    """Individual customer pain point."""

    description: str = Field(..., description="Clear description of the problem or frustration")
    severity: str = Field(..., description="Impact level: critical, high, medium, low")
    category: Optional[str] = Field(None, description="Pain point category (e.g., usability, performance, cost)")


class FeatureRequest(BaseModel):
    """Customer feature request or enhancement idea."""

    description: str = Field(..., description="Description of requested feature or improvement")
    priority: str = Field(..., description="Implied priority: urgent, high, medium, low")
    use_case: Optional[str] = Field(None, description="Stated use case or motivation")


class CompetitorMention(BaseModel):
    """Reference to competitor products or comparisons."""

    competitor_name: str = Field(..., description="Name of competitor mentioned")
    context: str = Field(..., description="Context of mention (comparison, switch, alternative)")
    sentiment: str = Field(..., description="Sentiment toward competitor: positive, negative, neutral")


class CustomerContext(BaseModel):
    """Contextual information about the customer."""

    user_segment: Optional[str] = Field(None, description="Inferred user segment (e.g., enterprise, SMB, individual)")
    experience_level: Optional[str] = Field(None, description="Expertise level: beginner, intermediate, expert")
    use_case_domain: Optional[str] = Field(None, description="Domain or industry context")


class InsightExtraction(BaseModel):
    """Complete structured extraction from customer feedback."""

    sentiment: SentimentAnalysis
    summary: str = Field(..., min_length=10, description="Concise summary of key message")
    pain_points: list[PainPoint] = Field(default_factory=list, description="Identified pain points or problems")
    feature_requests: list[FeatureRequest] = Field(default_factory=list, description="Feature requests or enhancements")
    competitor_mentions: list[CompetitorMention] = Field(default_factory=list, description="Competitor references")
    customer_context: CustomerContext = Field(default_factory=CustomerContext, description="Customer background info")
    journey_stage: Optional[str] = Field(None, description="Customer journey stage: awareness, consideration, purchase, retention, advocacy")
    urgency_level: int = Field(default=3, ge=1, le=5, description="Urgency from 1 (low) to 5 (critical)")
    themes: list[str] = Field(default_factory=list, description="Relevant themes or topics")


class BatchInsightExtraction(BaseModel):
    """Response for batch processing multiple feedback items."""

    extractions: list[InsightExtraction] = Field(..., description="Extraction results for each input")
    batch_metadata: dict = Field(default_factory=dict, description="Batch processing metadata")
