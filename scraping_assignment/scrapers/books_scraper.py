"""Books to Scrape crawler and parser."""

import logging
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from models.data_model import ScrapedRecord

logger = logging.getLogger(__name__)

# Mapping book rating CSS class names to integer values
RATING_MAP: Dict[str, int] = {
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}

DEFAULT_USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) "
    "Chrome/124.0.0.0 Safari/537.36"
)


class BooksScraper:
    """Scraper for https://books.toscrape.com/

    Features:
        - Session management with realistic User-Agent.
        - Automatic HTML pagination traversal using relative URL resolution.
        - Configurable rate limiting and retry backoff.
        - Graceful error handling for missing elements and network failures.
        - Metrics collection for operational summary.
    """

    SOURCE_NAME = "Books to Scrape"
    BASE_URL = "https://books.toscrape.com/"

    def __init__(
        self,
        base_url: str = BASE_URL,
        delay: float = 0.2,
        timeout: float = 15.0,
        max_retries: int = 3,
        user_agent: str = DEFAULT_USER_AGENT,
        scrape_details: bool = False,
    ) -> None:
        """Initialize the BooksScraper instance.

        Args:
            base_url: Starting entrypoint URL.
            delay: Polite sleep delay between consecutive HTTP requests (seconds).
            timeout: HTTP socket timeout in seconds.
            max_retries: Maximum attempts for transient network failures.
            user_agent: Custom User-Agent header string.
            scrape_details: Whether to visit each product page for category and description.
        """
        self.base_url = base_url
        self.delay = delay
        self.timeout = timeout
        self.max_retries = max_retries
        self.scrape_details = scrape_details

        self.session = requests.Session()
        self.session.headers.update({"User-Agent": user_agent})

        # Operational metrics tracking
        self.pages_attempted: int = 0
        self.records_collected: int = 0
        self.failed_pages: List[str] = []

    def _fetch_page(self, url: str) -> Optional[str]:
        """Fetch HTML content from a URL with retry logic and exponential backoff.

        Args:
            url: Absolute URL to retrieve.

        Returns:
            HTML text if successful, or None if all attempts failed.
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
                break  # Do not retry 4xx errors
            except requests.exceptions.RequestException as req_err:
                logger.error("Unexpected request error fetching %s: %s", url, req_err)
                break

        self.failed_pages.append(url)
        return None

    def _parse_product_pod(self, pod: Any, current_url: str) -> Optional[ScrapedRecord]:
        """Parse a single product pod element on a catalog page into a ScrapedRecord.

        Args:
            pod: BeautifulSoup Tag for <article class="product_pod">.
            current_url: URL of the page currently being parsed.

        Returns:
            Populated ScrapedRecord or None if pod is severely malformed.
        """
        try:
            # 1. Extract title and product URL
            title_tag = pod.select_one("h3 a")
            if not title_tag:
                logger.warning("Missing <h3><a> title tag in product pod at %s", current_url)
                return None

            title = title_tag.get("title") or title_tag.get_text(strip=True)
            rel_href = title_tag.get("href", "")
            product_url = urljoin(current_url, rel_href)

            # 2. Extract price
            price_tag = pod.select_one(".price_color")
            price_raw = price_tag.get_text(strip=True) if price_tag else None

            # 3. Extract availability
            avail_tag = pod.select_one(".availability")
            availability = avail_tag.get_text(strip=True) if avail_tag else None

            # 4. Extract rating class
            rating_tag = pod.select_one("p.star-rating")
            rating_val: Optional[int] = None
            if rating_tag:
                classes = [c.lower() for c in rating_tag.get("class", [])]
                for cls in classes:
                    if cls in RATING_MAP:
                        rating_val = RATING_MAP[cls]
                        break

            # 5. Optional details (category and description)
            category: Optional[str] = None
            description: Optional[str] = None

            if self.scrape_details and product_url:
                time.sleep(self.delay)
                detail_html = self._fetch_page(product_url)
                if detail_html:
                    category, description = self._parse_detail_page(detail_html)

            timestamp = datetime.now(timezone.utc).isoformat()

            return ScrapedRecord(
                source=self.SOURCE_NAME,
                source_url=product_url,
                name_or_title=title,
                category=category,
                price=price_raw,  # cleaned downstream by parse_price
                rating=rating_val,
                author=None,
                tags=None,
                description=description,
                scraped_at=timestamp,
            )

        except Exception as exc:
            logger.exception("Error extracting product pod from %s: %s", current_url, exc)
            return None

    def _parse_detail_page(self, html: str) -> tuple[Optional[str], Optional[str]]:
        """Extract category and description from a product detail page."""
        soup = BeautifulSoup(html, "html.parser")
        # Category from breadcrumb (Home > Books > CategoryName > Title)
        category: Optional[str] = None
        breadcrumb_links = soup.select("ul.breadcrumb li a")
        if len(breadcrumb_links) >= 3:
            category = breadcrumb_links[2].get_text(strip=True)

        # Description from #product_description + p
        description: Optional[str] = None
        desc_header = soup.select_one("#product_description")
        if desc_header:
            desc_p = desc_header.find_next_sibling("p")
            if desc_p:
                description = desc_p.get_text(strip=True)

        return (category, description)

    def scrape(self, max_pages: Optional[int] = None) -> List[ScrapedRecord]:
        """Execute pagination traversal and scrape book records.

        Args:
            max_pages: Optional maximum number of catalog pages to scrape.
                       If None, scrapes until pagination terminates.

        Returns:
            List of ScrapedRecord instances collected.
        """
        records: List[ScrapedRecord] = []
        current_url: Optional[str] = self.base_url
        page_num = 1

        logger.info("Starting BooksScraper traversal at %s", self.base_url)

        while current_url:
            if max_pages is not None and page_num > max_pages:
                logger.info("Reached configured max_pages limit (%d). Halting Books scraper.", max_pages)
                break

            self.pages_attempted += 1
            logger.info("Scraping Books page %d: %s", page_num, current_url)

            html = self._fetch_page(current_url)
            if not html:
                logger.warning("Skipping Books page %d due to fetch failure: %s", page_num, current_url)
                # If the catalog page fails, we cannot discover the next link; stop pagination
                break

            soup = BeautifulSoup(html, "html.parser")
            pods = soup.select("article.product_pod")
            logger.debug("Found %d product pods on Books page %d", len(pods), page_num)

            for pod in pods:
                record = self._parse_product_pod(pod, current_url)
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
                logger.info("No next page link found on Books page %d. Pagination complete.", page_num)
                current_url = None

        logger.info(
            "BooksScraper finished: %d records collected across %d pages attempted.",
            len(records),
            self.pages_attempted,
        )
        return records

    def close(self) -> None:
        """Close the underlying HTTP session."""
        self.session.close()
