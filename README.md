# The Polite Scraper

A small, polite scraping pipeline for the [Books to Scrape](https://books.toscrape.com) practice sandbox. It downloads the first three catalogue pages, visits all 60 book pages, and turns the HTML into clean, schema-checked JSON. It skips a broken page without crashing and ends every run with a short report.

FlyRank Internship · Backend Track · Week 5 · Assignment A9

```
fetch → extract → normalize → validate → store → report
```

> Status: Stage 5 of 6. The scraper finds the 60 book URLs on catalogue pages 1–3, extracts and validates each book, writes `output/books.json`, skips a broken page without stopping, and reports every run.

## Target classification

| Question | Answer |
|---|---|
| Site | Books to Scrape: `https://books.toscrape.com` |
| What it is | A practice sandbox, part of [toscrape.com](https://toscrape.com). It is a fictional bookstore built for people who learn web scraping. |
| Why this site | The site exists for this purpose. The toscrape.com page describes it as *"A fictional bookstore that desperately wants to be scraped. It's a safe place for beginners learning web scraping and for developers validating their scraping technologies as well."* |
| How much | Only the first 3 catalogue pages (`catalogue/page-1.html` to `page-3.html`) and the 60 book pages that they link to. The site has 1,000 books. This scraper touches only 60 of them. |
| What data | For each book: title, product URL, price, availability, star rating, description, plus the source page and fetch time as provenance. No personal data. The site has none. |
| JavaScript needed? | No. toscrape.com lists "Requires JavaScript: ✘" for Books. The data is in the HTML that the server sends. |

**robots.txt check** (checked on 2026-09-30, one request):

```
GET https://books.toscrape.com/robots.txt
→ 404 Not Found (nginx/1.21.6)
```

Result: **no robots file found.** A missing file is not permission. The permission comes from the sandbox statement above. The scraper still follows the politeness rules: an honest user-agent, a timeout, a delay of at least 0.5 s between requests, and a local cache.

**Why this is appropriate:** Books to Scrape is a public sandbox that its owners built so people can practise scraping, and this project collects a small, fixed slice of fictional data from it at a slow rate.

**I will not reuse this code on another site without checking its rules and terms first.**

## Tech stack (Python lane)

- Python 3.10+
- `requests` for HTTP
- `beautifulsoup4` for HTML parsing
- `pydantic` for schema validation
- `truststore` so HTTPS uses the operating system's certificates (see Notes)
- Built-in `json` for output

## Setup

```
python -m venv .venv
.venv\Scripts\activate          # Windows
source .venv/bin/activate       # macOS / Linux
pip install -r requirements.txt
```

## Run

```
python src/main.py
```

The first run downloads each page and prints `FETCH`. Later runs read the saved copies in `cache/` and print `CACHE HIT`. Delete `cache/` to download again.

The first run makes 63 requests (3 catalogue pages + 60 book pages) and takes about 40 seconds because of the delay. Expected output, after the `FETCH` / `CACHE HIT` lines:

```
catalogue_pages=3, discovered=60, unique_urls=60
detail_pages=60
valid_records=60, invalid_records=0
wrote output/books.json and output/errors.json
failed_pages=0, pages_fetched=63, cache_hits=0, duration=<seconds>s
wrote output/run-report.json
```

| File | Contents |
|---|---|
| `output/books.json` | The valid records, exactly 60, one per book. |
| `output/errors.json` | Records that failed the schema, each with its `reason` and its raw values. An empty list on a clean run. |
| `output/run-report.json` | What happened on the last run: counts, cache hits, failures, and duration. |

### Prove that one bad page does not stop the run

```
python src/main.py --inject-bad-url
```

This adds one made-up book URL that returns `404`. The scraper logs `SKIP` for it and carries on. `books.json` still has the 60 good records, and `run-report.json` shows `"failed_pages": 1`. The test costs the site one request, because a `404` is never retried or cached.

## Failures and the run report

- **One page at a time.** Each book page is fetched, extracted, and validated on its own. A page that fails is logged as `SKIP`, recorded in the report, and skipped. The other 59 records survive.
- **One retry, only when it can help.** A timeout, a connection error, or a `5xx` server error gets one more try after 2 seconds. A `404` (the page does not exist) and a `403` (the site said no) are never retried. Neither is any other status.
- **Catalogue failure stops the run.** Without the catalogue there is no list of books. The run exits with code `1`, and `books.json` from the last good run is left untouched.
- **A report on every run.** `output/run-report.json` is written at the end of every run, including a run that stops early.

| Field | Meaning |
|---|---|
| `started_at`, `finished_at`, `duration_seconds` | When the run happened and how long it took |
| `inject_bad_url` | `true` when the test URL was added |
| `catalogue_pages`, `book_urls` | How many catalogue pages were read and book URLs were tried |
| `requests_sent` | Every HTTP request, failures and retries included |
| `pages_fetched` | Real downloads that returned `200` |
| `cache_hits` | Pages read from `cache/` instead of the site |
| `retries` | Second attempts after a timeout, connection error, or `5xx` |
| `valid_records`, `invalid_records` | Records that passed or failed the schema |
| `failed_pages`, `failures` | Pages that could not be fetched or read, each with its URL and reason |

## Raw record

Each book page becomes one raw record with eight fields. The values are the text exactly as the page shows it. Stage 4 cleans them.

```json
{
  "title": "A Light in the Attic",
  "product_url": "https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
  "price_text": "£51.77",
  "availability_text": "In stock (22 available)",
  "rating_text": "Three",
  "description": "It's hard to imagine a world without A Light in the Attic. ...",
  "source_page": "https://books.toscrape.com/catalogue/page-1.html",
  "fetched_at": "2026-09-30T12:44:20Z"
}
```

- Every selector is scoped to the product area (`article.product_page`), so a second price elsewhere on the page can never be picked up.
- A book without a description gets `"description": null`. Text is never invented.
- `source_page` and `fetched_at` are the provenance: where and when the fact came from. `fetched_at` is the time of the real download. A cache hit keeps the original time.

## Record schema

A scraped page is untrusted input. Every raw record is normalized, then checked against the Pydantic model `Book` in [src/models.py](src/models.py) before it is stored.

| Field | Type | Required | Rule |
|---|---|---|---|
| `title` | string | yes | not empty |
| `product_url` | string | yes | absolute `https://` URL; the record's identity (canonical URL) |
| `price_text` | string | yes | the raw price, e.g. `"£51.77"` |
| `price_gbp` | number | yes | parsed from `price_text`; greater than 0 |
| `availability_text` | string | yes | not empty |
| `rating_text` | string | yes | one of `One`, `Two`, `Three`, `Four`, `Five` |
| `description` | string or null | no | `null` when the page has no description |
| `source_page` | string | yes | absolute `https://` URL of the catalogue page |
| `fetched_at` | datetime | yes | UTC, ISO 8601 |

No other fields are allowed.

- **Raw and clean side by side.** `price_text` stays as scraped. `price_gbp` is the clean number a program can sort and compare.
- **Rejected records never reach `books.json`.** A record that fails goes to `errors.json` with the reason, for example `price_gbp: Input should be a valid number`.
- **Idempotent.** Records are keyed by `product_url`, so a book seen twice counts once. Both files are rewritten on every run, never appended to. Running the scraper twice gives the same 60 records, not 120.

## Politeness rules

- **Honest user-agent:** `FlyRankInternship-A9/1.0 (+https://github.com/Archaii/The-polite-scraper)`.
- **Timeout:** a request gives up after 10 seconds.
- **Delay:** at least 0.5 seconds between two real requests. Cache hits never wait, because they never leave the computer.
- **Scope:** the site's own "next" links decide the pages, and the scraper stops after 3. No page or book URL is hardcoded except the first catalogue page.
- **Status check:** only `200` counts as a page. Any other status is a failed fetch, and it is never cached.
- **Retry:** one retry after 2 seconds, only for a timeout, a connection error, or a `5xx`. Never for `404` or `403`.
- **Cache:** every page is saved to `cache/` and read from there on later runs, so the site sees each request once.

## Notes

- **Long file names on Windows.** Some book slugs are almost 200 characters long, which breaks the 260-character path limit on Windows. Cache file names are cut to 80 characters plus a short hash of the URL.
- **Antivirus HTTPS scanning.** Some antivirus products (for example, AVG) re-sign HTTPS certificates. Python's bundled certificates then fail with `CERTIFICATE_VERIFY_FAILED`. [src/fetcher.py](src/fetcher.py) uses `truststore`, which makes Python trust the operating system's certificate store. On other machines, this has no effect.
