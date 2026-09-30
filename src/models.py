"""The shape of a finished book record, and the step that cleans raw records into it.

A scraped page is untrusted input. Every record passes through normalize()
and then the Book schema before it may be stored.
"""

import re
from datetime import datetime
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, ValidationError


def _require_https(url: str) -> str:
    if not url.startswith("https://"):
        raise ValueError("must be an absolute https:// URL")
    return url


HttpsUrl = Annotated[str, AfterValidator(_require_https)]
NonEmptyText = Annotated[str, Field(min_length=1)]


class Book(BaseModel):
    model_config = ConfigDict(extra="forbid")

    title: NonEmptyText
    # The canonical URL: the record's identity. The same book counts once.
    product_url: HttpsUrl
    # Raw and clean values live side by side.
    price_text: NonEmptyText
    price_gbp: float = Field(gt=0)
    availability_text: NonEmptyText
    rating_text: Literal["One", "Two", "Three", "Four", "Five"]
    description: str | None = None
    # Provenance: where and when the facts came from.
    source_page: HttpsUrl
    fetched_at: datetime


# "£51.77" -> 51.77. Anything else does not match and is left for the schema to reject.
_PRICE_PATTERN = re.compile(r"£\s*(\d+(?:\.\d+)?)")


def parse_price_gbp(price_text: str | None) -> float | None:
    if price_text is None:
        return None
    match = _PRICE_PATTERN.fullmatch(price_text.strip())
    return float(match.group(1)) if match else None


def normalize(raw: dict) -> dict:
    """Add the clean values to a raw record. The raw values stay untouched."""
    return {**raw, "price_gbp": parse_price_gbp(raw.get("price_text"))}


def describe_errors(err: ValidationError) -> str:
    """One readable line per failed field, e.g. "price_gbp: Input should be a valid number"."""
    return "; ".join(
        f"{'.'.join(str(part) for part in error['loc'])}: {error['msg']}" for error in err.errors()
    )


def validate_records(raw_records: list[dict]) -> tuple[list[Book], list[dict]]:
    """Split raw records into valid books (unique by product_url) and rejected records.

    A rejected record keeps its reason and its raw values, so it can be inspected later.
    """
    books: dict[str, Book] = {}
    errors: list[dict] = []
    for raw in raw_records:
        try:
            book = Book.model_validate(normalize(raw))
        except ValidationError as err:
            errors.append(
                {"product_url": raw.get("product_url"), "reason": describe_errors(err), "raw": raw}
            )
            continue
        # Keyed by canonical URL: a book seen twice is stored once.
        books[book.product_url] = book
    return list(books.values()), errors
