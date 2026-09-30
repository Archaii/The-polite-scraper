"""Turn one book detail page into a raw record.

The extractor only reads what is on the page. It does not clean or judge the
values: Stage 4 normalizes and validates them. A field the page does not have
is stored as None, never invented.
"""

from bs4 import BeautifulSoup, Tag


class ExtractError(Exception):
    """The page has no product area, so it is not a book page."""


def _text(element: Tag | None) -> str | None:
    """The element's text with runs of whitespace collapsed, or None when missing or empty."""
    if element is None:
        return None
    text = " ".join(element.get_text().split())
    return text or None


def _rating(product: Tag) -> str | None:
    """The word rating ("One" to "Five") from <p class="star-rating Three">."""
    stars = product.select_one("p.star-rating")
    if stars is None:
        return None
    words = [name for name in stars.get("class", []) if name != "star-rating"]
    return words[0] if words else None


def _description(product: Tag) -> str | None:
    """The paragraph right after the "Product Description" heading, if the book has one."""
    heading = product.select_one("#product_description")
    if heading is None:
        return None
    return _text(heading.find_next_sibling("p"))


def extract_book(html: str, product_url: str, source_page: str, fetched_at: str) -> dict:
    """Return the eight raw fields of one book page."""
    soup = BeautifulSoup(html, "html.parser")

    # Every selector is scoped to the product area, so a price or heading
    # elsewhere on the page can never be picked up by mistake.
    product = soup.select_one("article.product_page")
    if product is None:
        raise ExtractError(f"no article.product_page on {product_url}")

    return {
        "title": _text(product.select_one("h1")),
        "product_url": product_url,
        "price_text": _text(product.select_one("p.price_color")),
        "availability_text": _text(product.select_one("p.instock.availability")),
        "rating_text": _rating(product),
        "description": _description(product),
        "source_page": source_page,
        "fetched_at": fetched_at,
    }
