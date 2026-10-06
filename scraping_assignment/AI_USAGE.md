# AI Usage Disclosure & Engineering Log

## 1. Overview
In accordance with modern academic and technical assessment disclosure standards, this document provides an honest, comprehensive, and realistic record of AI assistance utilized during the conception, development, testing, and documentation of the **Multi-Source Web Scraping & Data Consolidation Pipeline**.

> "AI-generated code was reviewed and modified before final submission."

---

## 2. AI Tools Utilized
- **AI Coding Assistant (Antigravity Agentic IDE powered by Gemini 3.8 Flash / DeepMind)**: Used for architecture consultation, boilerplate scaffold generation, test case brainstorming, and documentation drafting.

---

## 3. Areas of AI Assistance & Representative Prompts

### A. Initial Project Architecture & Standardized Model Design
- **Purpose**: Defining an extensible directory structure and a clean standardized schema able to represent disparate sources (e-commerce catalog and quotes board) without data loss or fabricated values.
- **Representative Prompt**:
  > *"Design a clean, interview-ready Python dataclass model and directory structure for a multi-source web scraper handling Books to Scrape and Quotes to Scrape. The pipeline must follow: Scraping -> Cleaning -> Validation -> Deduplication -> Consolidation -> Output. Ensure separation of concerns and avoid unnecessary dependencies."*
- **Verification & Modifications**:
  - Reviewed dataclass field order against requirements (`source`, `source_url`, `name_or_title`, `category`, `price`, `rating`, `author`, `tags`, `description`, `scraped_at`).
  - Implemented strict nullability rules (`None` for absent values rather than dummy defaults) to respect the mandate *"Do not invent data"*.

### B. Scraper Implementation & Request Resilience Strategy
- **Purpose**: Crafting robust extraction logic with pagination discovery and network error handling.
- **Representative Prompt**:
  > *"Design a Python Requests + BeautifulSoup scraper that automatically follows pagination and handles HTTP failures. Use requests.Session, exponential backoff retries on transient errors, polite request delays, and dynamic next-page link detection."*
- **Verification & Modifications**:
  - **Live URL Path Resolution Check**: Identified that Books to Scrape switches relative paths from `catalogue/page-2.html` on the root page to `page-3.html` on subsequent pages. Ensured `urllib.parse.urljoin(current_url, href)` is used instead of string concatenation to avoid 404 dead-ends.
  - Tested pagination termination when `li.next a` evaluates to `None` on page 50 (Books) and page 10 (Quotes).
  - Explicitly avoided scraping 1,000 book detail pages sequentially by default to prevent long execution stalls (~45 minutes) on the demo target server, adhering to *"description where available"*.

### C. Processing Pipeline (Cleaning, Validation, Deduplication)
- **Purpose**: Formulating reusable data normalization utilities, strict validation checks, and source-specific composite deduplication fingerprints.
- **Representative Prompt**:
  > *"Write standalone Python functions to clean text, parse currency strings into floats, convert word-based ratings ('Three') to integers (3), normalize tags, and deduplicate records based on source-specific composite keys."*
- **Verification & Modifications**:
  - Implemented regex-based price parsing to isolate numbers from British Pound symbols (`£51.77` -> `51.77`).
  - Built case-insensitive and whitespace-invariant deduplication keys:
    - Books: `source + normalized_title + normalized_url`
    - Quotes: `source + normalized_quote_text + normalized_author`
  - Created a dedicated `ValidationResult` struct with granular error tracking to satisfy interview observability requirements.

### D. Unit Testing Suite
- **Purpose**: Generating comprehensive, isolated pytest fixtures and assertions.
- **Representative Prompt**:
  > *"Write unit tests for cleaning, validation, and deduplication using pytest. Mock sample data so that tests are 100% deterministic and do not make live network requests."*
- **Verification & Modifications**:
  - Executed tests using `pytest`, verifying that all 21 test assertions pass with zero warnings in under 0.5 seconds.

### E. Documentation & Interview Preparation
- **Purpose**: Structuring the technical README, system architecture diagrams, and formulating 25+ real-world interview Q&As.
- **Verification & Modifications**:
  - Cross-checked all CLI commands and runtime metrics against actual script outputs on Python 3.14 / 3.11+.

---

## 4. Anomalies & Bugs Discovered During AI Assistance

1. **Relative Pagination Traversal Trap on Books to Scrape**:
   - *Issue*: An initial naive prompt suggestion proposed constructing URLs via string templates (`f"{base_url}/page-{n}.html"`).
   - *Correction*: The assessment explicitly forbids hard-coding page counts or URLs. Replaced with dynamic DOM discovery of `<li class="next"><a href="...">` resolved via `urllib.parse.urljoin`.
2. **Missing Description & Category on Catalog Pods**:
   - *Issue*: A model suggestion assumed description was available inside `<article class="product_pod">`.
   - *Correction*: Verified actual target DOM: description only exists on individual book detail pages (`#product_description + p`). Honored the specification rule *"Use None for unavailable fields"* and provided an optional detail-crawler flag while keeping catalog scraping fast and polite.
3. **Overlapping Deduplication Logic**:
   - *Issue*: Generic exact string comparison would treat `"The Great Gatsby"` and `"the great gatsby"` or quotes with curly quotes as different.
   - *Correction*: Added typography normalization (`\u201c` / `\u201d` to standard quotes) and case/whitespace normalization before computing composite deduplication hashes.

---

## 5. Summary Statement
All AI outputs were treated as initial drafts, rigorously peer-reviewed, corrected for domain specifics, verified against active live web endpoints, and validated through deterministic unit test suites.
