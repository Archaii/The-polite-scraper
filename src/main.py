"""Entry point for the polite scraper.

Run from the project folder:
    python src/main.py
"""

import sys

import requests

from config import CACHE_DIR, START_URL
from fetcher import FetchError, fetch


def main() -> int:
    try:
        fetch(START_URL, CACHE_DIR / "catalogue-page-1.html")
    except (FetchError, requests.RequestException) as err:
        print(f"FAILED {START_URL}: {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
