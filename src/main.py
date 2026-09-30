"""Entry point for the polite scraper.

Run from the project folder:
    python src/main.py
"""

import hashlib
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

from config import CACHE_DIR, OUTPUT_DIR
from discover import discover_books
from extract import ExtractError, extract_book
from fetcher import FetchError, fetch
from models import validate_records
from store import write_json


MAX_SLUG_LENGTH = 80


def book_cache_path(book_url: str) -> Path:
    """cache/books/<slug>.html, where the slug is the book's folder in its URL.

    .../catalogue/a-light-in-the-attic_1000/index.html -> a-light-in-the-attic_1000

    Some slugs are close to 200 characters, which breaks the 260-character
    path limit on Windows. Long slugs are cut and get a short hash of the full
    URL, so two books never share a file.
    """
    slug = urlparse(book_url).path.rstrip("/").split("/")[-2]
    if len(slug) > MAX_SLUG_LENGTH:
        digest = hashlib.sha1(book_url.encode("utf-8")).hexdigest()[:8]
        slug = f"{slug[:MAX_SLUG_LENGTH]}-{digest}"
    return CACHE_DIR / "books" / f"{slug}.html"


def main() -> int:
    # Book descriptions contain characters the Windows console code page cannot print.
    sys.stdout.reconfigure(encoding="utf-8")

    try:
        discovery = discover_books()
        print(
            f"catalogue_pages={len(discovery.catalogue_pages)}, "
            f"discovered={discovery.discovered}, "
            f"unique_urls={len(discovery.book_sources)}"
        )

        records = []
        for book_url, source_page in discovery.book_sources.items():
            page = fetch(book_url, book_cache_path(book_url))
            records.append(extract_book(page.html, book_url, source_page, page.fetched_at))
    except (FetchError, ExtractError, requests.RequestException) as err:
        print(f"FAILED: {err}")
        return 1

    print(f"detail_pages={len(records)}")

    books, errors = validate_records(records)
    write_json(OUTPUT_DIR / "books.json", [book.model_dump(mode="json") for book in books])
    write_json(OUTPUT_DIR / "errors.json", errors)
    print(f"valid_records={len(books)}, invalid_records={len(errors)}")
    print("wrote output/books.json and output/errors.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
