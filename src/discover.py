"""Walk the catalogue pages and collect the link to every book."""

from dataclasses import dataclass, field
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from config import CACHE_DIR, MAX_CATALOGUE_PAGES, START_URL
from fetcher import fetch


@dataclass
class Discovery:
    catalogue_pages: list[str] = field(default_factory=list)
    # Every book link seen, duplicates included.
    discovered: int = 0
    # Unique book URL -> the catalogue page that first linked to it (its source_page).
    book_sources: dict[str, str] = field(default_factory=dict)


def discover_books(start_url: str = START_URL, max_pages: int = MAX_CATALOGUE_PAGES) -> Discovery:
    """Follow the catalogue's own "next" links from start_url, up to max_pages pages."""
    result = Discovery()
    page_url: str | None = start_url

    while page_url and len(result.catalogue_pages) < max_pages:
        page_number = len(result.catalogue_pages) + 1
        html = fetch(page_url, CACHE_DIR / f"catalogue-page-{page_number}.html")
        soup = BeautifulSoup(html, "html.parser")
        result.catalogue_pages.append(page_url)

        for link in soup.select("article.product_pod h3 a[href]"):
            # Links are relative (../book-name/index.html), so resolve them
            # against the page they came from.
            book_url = urljoin(page_url, link["href"])
            result.discovered += 1
            result.book_sources.setdefault(book_url, page_url)

        next_link = soup.select_one("li.next a[href]")
        page_url = urljoin(page_url, next_link["href"]) if next_link else None

    return result
