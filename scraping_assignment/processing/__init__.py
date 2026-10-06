"""Processing package for data cleaning, validation, and deduplication."""

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
from processing.deduplication import deduplicate_records
from processing.validation import ValidationResult, validate_record, validate_records

__all__ = [
    "clean_record",
    "clean_text",
    "normalize_whitespace",
    "normalize_url",
    "parse_price",
    "normalize_rating",
    "normalize_missing_value",
    "normalize_tags",
    "validate_record",
    "validate_records",
    "ValidationResult",
    "deduplicate_records",
]
