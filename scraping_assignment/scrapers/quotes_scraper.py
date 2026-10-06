"""Quotes to Scrape crawler and parser."""

import logging
import time
from datetime import datetime, timezone
from typing import Any, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from models.data_model import ScrapedRecord

logger = logging.getLogger(__name__)

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class QuotesScraper:
    """Scraper for https://quotes.toscrape.com/

    Features:
        - Session reuse with realistic User-Agent.
        - Automatic next-page link detection from HTML.
        - Resilient error handling with exponential backoff on network failures.
        - Extraction of quote text, author, and comma-separated tags.
        - Detailed metrics logging.
    """

    SOURCE_NAME = "Quotes to Scrape"
    BASE_URL = "https://quotes.toscrape.com/"

    def __init__(
        self,
        base_url: str = BASE_URL,
        delay: float = 0.2,
        timeout: float = 15.0,
        max_retries: int = 3,
        user_agent: str = DEFAULT_USER_AGENT,
    ) -> None:
        """Initialize QuotesScraper instance.

        Args:
            base_url: Starting entrypoint URL.
            delay: Polite delay between requests in seconds.
            timeout: HTTP socket timeout in seconds.
            max_retries: Maximum attempts for transient network errors.
            user_agent: Custom User-Agent header string.
        """
        self.base_url = base_url
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

        # Operational metrics tracking
        self.pages_attempted: int = 0
        self.records_collected: int = 0
        self.failed_pages: List[str] = []

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from a URL with retry logic and exponential backoff.

        Args:
            url: Absolute URL to fetch.

        Returns:
            HTML text if successful, or None if retries were exhausted.
        """
        for attempt in range(1, self.max_retries + 1):
            try:
                logger.debug("Requesting %s (attempt %d/%d)", url, attempt, self.max_retries)
                response = self.session.get(url, timeout=self.timeout)
                response.raise_for_status()
                return response.text
            except (requests.exceptions.Timeout, requests.exceptions.ConnectionError) as net_err:
                wait_time = 2 ** (attempt - 1)  # 1s, 2s, 4s
                logger.warning(
                    "Network error fetching %s on attempt %d/%d: %s. Retrying in %ds...",
                    url,
                    attempt,
                    self.max_retries,
                    net_err,
                    wait_time,
                )
                time.sleep(wait_time)
            except requests.exceptions.HTTPError as http_err:
                logger.error("HTTP error fetching %s: %s", url, http_err)
                break
            except requests.exceptions.RequestException as req_err:
                logger.error("Unexpected request error fetching %s: %s", url, req_err)
                break

        self.failed_pages.append(url)
        return None

    def _parse_quote_element(self, quote_div: Any, current_url: str) -> Optional[ScrapedRecord]:
        """Parse a single quote container element into a ScrapedRecord.

        Args:
            quote_div: BeautifulSoup Tag for <div class="quote">.
            current_url: URL of the page where the quote is hosted.

        Returns:
            Populated ScrapedRecord or None if quote text is missing.
        """
        try:
            # 1. Quote text
            text_tag = quote_div.select_one("span.text")
            if not text_tag:
                logger.warning("Missing span.text in quote block on %s", current_url)
                return None
            quote_text = text_tag.get_text(strip=True)

            # 2. Author
            author_tag = quote_div.select_one("small.author")
            author = author_tag.get_text(strip=True) if author_tag else None

            # 3. Tags
            tag_elements = quote_div.select("div.tags a.tag")
            tags_list = [t.get_text(strip=True) for t in tag_elements if t.get_text(strip=True)]
            tags_str = ", ".join(tags_list) if tags_list else None

            timestamp = datetime.now(timezone.utc).isoformat()

            return ScrapedRecord(
                source=self.SOURCE_NAME,
                source_url=current_url,
                name_or_title=quote_text,
                category=None,
                price=None,
                rating=None,
                author=author,
                tags=tags_str,
                description=None,
                scraped_at=timestamp,
            )

        except Exception as exc:
            logger.exception("Error extracting quote on %s: %s", current_url, exc)
            return None

    def scrape(self, max_pages: Optional[int] = None) -> List[ScrapedRecord]:
        """Execute pagination traversal and scrape quote records.

        Args:
            max_pages: Optional maximum number of pages to scrape.
                       If None, scrapes until pagination terminates.

        Returns:
            List of ScrapedRecord instances collected.
        """
        records: List[ScrapedRecord] = []
        current_url: Optional[str] = self.base_url
        page_num = 1

        logger.info("Starting QuotesScraper traversal at %s", self.base_url)

        while current_url:
            if max_pages is not None and page_num > max_pages:
                logger.info("Reached configured max_pages limit (%d). Halting Quotes scraper.", max_pages)
                break

            self.pages_attempted += 1
            logger.info("Scraping Quotes page %d: %s", page_num, current_url)

            html = self._fetch_page(current_url)
            if not html:
                logger.warning("Skipping Quotes page %d due to fetch failure: %s", page_num, current_url)
                break

            soup = BeautifulSoup(html, "html.parser")
            quote_divs = soup.select("div.quote")
            logger.debug("Found %d quote blocks on Quotes page %d", len(quote_divs), page_num)

            for quote_div in quote_divs:
                record = self._parse_quote_element(quote_div, current_url)
                if record:
                    records.append(record)
                    self.records_collected += 1

            # Discover next page link
            next_tag = soup.select_one("li.next a")
            if next_tag and next_tag.get("href"):
                next_rel_href = next_tag["href"]
                current_url = urljoin(current_url, next_rel_href)
                page_num += 1
                time.sleep(self.delay)
            else:
                logger.info("No next page link found on Quotes page %d. Pagination complete.", page_num)
                current_url = None

        logger.info(
            "QuotesScraper finished: %d records collected across %d pages attempted.",
            len(records),
            self.pages_attempted,
        )
        return records

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()
