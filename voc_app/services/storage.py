"""Storage utilities for persisting raw crawl outputs."""

from __future__ import annotations

import asyncio
import uuid
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterable, Sequence

from sqlalchemy.ext.asyncio import AsyncSession

from voc_app.config import BASE_DIR
from voc_app.models import CrawlRun, DataSource, Feedback
from voc_app.crawlers import CrawlOutput


@dataclass(slots=True)
class StorageOptions:
    """Configuration controlling how crawl outputs are stored."""

    store_files: bool = True
    base_directory: Path = BASE_DIR.parent / "data" / "raw"


class CrawlStorageService:
    """Persist crawl outputs to durable storage destinations."""

    def __init__(self, session: AsyncSession, options: StorageOptions | None = None) -> None:
        self._session = session
        self._options = options or StorageOptions()

    async def persist_outputs(
        self,
        *,
        data_source: DataSource,
        crawl_run: CrawlRun,
        outputs: Sequence[CrawlOutput],
    ) -> list[Feedback]:
        """Persist a batch of crawl outputs."""

        if not outputs:
            return []

        feedback_records: list[Feedback] = []
        for index, output in enumerate(outputs, start=1):
            file_path = await self._maybe_store_file(
                data_source=data_source, crawl_run=crawl_run, index=index, html=output.raw.html
            )

            metadata = self._build_metadata(output, file_path)
            feedback = Feedback(
                data_source_id=data_source.id,
                crawl_run_id=crawl_run.id,
                raw_content=output.raw.html,
                clean_content=output.cleaned_html,
                url=output.target.url,
                metadata=metadata,
            )
            feedback_records.append(feedback)

        self._session.add_all(feedback_records)
        await self._session.flush()
        return feedback_records

    async def _maybe_store_file(
        self,
        *,
        data_source: DataSource,
        crawl_run: CrawlRun,
        index: int,
        html: str | None,
    ) -> Path | None:
        if not self._options.store_files or not html:
            return None

        timestamp = datetime.utcnow().strftime("%Y%m%dT%H%M%S")
        file_name = f"{crawl_run.id}_{index}_{timestamp}_{uuid.uuid4().hex}.html"
        target_dir = self._options.base_directory / data_source.platform
        target_path = target_dir / file_name

        target_dir.mkdir(parents=True, exist_ok=True)
        await asyncio.to_thread(target_path.write_text, html, encoding="utf-8")
        return target_path

    @staticmethod
    def _build_metadata(output: CrawlOutput, file_path: Path | None) -> dict:
        metadata: dict = {
            "target_metadata": output.target.metadata,
            "query": output.target.query,
            "crawler_metadata": output.raw.metadata,
        }

        if output.markdown:
            metadata["markdown"] = output.markdown
        if file_path:
            metadata["raw_file_path"] = str(file_path)

        # Remove keys with None values for cleaner storage
        return {key: value for key, value in metadata.items() if value is not None}


async def persist_crawl_outputs(
    session: AsyncSession,
    *,
    data_source: DataSource,
    crawl_run: CrawlRun,
    outputs: Iterable[CrawlOutput],
    options: StorageOptions | None = None,
) -> list[Feedback]:
    """Convenience helper for persisting crawl outputs."""

    service = CrawlStorageService(session, options)
    return await service.persist_outputs(
        data_source=data_source,
        crawl_run=crawl_run,
        outputs=list(outputs),
    )
