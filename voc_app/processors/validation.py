"""Validation checks for processed feedback and insight data."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Sequence

from voc_app.models import Feedback, Insight


@dataclass(slots=True)
class ValidationIssue:
    """Represents a single validation failure."""

    record_type: str
    record_id: str | None
    field: str
    message: str


@dataclass(slots=True)
class ValidationResult:
    """Aggregated validation output."""

    issues: list[ValidationIssue]

    @property
    def is_valid(self) -> bool:
        return not self.issues


class DataValidator:
    """Runs structural validation checks on feedback and insights."""

    def validate_feedback(self, records: Sequence[Feedback]) -> ValidationResult:
        issues: list[ValidationIssue] = []

        for feedback in records:
            record_id = str(feedback.id) if feedback.id else None

            if not feedback.raw_content:
                issues.append(
                    ValidationIssue(
                        record_type="feedback",
                        record_id=record_id,
                        field="raw_content",
                        message="Raw content is required.",
                    )
                )

            if feedback.posted_at is None:
                issues.append(
                    ValidationIssue(
                        record_type="feedback",
                        record_id=record_id,
                        field="posted_at",
                        message="Posted timestamp missing.",
                    )
                )

            if not feedback.data_source_id:
                issues.append(
                    ValidationIssue(
                        record_type="feedback",
                        record_id=record_id,
                        field="data_source_id",
                        message="Feedback must reference a data source.",
                    )
                )

        return ValidationResult(issues=issues)

    def validate_insights(self, records: Sequence[Insight]) -> ValidationResult:
        issues: list[ValidationIssue] = []

        for insight in records:
            record_id = str(insight.id) if insight.id else None

            if not insight.feedback_id:
                issues.append(
                    ValidationIssue(
                        record_type="insight",
                        record_id=record_id,
                        field="feedback_id",
                        message="Insight must reference feedback.",
                    )
                )

            if insight.sentiment_score is not None and not (-1 <= float(insight.sentiment_score) <= 1):
                issues.append(
                    ValidationIssue(
                        record_type="insight",
                        record_id=record_id,
                        field="sentiment_score",
                        message="Sentiment score must be between -1 and 1.",
                    )
                )

            if insight.summary is None or not insight.summary.strip():
                issues.append(
                    ValidationIssue(
                        record_type="insight",
                        record_id=record_id,
                        field="summary",
                        message="Summary content missing.",
                    )
                )

        return ValidationResult(issues=issues)


def validate_feedback(records: Iterable[Feedback]) -> ValidationResult:
    return DataValidator().validate_feedback(list(records))


def validate_insights(records: Iterable[Insight]) -> ValidationResult:
    return DataValidator().validate_insights(list(records))
