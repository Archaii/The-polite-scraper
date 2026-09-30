"""The run report: a few honest numbers written at the end of every run."""

import time
from dataclasses import dataclass, field
from datetime import datetime, timezone

from fetcher import FetchStats


def utc_now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class RunReport:
    inject_bad_url: bool
    started_at: str = field(default_factory=utc_now)
    catalogue_pages: int = 0
    book_urls: int = 0
    valid_records: int = 0
    invalid_records: int = 0
    # One {"url", "reason"} entry per page that could not be fetched or read.
    failures: list[dict] = field(default_factory=list)
    _started: float = field(default_factory=time.monotonic, repr=False)

    def add_failure(self, url: str, err: Exception) -> None:
        self.failures.append({"url": url, "reason": f"{type(err).__name__}: {err}"})

    def to_dict(self, fetch_stats: FetchStats) -> dict:
        return {
            "started_at": self.started_at,
            "finished_at": utc_now(),
            "duration_seconds": round(time.monotonic() - self._started, 2),
            "inject_bad_url": self.inject_bad_url,
            "catalogue_pages": self.catalogue_pages,
            "book_urls": self.book_urls,
            "requests_sent": fetch_stats.requests_sent,
            "pages_fetched": fetch_stats.pages_fetched,
            "cache_hits": fetch_stats.cache_hits,
            "retries": fetch_stats.retries,
            "valid_records": self.valid_records,
            "invalid_records": self.invalid_records,
            "failed_pages": len(self.failures),
            "failures": self.failures,
        }
