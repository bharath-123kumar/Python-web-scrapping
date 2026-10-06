"""Unit tests for validation logic in processing/validation.py."""

import pytest

from models.data_model import ScrapedRecord
from processing.validation import validate_record, validate_records


class TestValidation:
    """Test suite for record validation rules."""

    def test_validation_valid_book(self):
        rec = ScrapedRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/a-light-in-the-attic_1000/index.html",
            name_or_title="A Light in the Attic",
            category="Poetry",
            price=51.77,
            rating=3,
            author=None,
            tags=None,
            description="A poetry collection",
            scraped_at="2026-10-06T12:00:00Z",
        )
        is_valid, errors = validate_record(rec)
        assert is_valid is True
        assert len(errors) == 0

    def test_validation_valid_quote(self):
        rec = ScrapedRecord(
            source="Quotes to Scrape",
            source_url="https://quotes.toscrape.com/page/1/",
            name_or_title="The world as we have created it is a process of our thinking.",
            category=None,
            price=None,
            rating=None,
            author="Albert Einstein",
            tags="change, thinking, world",
            description=None,
            scraped_at="2026-10-06T12:00:00Z",
        )
        is_valid, errors = validate_record(rec)
        assert is_valid is True
        assert len(errors) == 0

    def test_validation_invalid_source(self):
        rec = ScrapedRecord(
            source="Unknown Random Source",
            source_url="https://example.com",
            name_or_title="Sample Title",
        )
        is_valid, errors = validate_record(rec)
        assert is_valid is False
        assert any("Invalid source" in e for e in errors)

    def test_validation_missing_source(self):
        rec = ScrapedRecord(
            source="",
            source_url="https://example.com",
            name_or_title="Sample Title",
        )
        is_valid, errors = validate_record(rec)
        assert is_valid is False
        assert any("Missing source" in e for e in errors)

    def test_validation_invalid_url(self):
        # Malformed URLs
        rec1 = ScrapedRecord(
            source="Books to Scrape",
            source_url="not-a-valid-url",
            name_or_title="Book Title",
        )
        is_valid1, errors1 = validate_record(rec1)
        assert is_valid1 is False
        assert any("Malformed source_url" in e for e in errors1)

        # Missing URL
        rec2 = ScrapedRecord(
            source="Books to Scrape",
            source_url="",
            name_or_title="Book Title",
        )
        is_valid2, errors2 = validate_record(rec2)
        assert is_valid2 is False
        assert any("Missing source_url" in e for e in errors2)

    def test_validation_missing_name_or_title(self):
        rec = ScrapedRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/test.html",
            name_or_title="   ",
        )
        is_valid, errors = validate_record(rec)
        assert is_valid is False
        assert any("Missing name_or_title" in e for e in errors)

    def test_validation_invalid_price(self):
        # Negative price
        rec1 = ScrapedRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/test.html",
            name_or_title="Book Title",
            price=-10.50,
        )
        is_valid1, errors1 = validate_record(rec1)
        assert is_valid1 is False
        assert any("price cannot be negative" in e for e in errors1)

        # Non-numeric price string that slipped past cleaning
        rec2 = ScrapedRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/test.html",
            name_or_title="Book Title",
            price="Fifty Dollars",  # type: ignore
        )
        is_valid2, errors2 = validate_record(rec2)
        assert is_valid2 is False
        assert any("must be numeric" in e for e in errors2)

    def test_validation_invalid_rating(self):
        # Rating out of range (> 5)
        rec1 = ScrapedRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/test.html",
            name_or_title="Book Title",
            rating=6,
        )
        is_valid1, errors1 = validate_record(rec1)
        assert is_valid1 is False
        assert any("rating must be between 1 and 5" in e for e in errors1)

        # Rating out of range (< 1)
        rec2 = ScrapedRecord(
            source="Books to Scrape",
            source_url="https://books.toscrape.com/catalogue/test.html",
            name_or_title="Book Title",
            rating=0,
        )
        is_valid2, errors2 = validate_record(rec2)
        assert is_valid2 is False
        assert any("rating must be between 1 and 5" in e for e in errors2)

    def test_validate_records_batch(self):
        records = [
            ScrapedRecord(
                source="Books to Scrape",
                source_url="https://books.toscrape.com/catalogue/b1.html",
                name_or_title="Valid Book 1",
                price=10.0,
                rating=4,
            ),
            ScrapedRecord(
                source="Invalid Source",
                source_url="https://books.toscrape.com/catalogue/b2.html",
                name_or_title="Invalid Book 2",
            ),
            ScrapedRecord(
                source="Quotes to Scrape",
                source_url="https://quotes.toscrape.com/page/1/",
                name_or_title="Valid Quote",
                author="Author",
            ),
            ScrapedRecord(
                source="Quotes to Scrape",
                source_url="",
                name_or_title="Invalid Quote Without URL",
            ),
        ]

        result = validate_records(records)
        assert result.total_inspected == 4
        assert result.total_valid == 2
        assert result.total_invalid == 2
        assert len(result.valid_records) == 2
        assert len(result.invalid_records) == 2
        assert len(result.error_counts) >= 2
