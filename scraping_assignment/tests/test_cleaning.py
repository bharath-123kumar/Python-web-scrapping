"""Unit tests for data cleaning functions in processing/cleaning.py."""

import pytest

from models.data_model import ScrapedRecord
from processing.cleaning import (
    clean_record,
    clean_text,
    normalize_missing_value,
    normalize_rating,
    normalize_tags,
    normalize_url,
    normalize_whitespace,
    parse_price,
)


class TestCleaning:
    """Test suite for cleaning and normalization utilities."""

    def test_clean_text(self):
        # Typographic quotes and extra whitespace
        raw = "   \u201cThe secret of getting ahead is getting started.\u201d   "
        assert clean_text(raw) == '"The secret of getting ahead is getting started."'

        # Em dash and ellipses
        raw_dash = "Life \u2014 is \u2026 beautiful"
        assert clean_text(raw_dash) == 'Life - is ... beautiful'

        # Empty string and None handling
        assert clean_text("") is None
        assert clean_text("   ") is None
        assert clean_text(None) is None
        assert clean_text("N/A") is None

    def test_normalize_whitespace(self):
        assert normalize_whitespace("Hello   \n\t  World") == "Hello World"
        assert normalize_whitespace("   Only    spaces   ") == "Only spaces"
        assert normalize_whitespace("Non-breaking\xa0space") == "Non-breaking space"
        assert normalize_whitespace("") is None
        assert normalize_whitespace("     ") is None
        assert normalize_whitespace(None) is None

    def test_normalize_missing_value(self):
        assert normalize_missing_value("") is None
        assert normalize_missing_value("  ") is None
        assert normalize_missing_value("none") is None
        assert normalize_missing_value("None") is None
        assert normalize_missing_value("null") is None
        assert normalize_missing_value("N/A") is None
        assert normalize_missing_value("nan") is None
        assert normalize_missing_value("Valid String") == "Valid String"
        assert normalize_missing_value(42) == 42
        assert normalize_missing_value(0) == 0

    def test_normalize_url(self):
        # Valid URLs
        assert normalize_url("https://books.toscrape.com/index.html") == "https://books.toscrape.com/index.html"
        assert normalize_url("  http://example.com/page?id=1#section  ") == "http://example.com/page?id=1"
        assert normalize_url("HTTPS://Example.COM/PATH") == "https://example.com/PATH"

        # Invalid or missing URLs
        assert normalize_url("") is None
        assert normalize_url("not-a-url") is None
        assert normalize_url("ftp:///missing") is None
        assert normalize_url(None) is None

    def test_parse_price(self):
        # Currency strings
        assert parse_price("£51.77") == 51.77
        assert parse_price("$19.99") == 19.99
        assert parse_price("€ 100.50") == 100.50
        assert parse_price("51.77") == 51.77
        assert parse_price("Price: £0.99 (sale)") == 0.99

        # Numeric inputs
        assert parse_price(45.678) == 45.68
        assert parse_price(25) == 25.0

        # Edge cases and invalid
        assert parse_price(None) is None
        assert parse_price("") is None
        assert parse_price("Free") is None
        assert parse_price(-15.0) is None

    def test_normalize_rating(self):
        # Word-based ratings (case-insensitive)
        assert normalize_rating("One") == 1
        assert normalize_rating("two") == 2
        assert normalize_rating("THREE") == 3
        assert normalize_rating("Four") == 4
        assert normalize_rating("Five") == 5

        # Numeric representations
        assert normalize_rating(1) == 1
        assert normalize_rating(5) == 5
        assert normalize_rating("4") == 4
        assert normalize_rating(3.0) == 3

        # Invalid ratings
        assert normalize_rating("Zero") == None
        assert normalize_rating("Six") is None
        assert normalize_rating(0) is None
        assert normalize_rating(6) is None
        assert normalize_rating(-1) is None
        assert normalize_rating("Not a rating") is None
        assert normalize_rating(None) is None

    def test_normalize_tags(self):
        # List of tags
        assert normalize_tags(["books", "reading", "  LIFE  "]) == "books, reading, life"
        # Deduplication in tags while preserving order
        assert normalize_tags(["love", "life", "love"]) == "love, life"
        # Comma-separated string
        assert normalize_tags("humor, quotes , inspirational") == "humor, quotes, inspirational"
        # Empty inputs
        assert normalize_tags([]) is None
        assert normalize_tags("") is None
        assert normalize_tags(None) is None

    def test_clean_record(self):
        raw = ScrapedRecord(
            source="  Books to Scrape  ",
            source_url="https://books.toscrape.com/catalogue/book_1/index.html#comments",
            name_or_title="  A Light in the   Attic  ",
            category="  Poetry  ",
            price="£51.77",
            rating="Three",
            author="  N/A  ",
            tags=["poetry", "classic"],
            description="  Some description  ",
            scraped_at=" 2026-10-06T12:00:00Z ",
        )
        cleaned = clean_record(raw)
        assert cleaned.source == "Books to Scrape"
        assert cleaned.source_url == "https://books.toscrape.com/catalogue/book_1/index.html"
        assert cleaned.name_or_title == "A Light in the Attic"
        assert cleaned.category == "Poetry"
        assert cleaned.price == 51.77
        assert cleaned.rating == 3
        assert cleaned.author is None  # 'N/A' normalized to None
        assert cleaned.tags == "poetry, classic"
        assert cleaned.description == "Some description"
        assert cleaned.scraped_at == "2026-10-06T12:00:00Z"
