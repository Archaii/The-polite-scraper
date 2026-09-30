"""Entry point for the polite scraper.

Run from the project folder:
    python src/main.py
"""

import sys

import requests

from discover import discover_books
from fetcher import FetchError


def main() -> int:
    try:
        discovery = discover_books()
    except (FetchError, requests.RequestException) as err:
        print(f"FAILED catalogue discovery: {err}")
        return 1

    print(
        f"catalogue_pages={len(discovery.catalogue_pages)}, "
        f"discovered={discovery.discovered}, "
        f"unique_urls={len(discovery.book_sources)}"
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
