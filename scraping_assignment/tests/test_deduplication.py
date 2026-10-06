"""Unit tests for duplicate detection logic in processing/deduplication.py."""

import pytest

from models.data_model import ScrapedRecord
from processing.deduplication import deduplicate_records, generate_dedup_key


class TestDeduplication:
    """Test suite for duplicate detection and key generation strategies."""

    def test_duplicate_detection_books(self):
        book1 = ScrapedRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            name_or_title="A Light in the Attic",
            price=51.77,
            rating=3,
        )
        # Duplicate with identical normalized title and URL
        book2 = ScrapedRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            name_or_title="A Light in the Attic",
            price=51.77,
            rating=3,
        )

        unique, duplicates, count = deduplicate_records([book1, book2])
        assert len(unique) == 1
        assert len(duplicates) == 1
        assert count == 1
        assert unique[0] is book1
        assert duplicates[0] is book2

    def test_duplicate_detection_quotes(self):
        quote1 = ScrapedRecord(
            source="Quotes to Scrape",
            source_url="https://quotes.toscrape.com/page/1/",
            name_or_title="The world as we have created it is a process of our thinking.",
            author="Albert Einstein",
        )
        # Same quote appearing on page 2 or another tag listing
        quote2 = ScrapedRecord(
            source="Quotes to Scrape",
            source_url="https://quotes.toscrape.com/tag/change/page/1/",
            name_or_title="The world as we have created it is a process of our thinking.",
            author="Albert Einstein",
        )

        unique, duplicates, count = deduplicate_records([quote1, quote2])
        assert len(unique) == 1
        assert len(duplicates) == 1
        assert count == 1
        assert unique[0] is quote1
        assert duplicates[0] is quote2

    def test_duplicate_detection_case_and_whitespace_insensitivity(self):
        # Different casing, punctuation, and inner whitespace
        book1 = ScrapedRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/book_1/index.html",
            name_or_title="The Great Gatsby",
        )
        book2 = ScrapedRecord(
            source="Books to Scrape",
            source_url="HTTPS://BOOKS.TOSCRAPE.COM/catalogue/book_1/index.html/",
            name_or_title='  "the   great   gatsby"  ',
        )

        key1 = generate_dedup_key(book1)
        key2 = generate_dedup_key(book2)
        assert key1 == key2

        unique, duplicates, count = deduplicate_records([book1, book2])
        assert len(unique) == 1
        assert count == 1

    def test_distinct_records_not_flagged(self):
        # Two books with same title but different product URLs
        book1 = ScrapedRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/edition_1/index.html",
            name_or_title="Hamlet",
        )
        book2 = ScrapedRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/edition_2/index.html",
            name_or_title="Hamlet",
        )

        unique, duplicates, count = deduplicate_records([book1, book2])
        assert len(unique) == 2
        assert len(duplicates) == 0
        assert count == 0

        # Two quotes with same text but different authors
        quote1 = ScrapedRecord(
            source="Quotes to Scrape",
            source_url="https://quotes.toscrape.com/page/1/",
            name_or_title="To be or not to be.",
            author="William Shakespeare",
        )
        quote2 = ScrapedRecord(
            source="Quotes to Scrape",
            source_url="https://quotes.toscrape.com/page/2/",
            name_or_title="To be or not to be.",
            author="Anonymous",
        )

        unique_q, duplicates_q, count_q = deduplicate_records([quote1, quote2])
        assert len(unique_q) == 2
        assert count_q == 0
