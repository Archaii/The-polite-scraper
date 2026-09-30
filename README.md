# The Polite Scraper

A small, polite scraping pipeline for the [Books to Scrape](https://books.toscrape.com) practice sandbox. It downloads the first three catalogue pages, visits all 60 book pages, and turns the HTML into clean, schema-checked JSON. It skips a broken page without crashing and ends every run with a short report.

FlyRank Internship · Backend Track · Week 5 · Assignment A9

```
fetch → extract → normalize → validate → store → report
```

> Status: Stage 2 of 6. The scraper follows the catalogue's "next" links through pages 1–3 and finds the 60 book URLs.

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

Expected summary:

```
catalogue_pages=3, discovered=60, unique_urls=60
```

## Politeness rules

- **Honest user-agent:** `FlyRankInternship-A9/1.0 (+https://github.com/Archaii/The-polite-scraper)`.
- **Timeout:** a request gives up after 10 seconds.
- **Delay:** at least 0.5 seconds between two real requests. Cache hits never wait, because they never leave the computer.
- **Scope:** the site's own "next" links decide the pages, and the scraper stops after 3. No page or book URL is hardcoded except the first catalogue page.
- **Status check:** only `200` counts as a page. Any other status is a failed fetch, and it is never cached.
- **Cache:** every page is saved to `cache/` and read from there on later runs, so the site sees each request once.

## Notes

- **Antivirus HTTPS scanning.** Some antivirus products (for example, AVG) re-sign HTTPS certificates. Python's bundled certificates then fail with `CERTIFICATE_VERIFY_FAILED`. [src/fetcher.py](src/fetcher.py) uses `truststore`, which makes Python trust the operating system's certificate store. On other machines, this has no effect.
