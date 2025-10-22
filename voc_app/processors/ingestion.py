"""Ingestion pipeline orchestrating crawl outputs into persistence layers."""

from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import Iterable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from voc_app.crawlers import CrawlOutput
from voc_app.models import CrawlRun, DataSource
from voc_app.processors.cleaner import (
    CleanedRecord,
    CleaningOptions,
    CleaningPayload,
    CleaningSummary,
    TextCleaner,
)
from voc_app.services.storage import CrawlStorageService, StorageOptions


@dataclass(slots=True)
class IngestionResult:
    """Report of ingestion outcomes for a batch."""

    stored_feedback_ids: list[str]
    cleaning_summary: CleaningSummary


class IngestionPipeline:
    """Coordinates cleaning and storage for crawl outputs."""

    def __init__(
        self,
        session: AsyncSession,
        *,
        cleaning_options: CleaningOptions | None = None,
        storage_options: StorageOptions | None = None,
    ) -> None:
        self.session = session
        self.cleaner = TextCleaner(cleaning_options)
        self.storage_service = CrawlStorageService(session, storage_options)

    async def ingest(
        self,
        *,
        data_source: DataSource,
        crawl_run: CrawlRun,
        outputs: Sequence[CrawlOutput],
    ) -> IngestionResult:
        summary = self.cleaner.clean_batch(self._build_payloads(outputs))

        # Filter out duplicates and discarded entries
        pipeline_ready = [record for record in summary.records if not record.discarded]

        if not pipeline_ready:
            return IngestionResult(stored_feedback_ids=[], cleaning_summary=summary)

        # Persist sanitized payloads
        feedback_records = await self.storage_service.persist_outputs(
            data_source=data_source,
            crawl_run=crawl_run,
            outputs=self._rebuild_outputs(outputs, pipeline_ready),
        )

        stored_ids = [str(record.id) for record in feedback_records]
        return IngestionResult(stored_feedback_ids=stored_ids, cleaning_summary=summary)

    def _build_payloads(self, outputs: Sequence[CrawlOutput]) -> list[CleaningPayload]:
        payloads: list[CleaningPayload] = []
        for output in outputs:
            identifier = output.target.metadata.get("external_id") if output.target.metadata else None
            payloads.append(
                CleaningPayload(
                    identifier=identifier or output.target.url,
                    text=output.raw.html or "",
                    metadata={
                        "target": output.target.metadata,
                        "crawler": output.raw.metadata,
                        "url": output.target.url,
                    },
                )
            )
        return payloads

    def _rebuild_outputs(
        self, outputs: Sequence[CrawlOutput], records: Iterable[CleanedRecord]
    ) -> list[CrawlOutput]:
        record_map = {record.identifier: record for record in records}
        filtered: list[CrawlOutput] = []

        for output in outputs:
            identifier = output.target.metadata.get("external_id") if output.target.metadata else None
            lookup_key = identifier or output.target.url
            record = record_map.get(lookup_key)
            if not record:
                continue

            output.raw.html = record.cleaned_text
            output.cleaned_html = record.cleaned_text
            filtered.append(output)
        return filtered


async def run_ingestion_pipeline(
    session: AsyncSession,
    *,
    data_source: DataSource,
    crawl_run: CrawlRun,
    outputs: Iterable[CrawlOutput],
    cleaning_options: CleaningOptions | None = None,
    storage_options: StorageOptions | None = None,
) -> IngestionResult:
    pipeline = IngestionPipeline(
        session,
        cleaning_options=cleaning_options,
        storage_options=storage_options,
    )
    return await pipeline.ingest(
        data_source=data_source,
        crawl_run=crawl_run,
        outputs=list(outputs),
    )
