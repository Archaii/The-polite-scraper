"""Polite HTTP fetching with a local HTML cache."""

import time
from pathlib import Path

import truststore

# Verify HTTPS with the operating system's certificate store instead of
# Python's bundled one. Needed when antivirus software (e.g. AVG) scans HTTPS
# traffic and re-signs certificates with its own root. Must run before
# requests opens any connection. On other machines it has no effect.
truststore.inject_into_ssl()

import requests  # noqa: E402

from config import DELAY_SECONDS, TIMEOUT_SECONDS, USER_AGENT  # noqa: E402


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


def fetch(url: str, cache_path: Path) -> str:
    """Return the HTML for url, reading the cached copy when one exists.

    Only a 200 response is saved to the cache. Anything else raises FetchError.
    """
    global _last_request_at

    if cache_path.exists():
        body = cache_path.read_bytes()
        print(f"CACHE HIT {url} ({len(body):,} bytes)")
        return body.decode("utf-8")

    _wait_politely()
    try:
        response = _session.get(url, timeout=TIMEOUT_SECONDS)
    finally:
        # Count failed requests too: they reached the site all the same.
        _last_request_at = time.monotonic()

    if response.status_code != 200:
        raise FetchError(url, response.status_code)

    # Keep the raw bytes and decode them as UTF-8 ourselves. Letting requests
    # guess the encoding can turn "£" into "Â£".
    body = response.content
    cache_path.parent.mkdir(parents=True, exist_ok=True)
    cache_path.write_bytes(body)
    print(f"FETCH {url} {response.status_code} ({len(body):,} bytes)")
    return body.decode("utf-8")
