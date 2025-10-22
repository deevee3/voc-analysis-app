"""Utilities for normalizing and deduplicating raw crawl text."""

from __future__ import annotations

import html
import re
import unicodedata
from dataclasses import dataclass, field
from hashlib import sha256
from typing import Any, Iterable, Iterator, Sequence


@dataclass(slots=True)
class CleaningPayload:
    """Container representing a raw piece of text slated for cleaning."""

    identifier: str | None
    text: str
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(slots=True)
class CleaningOptions:
    """Configuration toggles for the cleaning routine."""

    deduplicate: bool = True
    min_characters: int = 40
    collapse_whitespace: bool = True
    lowercase: bool = False
    remove_urls: bool = True
    remove_hashtags: bool = False
    remove_markdown: bool = True


@dataclass(slots=True)
class CleanedRecord:
    """Result of cleaning a single payload."""

    identifier: str | None
    cleaned_text: str
    metadata: dict[str, Any]
    fingerprint: str
    is_duplicate: bool
    discarded: bool
    discard_reason: str | None


@dataclass(slots=True)
class CleaningSummary:
    """Aggregated output for a batch cleaning operation."""

    records: list[CleanedRecord]
    duplicates: list[CleanedRecord]
    discarded: list[CleanedRecord]


class TextCleaner:
    """Applies deterministic normalization and deduplication to text content."""

    def __init__(self, options: CleaningOptions | None = None) -> None:
        self.options = options or CleaningOptions()

    def clean_batch(self, payloads: Iterable[CleaningPayload]) -> CleaningSummary:
        seen_fingerprints: set[str] = set()
        cleaned_records: list[CleanedRecord] = []
        duplicates: list[CleanedRecord] = []
        discarded: list[CleanedRecord] = []

        for payload in payloads:
            cleaned_text = self._clean_text(payload.text)
            fingerprint = self._fingerprint(cleaned_text)

            is_duplicate = self.options.deduplicate and fingerprint in seen_fingerprints
            discard_reason = self._determine_discard_reason(cleaned_text)
            discarded_flag = discard_reason is not None

            record = CleanedRecord(
                identifier=payload.identifier,
                cleaned_text=cleaned_text,
                metadata=payload.metadata,
                fingerprint=fingerprint,
                is_duplicate=is_duplicate,
                discarded=discarded_flag,
                discard_reason=discard_reason,
            )

            if fingerprint not in seen_fingerprints:
                seen_fingerprints.add(fingerprint)

            if is_duplicate:
                duplicates.append(record)
            elif discarded_flag:
                discarded.append(record)
            else:
                cleaned_records.append(record)

        return CleaningSummary(records=cleaned_records, duplicates=duplicates, discarded=discarded)

    def _clean_text(self, text: str) -> str:
        normalized = unicodedata.normalize("NFKC", text)
        normalized = html.unescape(normalized)

        if self.options.remove_markdown:
            normalized = self._strip_markdown(normalized)

        normalized = self._strip_html(normalized)
        normalized = normalized.replace("\u200b", "")  # zero-width space

        if self.options.remove_urls:
            normalized = re.sub(r"https?://\S+", " ", normalized)

        if self.options.remove_hashtags:
            normalized = re.sub(r"#[\w-]+", " ", normalized)

        normalized = re.sub(r"@[\w-]+", " ", normalized)

        if self.options.collapse_whitespace:
            normalized = re.sub(r"\s+", " ", normalized).strip()

        if self.options.lowercase:
            normalized = normalized.lower()

        return normalized

    @staticmethod
    def _strip_html(text: str) -> str:
        if "<" not in text:
            return text
        return re.sub(r"<[^>]+>", " ", text)

    @staticmethod
    def _strip_markdown(text: str) -> str:
        text = re.sub(r"`{1,3}.*?`{1,3}", " ", text, flags=re.DOTALL)
        text = re.sub(r"!\[[^\]]*\]\([^\)]*\)", " ", text)
        text = re.sub(r"\[[^\]]*\]\([^\)]*\)", " ", text)
        text = re.sub(r"[*_]{1,3}([^*_]+)[*_]{1,3}", r"\1", text)
        text = re.sub(r"^>+\s?", "", text, flags=re.MULTILINE)
        text = re.sub(r"^#{1,6}\s", "", text, flags=re.MULTILINE)
        return text

    def _determine_discard_reason(self, text: str) -> str | None:
        if not text:
            return "empty"
        if len(text) < self.options.min_characters:
            return "too_short"
        return None

    @staticmethod
    def _fingerprint(text: str) -> str:
        return sha256(text.encode("utf-8")).hexdigest()


def clean_texts(
    payloads: Sequence[CleaningPayload],
    options: CleaningOptions | None = None,
) -> CleaningSummary:
    """Convenience helper to clean a batch of payloads."""

    cleaner = TextCleaner(options)
    return cleaner.clean_batch(payloads)
