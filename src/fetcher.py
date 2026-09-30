"""Polite HTTP fetching with a local HTML cache."""

import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

import truststore

# Verify HTTPS with the operating system's certificate store instead of
# Python's bundled one. Needed when antivirus software (e.g. AVG) scans HTTPS
# traffic and re-signs certificates with its own root. Must run before
# requests opens any connection. On other machines it has no effect.
truststore.inject_into_ssl()

import requests  # noqa: E402

from config import (  # noqa: E402
    DELAY_SECONDS,
    MAX_ATTEMPTS,
    RETRY_WAIT_SECONDS,
    TIMEOUT_SECONDS,
    USER_AGENT,
)


class FetchError(Exception):
    """A request that did not return a usable page (any status other than 200)."""

    def __init__(self, url: str, status: int):
        super().__init__(f"HTTP {status} for {url}")
        self.url = url
        self.status = status


# One session for every request: it reuses the connection and sends the
# user-agent header each time.
_session = requests.Session()
_session.headers["User-Agent"] = USER_AGENT

# When the last real request finished, so the next one can keep its distance.
_last_request_at: float | None = None


def _wait_politely() -> None:
    """Sleep until at least DELAY_SECONDS have passed since the last real request."""
    if _last_request_at is None:
        return
    elapsed = time.monotonic() - _last_request_at
    if elapsed < DELAY_SECONDS:
        time.sleep(DELAY_SECONDS - elapsed)


@dataclass
class Page:
    url: str
    html: str
    # When the page was really downloaded, as UTC ISO 8601 ("2026-09-30T12:39:05Z").
    fetched_at: str
    from_cache: bool


def _fetched_at(cache_path: Path) -> str:
    """The download time of a cached page.

    The cache file is written once, right after the download, so its
    modification time is the fetch time. A cache hit keeps the original
    time instead of pretending the page was fetched again.
    """
    mtime = cache_path.stat().st_mtime
    return datetime.fromtimestamp(mtime, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


@dataclass
class FetchStats:
    """Counts for the run report, kept here because every page goes through fetch()."""

    requests_sent: int = 0  # every HTTP request, failures and retries included
    pages_fetched: int = 0  # real downloads that returned 200
    cache_hits: int = 0
    retries: int = 0


stats = FetchStats()


def _is_worth_retrying(status: int) -> bool:
    """Only a server error (5xx) may be temporary.

    A 404 means the page does not exist, and asking again will not create it.
    A 403 means the site said no, and asking again is how a polite robot
    becomes a pest. No other status is retried either.
    """
    return 500 <= status <= 599


def _get(url: str) -> requests.Response:
    """Send one GET, waiting first so real requests stay DELAY_SECONDS apart."""
    global _last_request_at

    _wait_politely()
    stats.requests_sent += 1
    try:
        return _session.get(url, timeout=TIMEOUT_SECONDS)
    finally:
        # Count failed requests too: they reached the site all the same.
        _last_request_at = time.monotonic()


def _get_with_one_retry(url: str) -> requests.Response:
    """GET url, retrying once after a timeout, a connection error, or a 5xx."""
    for attempt in range(1, MAX_ATTEMPTS + 1):
        is_last_attempt = attempt == MAX_ATTEMPTS
        try:
            response = _get(url)
        except (requests.Timeout, requests.ConnectionError) as err:
            if is_last_attempt:
                raise
            reason = type(err).__name__
        else:
            if is_last_attempt or not _is_worth_retrying(response.status_code):
                return response
            reason = f"HTTP {response.status_code}"

        stats.retries += 1
        print(f"RETRY {url} after {reason}, waiting {RETRY_WAIT_SECONDS}s")
        time.sleep(RETRY_WAIT_SECONDS)

    raise AssertionError("unreachable: the last attempt always returns or raises")


def fetch(url: str, cache_path: Path) -> Page:
    """Return the page at url, reading the cached copy when one exists.

    Only a 200 response is saved to the cache. Anything else raises FetchError.
    Timeouts and connection errors that survive the retry raise the requests
    exception.
    """
    if cache_path.exists():
        body = cache_path.read_bytes()
        stats.cache_hits += 1
        print(f"CACHE HIT {url} ({len(body):,} bytes)")
        return Page(url, body.decode("utf-8"), _fetched_at(cache_path), from_cache=True)

    response = _get_with_one_retry(url)
    if response.status_code != 200:
        raise FetchError(url, response.status_code)

    # Keep the raw bytes and decode them as UTF-8 ourselves. Letting requests
    # guess the encoding can turn "£" into "Â£".
    body = response.content
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(body)
    stats.pages_fetched += 1
    print(f"FETCH {url} {response.status_code} ({len(body):,} bytes)")
    return Page(url, body.decode("utf-8"), _fetched_at(cache_path), from_cache=False)
