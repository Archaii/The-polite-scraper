"""Entry point for the polite scraper.

Run from the project folder:
    python src/main.py
    python src/main.py --inject-bad-url
"""

import argparse
import hashlib
import sys
from pathlib import Path
from urllib.parse import urlparse

import requests

import fetcher
from config import BAD_BOOK_URL, CACHE_DIR, OUTPUT_DIR
from discover import discover_books
from extract import ExtractError, extract_book
from fetcher import FetchError, fetch
from models import validate_records
from report import RunReport
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


# What can go wrong with one page: a bad status, a timeout or connection error
# that survived the retry, a page that is not a book page, a cache file that
# cannot be written, or bytes that are not UTF-8.
PAGE_ERRORS = (FetchError, ExtractError, requests.RequestException, OSError, UnicodeDecodeError)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Politely scrape the first 3 catalogue pages of Books to Scrape.")
    parser.add_argument(
        "--inject-bad-url",
        action="store_true",
        help="add one made-up book URL (404) to prove that a broken page is skipped, not fatal",
    )
    return parser.parse_args()


def scrape(report: RunReport) -> None:
    """Discover, fetch, extract, validate, and store. Fills in report as it goes."""
    discovery = discover_books()
    report.catalogue_pages = len(discovery.catalogue_pages)
    print(
        f"catalogue_pages={len(discovery.catalogue_pages)}, "
        f"discovered={discovery.discovered}, "
        f"unique_urls={len(discovery.book_sources)}"
    )

    book_sources = dict(discovery.book_sources)
    if report.inject_bad_url:
        book_sources[BAD_BOOK_URL] = discovery.catalogue_pages[0]
    report.book_urls = len(book_sources)

    # Each page is handled on its own: a broken one is logged and skipped,
    # and every other page still produces its record.
    records = []
    for book_url, source_page in book_sources.items():
        try:
            page = fetch(book_url, book_cache_path(book_url))
            records.append(extract_book(page.html, book_url, source_page, page.fetched_at))
        except PAGE_ERRORS as err:
            print(f"SKIP {book_url}: {type(err).__name__}: {err}")
            report.add_failure(book_url, err)
    print(f"detail_pages={len(records)}")

    books, errors = validate_records(records)
    report.valid_records = len(books)
    report.invalid_records = len(errors)
    write_json(OUTPUT_DIR / "books.json", [book.model_dump(mode="json") for book in books])
    write_json(OUTPUT_DIR / "errors.json", errors)
    print(f"valid_records={len(books)}, invalid_records={len(errors)}")
    print("wrote output/books.json and output/errors.json")


def main() -> int:
    # Book descriptions contain characters the Windows console code page cannot print.
    sys.stdout.reconfigure(encoding="utf-8")
    report = RunReport(inject_bad_url=parse_args().inject_bad_url)

    exit_code = 0
    try:
        scrape(report)
    except PAGE_ERRORS as err:
        # Without the catalogue there is no list of books, so the run stops here.
        # books.json from the last good run is left untouched.
        print(f"ABORTED: catalogue discovery failed: {type(err).__name__}: {err}")
        report.add_failure(getattr(err, "url", "catalogue"), err)
        exit_code = 1
    finally:
        # Written on every run, including one that stops early.
        summary = report.to_dict(fetcher.stats)
        write_json(OUTPUT_DIR / "run-report.json", summary)
        print(
            f"failed_pages={summary['failed_pages']}, pages_fetched={summary['pages_fetched']}, "
            f"cache_hits={summary['cache_hits']}, duration={summary['duration_seconds']}s"
        )
        print("wrote output/run-report.json")
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
