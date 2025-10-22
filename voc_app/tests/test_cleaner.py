"""Tests for the text cleaning utility."""

import pytest

from voc_app.processors.cleaner import (
    CleanedRecord,
    CleaningOptions,
    CleaningPayload,
    TextCleaner,
    clean_texts,
)


class TestTextCleaner:
    """Test suite for TextCleaner."""

    def test_basic_cleaning_normalizes_whitespace(self):
        """Ensure whitespace collapsing works."""
        payload = CleaningPayload(identifier="test1", text="Hello    world\n\n\nfrom   here")
        cleaner = TextCleaner(CleaningOptions(deduplicate=False))
        summary = cleaner.clean_batch([payload])

        assert len(summary.records) == 1
        assert "Hello world from here" in summary.records[0].cleaned_text

    def test_removes_urls_when_configured(self):
        """Verify URL removal."""
        payload = CleaningPayload(
            identifier="test2", text="Check this out https://example.com/path for more info"
        )
        cleaner = TextCleaner(CleaningOptions(remove_urls=True, deduplicate=False))
        summary = cleaner.clean_batch([payload])

        assert "https://example.com" not in summary.records[0].cleaned_text
        assert "Check this out" in summary.records[0].cleaned_text

    def test_deduplication_flags_identical_content(self):
        """Duplicates should be flagged."""
        payloads = [
            CleaningPayload(identifier="a", text="Same content here"),
            CleaningPayload(identifier="b", text="Same content here"),
        ]
        cleaner = TextCleaner(CleaningOptions(deduplicate=True))
        summary = cleaner.clean_batch(payloads)

        assert len(summary.records) == 1
        assert len(summary.duplicates) == 1
        assert summary.duplicates[0].is_duplicate is True

    def test_discards_content_below_min_characters(self):
        """Short content should be discarded."""
        payload = CleaningPayload(identifier="short", text="Hi")
        cleaner = TextCleaner(CleaningOptions(min_characters=40))
        summary = cleaner.clean_batch([payload])

        assert len(summary.records) == 0
        assert len(summary.discarded) == 1
        assert summary.discarded[0].discard_reason == "too_short"

    def test_strips_html_tags(self):
        """HTML tags should be removed."""
        payload = CleaningPayload(identifier="html", text="<p>Hello <b>world</b></p>")
        cleaner = TextCleaner(CleaningOptions(deduplicate=False, min_characters=5))
        summary = cleaner.clean_batch([payload])

        assert "<p>" not in summary.records[0].cleaned_text
        assert "<b>" not in summary.records[0].cleaned_text
        assert "Hello world" in summary.records[0].cleaned_text

    def test_strips_markdown_formatting(self):
        """Markdown syntax should be removed when configured."""
        payload = CleaningPayload(
            identifier="md", text="# Heading\n\n**Bold text** and `code` here [link](url)"
        )
        cleaner = TextCleaner(CleaningOptions(remove_markdown=True, deduplicate=False, min_characters=10))
        summary = cleaner.clean_batch([payload])

        text = summary.records[0].cleaned_text
        assert "**" not in text
        assert "`" not in text
        assert "[link]" not in text
        assert "Heading" in text
        assert "Bold text" in text

    def test_convenience_helper(self):
        """Test the module-level convenience function."""
        payloads = [CleaningPayload(identifier="test", text="Sample text for cleaning")]
        summary = clean_texts(payloads)

        assert len(summary.records) == 1


class TestCleaningOptions:
    """Test configuration object."""

    def test_default_options_enable_deduplication(self):
        """Default options should enable dedup."""
        opts = CleaningOptions()
        assert opts.deduplicate is True

    def test_can_disable_url_removal(self):
        """URL removal can be toggled."""
        opts = CleaningOptions(remove_urls=False)
        assert opts.remove_urls is False
