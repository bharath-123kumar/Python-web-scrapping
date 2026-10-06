# Multi-Source Web Scraping & Data Consolidation Pipeline

[![Python Version](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/)
[![Testing](https://img.shields.io/badge/pytest-passing-brightgreen.svg)](https://pytest.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

An interview-ready, production-grade Python web scraping and data engineering pipeline that extracts, cleans, validates, deduplicates, and consolidates data from multiple heterogenous web sources:
- **Books to Scrape** ([https://books.toscrape.com/](https://books.toscrape.com/))
- **Quotes to Scrape** ([https://quotes.toscrape.com/](https://quotes.toscrape.com/))

The pipeline strictly adheres to modern data engineering best practices: **Scraping → Cleaning → Validation → Deduplication → Consolidation → Output**.

---

## Table of Contents
1. [Project Overview](#project-overview)
2. [Objective](#objective)
3. [Features](#features)
4. [Technology Stack](#technology-stack)
5. [Project Structure](#project-structure)
6. [Python Version & Prerequisites](#python-version--prerequisites)
7. [Installation & Setup](#installation--setup)
8. [How to Run](#how-to-run)
9. [How Pagination Works](#how-pagination-works)
10. [Books Scraper Explanation](#books-scraper-explanation)
11. [Quotes Scraper Explanation](#quotes-scraper-explanation)
12. [Standardized Data Model](#standardized-data-model)
13. [Cleaning Approach](#cleaning-approach)
14. [Validation Approach](#validation-approach)
15. [Deduplication Approach](#deduplication-approach)
16. [Error Handling & Resilience](#error-handling--resilience)
17. [Logging System](#logging-system)
18. [Output Files](#output-files)
19. [Testing](#testing)
20. [Assumptions](#assumptions)
21. [Known Limitations](#known-limitations)
22. [AI Usage Summary](#ai-usage-summary)
23. [Production Roadmap & Scaling](#possible-production-improvements)

---

## Project Overview
Real-world data ingestion pipelines frequently interact with diverse external sources lacking APIs. This repository demonstrates how to architect a modular, maintainable, and resilient scraping workflow without relying on bloated browser automation tools (such as Selenium or Playwright) when lightweight HTTP requests and DOM parsing are sufficient.

The design decouples source-specific ingestion logic from generic downstream data processing, guaranteeing that new sources can be plugged in seamlessly.

---

## Objective
- Ingest 1,000 book records across 50 catalog pages from **Books to Scrape**.
- Ingest 100 quote records across 10 catalog pages from **Quotes to Scrape**.
- Map both disparate domains into a unified, standardized schema without inventing data.
- Enforce strict cleaning, domain-aware integrity checks, and composite deduplication.
- Generate an audit-ready dataset (`output/final_dataset.csv`) and an operational JSON metrics summary (`output/summary_report.json`).

---

## Features
- **Dynamic DOM-Driven Pagination**: Follows next-page links dynamically using `urllib.parse.urljoin` without hardcoding page numbers or counts.
- **Session Re-use & Polite Rate Limiting**: Employs `requests.Session()` with realistic browser headers, configurable timeouts, and polite request delays.
- **Fault-Tolerant Exponential Backoff**: Retries transient network glitches (1s, 2s, 4s) up to 3 attempts, failing gracefully without halting the pipeline.
- **Fault Isolation**: If one target source experiences an outage, subsequent sources continue extraction uninterrupted.
- **Standardized Schema**: Common `ScrapedRecord` dataclass cleanly representing both literary products and quotations with accurate nullability.
- **Robust Cleaning**: Regex currency parsing, word-to-integer rating normalization (`"Three"` → `3`), typographic Unicode cleanup, and tag list normalization.
- **Measurable Validation**: Validates HTTP URLs, source whitelisting, non-empty identifiers, and numeric bounds, sequestering invalid rows.
- **Smart Composite Deduplication**: Normalizes case, outer punctuation, and whitespace to prevent false negatives.
- **Comprehensive Pytest Suite**: 21 deterministic unit tests executing against mocked records in < 0.5s.

---

## Technology Stack
- **Python 3.11+** (Tested on Python 3.14.2)
- **`requests`**: HTTP request orchestration and session management.
- **`beautifulsoup4`**: Fast HTML DOM traversal and tag parsing.
- **`lxml`**: High-performance underlying XML/HTML parser.
- **`pandas`**: Structured DataFrame manipulation and clean UTF-8 CSV persistence.
- **`python-dateutil`**: Robust ISO timestamp parsing and date handling.
- **`pytest`**: Automated unit testing.
- **Standard Library Modules**: `dataclasses`, `logging`, `json`, `csv`, `time`, `re`, `urllib.parse`, `typing`, `pathlib`, `argparse`.

---

## Project Structure
```text
scraping_assignment/
│
├── scrapers/
│   ├── __init__.py            # Package exports
│   ├── books_scraper.py       # Books to Scrape crawler (50 pages)
│   └── quotes_scraper.py      # Quotes to Scrape crawler (10 pages)
│
├── processing/
│   ├── __init__.py            # Package exports
│   ├── cleaning.py            # Text, currency, rating & URL cleaners
│   ├── validation.py          # Schema validation & error classification
│   └── deduplication.py       # Domain-specific composite key deduplication
│
├── models/
│   ├── __init__.py            # Package exports
│   └── data_model.py          # Standardized ScrapedRecord dataclass
│
├── output/
│   ├── final_dataset.csv      # Consolidated cleaned CSV (1,100 records)
│   └── summary_report.json    # Exact audit metrics & telemetry
│
├── logs/
│   └── scraper.log            # Execution log file (DEBUG & INFO levels)
│
├── tests/
│   ├── __init__.py            # Package exports
│   ├── test_cleaning.py       # Unit tests for normalization functions
│   ├── test_validation.py     # Unit tests for validation integrity
│   └── test_deduplication.py  # Unit tests for duplicate detection
│
├── main.py                    # Orchestrator & CLI entrypoint
├── requirements.txt           # Minimal pinned dependencies
├── README.md                  # Comprehensive documentation
├── AI_USAGE.md                # Engineering transparency and AI usage log
└── .gitignore                 # Standard Python ignores (preserves outputs)
```

---

## Python Version & Prerequisites
- Python **3.11 or higher** is required (uses modern type union syntax `int | None` and standard library improvements).
- Ensure `pip` is updated:
  ```bash
  python -m pip install --upgrade pip
  ```

---

## Installation & Setup

### 1. Clone or Navigate to the Repository
```bash
cd scraping_assignment
```

### 2. Create and Activate a Virtual Environment
**On Windows (PowerShell / Command Prompt):**
```powershell
python -m venv .venv
.venv\Scripts\activate
```

**On Linux / macOS:**
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

---

## How to Run

### Run the Complete Pipeline (Default Full Run)
Traverses all 50 pages of Books to Scrape and all 10 pages of Quotes to Scrape:
```bash
python main.py
```

### Run a Fast Demo Run (Restricting Pages)
Useful for rapid interview demonstrations or integration checks:
```bash
python main.py --books-max-pages 2 --quotes-max-pages 2
```

### Launch Interactive Localhost Dashboard
To explore the ingested dataset, view live metrics, and inspect logs in an interactive web UI:
```bash
python server.py
```
Then open your web browser at:
- **Local Dashboard**: [http://localhost:8000](http://localhost:8000) or [http://127.0.0.1:8000](http://127.0.0.1:8000)
- **Interactive Swagger REST API Docs**: [http://localhost:8000/docs](http://localhost:8000/docs)

### CLI Arguments Available
- `--books-max-pages <N>`: Maximum catalogue pages to crawl from Books to Scrape (default: `None` = all).
- `--quotes-max-pages <N>`: Maximum pages to crawl from Quotes to Scrape (default: `None` = all).
- `--scrape-details`: Visit each book detail page for deeper descriptions and category tags (default: `False`).
- `--delay <seconds>`: Polite sleep delay between consecutive HTTP requests (default: `0.2`).

---

## How Pagination Works

Both target websites present traditional HTML link-based pagination rather than client-rendered infinite scrolling.

### The Relative URL Trap & `urljoin` Resolution
A common beginner mistake is hardcoding `https://books.toscrape.com/catalogue/page-{N}.html`. In our scrapers:
1. On page 1 (`https://books.toscrape.com/`), the next link is `catalogue/page-2.html`.
2. On page 2 (`https://books.toscrape.com/catalogue/page-2.html`), the next link is `page-3.html`.
3. If one naively appends `https://books.toscrape.com/` + `page-3.html`, a `404 Not Found` occurs.

By using `urllib.parse.urljoin(current_page_url, next_href)`, Python correctly resolves relative links against the base URL:
```python
next_tag = soup.select_one("li.next a")
if next_tag and next_tag.get("href"):
    current_url = urljoin(current_url, next_tag["href"])
else:
    current_url = None  # Natural termination
```
Pagination terminates naturally when `<li class="next"><a ...>` is not present in the DOM (on page 50 of Books and page 10 of Quotes).

---

## Books Scraper Explanation (`scrapers/books_scraper.py`)
- **Target URL**: `https://books.toscrape.com/`
- **Container Selector**: `article.product_pod`
- **Fields Extracted**:
  - `name_or_title`: Extracted from `h3 a['title']` (avoids truncated visible text).
  - `price`: Extracted from `.price_color` (e.g., `"£51.77"`).
  - `availability`: Extracted from `.availability`.
  - `rating`: Extracted from `p.star-rating['class']` (mapped `"Three"` → `3`).
  - `source_url`: Normalized absolute URL resolved via `urljoin(current_url, h3 a['href'])`.
  - `category` & `description`: Available on individual book detail pages (`#product_description + p`). Traversed when `--scrape-details` is enabled; otherwise cleanly populated as `None` to prevent polite scraping from stalling over 1,000 sequential page fetches.

---

## Quotes Scraper Explanation (`scrapers/quotes_scraper.py`)
- **Target URL**: `https://quotes.toscrape.com/`
- **Container Selector**: `div.quote`
- **Fields Extracted**:
  - `name_or_title`: Extracted from `span.text`.
  - `author`: Extracted from `small.author`.
  - `tags`: Extracted from `div.tags a.tag`, joined as clean comma-separated values.
  - `source_url`: Preserved current page URL where the quote was encountered.
  - `scraped_at`: ISO 8601 UTC timestamp.
  - `category`, `price`, `rating`: Appropriately set to `None`.

---

## Standardized Data Model (`models/data_model.py`)

A single `ScrapedRecord` dataclass maps records from both domains cleanly:

| Column | Type | Books to Scrape | Quotes to Scrape |
| :--- | :--- | :--- | :--- |
| `source` | `str` | `"Books to Scrape"` | `"Quotes to Scrape"` |
| `source_url` | `str` | Book Product URL | Quote Page URL |
| `name_or_title` | `str` | Book Title | Quote Text |
| `category` | `str` / `None` | Genre (if details scraped) | `None` |
| `price` | `float` / `None`| Numeric Price (e.g. `51.77`)| `None` |
| `rating` | `int` / `None` | 1 to 5 integer | `None` |
| `author` | `str` / `None` | `None` | Author Name |
| `tags` | `str` / `None` | `None` | Comma-separated tags |
| `description` | `str` / `None` | Product description | `None` |
| `scraped_at` | `str` | UTC ISO Timestamp | UTC ISO Timestamp |

---

## Cleaning Approach (`processing/cleaning.py`)
1. **Typographic Normalization**: Replaces curly quotes (`\u201c`, `\u201d`, `\u2018`, `\u2019`), em-dashes, and non-breaking spaces (`\xa0`) with standard ASCII equivalents.
2. **Whitespace Normalization**: Collapses multiple contiguous spaces, tabs, and newlines into single spaces using `re.sub(r"\s+", " ", text).strip()`.
3. **Price Parsing**: Uses regex `r"(\d+(?:\.\d+)?)"` to extract numeric float representations from currency symbols (`"£51.77"` → `51.77`).
4. **Rating Mapping**: Converts case-insensitive word ratings (`"One"` through `"Five"`) into integers `1` through `5`.
5. **Sentinel Normalization**: Converts `""`, `"N/A"`, `"null"`, `"none"`, `"nan"` into Python `None`.
6. **URL Normalization**: Strips URL fragments (`#section`), trims outer whitespace, and verifies scheme and netloc.

---

## Validation Approach (`processing/validation.py`)
Records must satisfy five core integrity assertions before entering the consolidated dataset:
1. **Source Integrity**: `source` must exist and match one of `{"Books to Scrape", "Quotes to Scrape"}`.
2. **URL Validity**: `source_url` must be a valid `http://` or `https://` URL containing a host domain.
3. **Identifier Presence**: `name_or_title` must be a non-empty string.
4. **Price Constraints**: If present, `price` must be numeric and non-negative (`>= 0`).
5. **Rating Constraints**: If present, `rating` must be an integer between 1 and 5.

Invalid records are diverted into a `ValidationResult.invalid_records` audit log with specific rejection reasons, ensuring the pipeline never crashes on a single malformed row.

---

## Deduplication Approach (`processing/deduplication.py`)

Raw exact string matching fails when minor formatting differences occur across pages (e.g., differing capitalization, outer punctuation, or trailing slashes in URLs).

### Composite Fingerprint Strategy
- **Books**:
  $$\text{Key} = \text{norm}(source) + \text{"::"} + \text{norm}(title) + \text{"::"} + \text{norm\_url}(source\_url)$$
  *Rationale*: Protects against collision between different books or editions with identical titles, while detecting identical catalogue items.
- **Quotes**:
  $$\text{Key} = \text{norm}(source) + \text{"::"} + \text{norm}(quote\_text) + \text{"::"} + \text{norm}(author)$$
  *Rationale*: Detects when the same quote appears across multiple tag pages or pagination sets.

All keys are generated after lowercasing, whitespace collapsing, and stripping outer quotation marks.

---

## Error Handling & Resilience
- **HTTP Sessions**: Reuses TCP connections via `requests.Session()` with keep-alive.
- **Exponential Backoff**:
  - Attempt 1: Immediate.
  - Attempt 2: Wait 1 second on `Timeout` or `ConnectionError`.
  - Attempt 3: Wait 2 seconds.
  - Attempt 4: Wait 4 seconds.
- **Non-Retriable Statuses**: HTTP 4xx errors are logged immediately without futile retries.
- **Source Isolation**: Scraping Books and Quotes are wrapped in separate `try/except` blocks. If one domain is unreachable, the remaining source still completes.

---

## Logging System (`logs/scraper.log`)
Uses standard Python `logging` with dual handlers:
- **File Handler**: Writes persistent logs to `logs/scraper.log`.
- **Console Stream Handler**: Outputs formatted operational progress to `sys.stdout`.
- Format: `[YYYY-MM-DD HH:MM:SS] [LEVEL] [LOGGER_NAME]: Message`.

---

## Output Files

### 1. `output/final_dataset.csv`
- Exactly 10 columns in canonical order: `source`, `source_url`, `name_or_title`, `category`, `price`, `rating`, `author`, `tags`, `description`, `scraped_at`.
- Clean UTF-8 encoding without index column (`index=False`).
- Contains **1,100 records** (1,000 Books + 100 Quotes) on a full run.

### 2. `output/summary_report.json`
Actual operational metrics recorded from live execution:
```json
{
  "execution_time_seconds": 64.57,
  "sources": {
    "Books to Scrape": {
      "pages_attempted": 50,
      "records_collected": 1000,
      "records_after_cleaning": 1000,
      "records_rejected": 0,
      "duplicates_detected": 0
    },
    "Quotes to Scrape": {
      "pages_attempted": 10,
      "records_collected": 100,
      "records_after_cleaning": 100,
      "records_rejected": 0,
      "duplicates_detected": 0
    }
  },
  "total_records_collected": 1100,
  "total_records_after_cleaning": 1100,
  "total_records_rejected": 0,
  "total_duplicates": 0,
  "final_record_count": 1100,
  "failed_pages": []
}
```

---

## Testing

Execute the test suite with `pytest`:
```bash
pytest
```

Verbose test output:
```bash
pytest -v
```

### Test Coverage Summary:
- **`tests/test_cleaning.py`**: Validates text cleaning, typographic normalization, whitespace collapsing, missing sentinel replacement, URL fragment stripping, currency parsing, rating conversion, and tag deduplication.
- **`tests/test_validation.py`**: Validates schema compliance, rejects invalid sources, malformed URLs, missing titles, negative prices, and out-of-bounds ratings.
- **`tests/test_deduplication.py`**: Validates book fingerprint keys, quote author fingerprints, case/whitespace insensitivity, and verifies that distinct items are never falsely flagged.

All unit tests run deterministically against local mock objects without making external network calls.

---

## Assumptions
1. Target websites follow standard static HTML rendering without requiring JavaScript hydration.
2. The catalogue structure of Books to Scrape and Quotes to Scrape terminates when the `li.next` element is absent.
3. In Quotes to Scrape, `name_or_title` stores the quote body because quotes do not possess separate titles.

---

## Known Limitations
1. **Sequential Execution**: Pages are scraped sequentially with polite pauses. While fast enough for 60 pages (~64s), crawling 100,000 pages would require asynchronous requests (`aiohttp` / `asyncio`) or distributed queues.
2. **Detail Page Traversal**: Books catalogue listings do not contain full descriptions; fetching all 1,000 detail pages sequentially would require ~45 minutes. Detail traversal is supported as an opt-in CLI flag (`--scrape-details`).
3. **Static Scraping**: Cannot parse Single Page Applications (SPAs) rendered exclusively with client-side JavaScript (e.g. React/Vue without SSR).

---

## AI Usage Summary
Per transparent engineering disclosure guidelines, AI assistance (Gemini 3.8 Flash / DeepMind agentic tools) was used for scaffold generation, test boundary planning, and documentation drafting. All code was verified against live target endpoints, reviewed, and refined. See [AI_USAGE.md](AI_USAGE.md) for full details.

---

## Possible Production Improvements
To transition this pipeline into an enterprise-scale scraping infrastructure:
1. **Distributed Task Queue**: Use **Celery** or **RabbitMQ** with **Redis** to dispatch page scraping tasks across worker pools.
2. **Asynchronous HTTP**: Adopt `aiohttp` or `httpx` with `asyncio` for non-blocking concurrent I/O.
3. **Persistent Database**: Replace flat CSV with **PostgreSQL** (relational tables with index on composite hash) or **MongoDB** (document storage).
4. **Workflow Orchestration**: Schedule scheduled pipeline DAGs via **Apache Airflow** or **Prefect**.
5. **Proxy Rotation & WAF Handling**: Integrate proxy rotation (e.g., Bright Data, ScraperAPI) and header rotation to avoid IP blacklisting.
6. **Data Quality Monitoring**: Integrate **Great Expectations** or **Soda Core** to generate automated data quality scorecards.
7. **Containerization**: Package the scraper with **Docker** and deploy to Kubernetes / AWS ECS.
