"""Validation rules and reporting for scraped records."""

import logging
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple
from urllib.parse import urlparse

from models.data_model import ScrapedRecord

logger = logging.getLogger(__name__)

EXPECTED_SOURCES: Set[str] = {
    "Books to Scrape",
    "Quotes to Scrape",
}


@dataclass
class ValidationResult:
    """Encapsulates the outcome of validating a batch of records."""

    valid_records: List[ScrapedRecord] = field(default_factory=list)
    invalid_records: List[Tuple[ScrapedRecord, List[str]]] = field(default_factory=list)
    error_counts: Dict[str, int] = field(default_factory=dict)

    @property
    def total_inspected(self) -> int:
        return len(self.valid_records) + len(self.invalid_records)

    @property
    def total_valid(self) -> int:
        return len(self.valid_records)

    @property
    def total_invalid(self) -> int:
        return len(self.invalid_records)


def _is_valid_http_url(url: Optional[str]) -> bool:
    """Verify that a string is a well-formed HTTP/HTTPS URL with domain."""
    if not url or not isinstance(url, str):
        return False
    try:
        parsed = urlparse(url)
        return parsed.scheme.lower() in {"http", "https"} and bool(parsed.netloc)
    except Exception:
        return False


def validate_record(record: ScrapedRecord) -> Tuple[bool, List[str]]:
    """Validate a single ScrapedRecord against pipeline integrity rules.

    Rules enforced:
        1. source must exist and be in EXPECTED_SOURCES.
        2. source_url must exist and be a valid HTTP/HTTPS URL.
        3. name_or_title must exist and not be empty.
        4. price must be numeric and non-negative when present.
        5. rating must be an integer between 1 and 5 when present.

    Args:
        record: The ScrapedRecord to evaluate.

    Returns:
        Tuple of (is_valid: bool, error_messages: List[str]).
    """
    errors: List[str] = []

    # 1. Source existence and whitelist
    if not record.source:
        errors.append("Missing source: source field is empty or None")
    elif record.source not in EXPECTED_SOURCES:
        errors.append(f"Invalid source '{record.source}': must be one of {sorted(EXPECTED_SOURCES)}")

    # 2. Source URL format
    if not record.source_url:
        errors.append("Missing source_url: URL field is empty or None")
    elif not _is_valid_http_url(record.source_url):
        errors.append(f"Malformed source_url: '{record.source_url}' is not a valid HTTP/HTTPS URL")

    # 3. Name or Title presence
    if not record.name_or_title or not str(record.name_or_title).strip():
        errors.append("Missing name_or_title: title/quote content is required")

    # 4. Price numeric validity when present
    if record.price is not None:
        if not isinstance(record.price, (int, float)):
            errors.append(f"Invalid price '{record.price}': must be numeric")
        elif record.price < 0:
            errors.append(f"Invalid price '{record.price}': price cannot be negative")

    # 5. Rating range validity when present
    if record.rating is not None:
        if not isinstance(record.rating, int) or isinstance(record.rating, bool):
            errors.append(f"Invalid rating '{record.rating}': must be an integer")
        elif record.rating < 1 or record.rating > 5:
            errors.append(f"Invalid rating '{record.rating}': rating must be between 1 and 5")

    return (len(errors) == 0, errors)


def validate_records(records: Iterable[ScrapedRecord]) -> ValidationResult:
    """Validate a collection of records, categorizing valid and invalid items.

    Args:
        records: Iterable collection of ScrapedRecord instances.

    Returns:
        ValidationResult containing partitioned lists and error metrics.
    """
    result = ValidationResult()

    for idx, record in enumerate(records):
        is_valid, errors = validate_record(record)
        if is_valid:
            result.valid_records.append(record)
        else:
            result.invalid_records.append((record, errors))
            for err in errors:
                result.error_counts[err] = result.error_counts.get(err, 0) + 1
            logger.warning(
                "Validation rejected record #%d from source '%s': %s",
                idx,
                record.source,
                "; ".join(errors),
            )

    return result
