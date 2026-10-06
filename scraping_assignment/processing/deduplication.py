"""Deduplication logic utilizing source-specific normalized composite fingerprint keys."""

import logging
import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

from models.data_model import ScrapedRecord

logger = logging.getLogger(__name__)


@dataclass
class DeduplicationResult:
    """Outcome of deduplication execution."""

    unique_records: List[ScrapedRecord] = field(default_factory=list)
    duplicate_records: List[ScrapedRecord] = field(default_factory=list)

    @property
    def duplicate_count(self) -> int:
        return len(self.duplicate_records)

    @property
    def unique_count(self) -> int:
        return len(self.unique_records)


def _normalize_string_for_key(text: Optional[str]) -> str:
    """Normalize a string specifically for duplicate key generation.

    Applies:
        1. Stripping leading/trailing spaces.
        2. Lowercasing.
        3. Collapsing multiple spaces.
        4. Stripping enclosing quotation marks and minor punctuation noise.
    """
    if not text:
        return ""
    # Lowercase and normalize whitespace
    cleaned = re.sub(r"\s+", " ", text.lower()).strip()
    # Remove leading/trailing common quotation marks and trailing periods
    cleaned = cleaned.strip("\"'“”’‘.,;:!?")
    return cleaned


def _normalize_url_for_key(url: Optional[str]) -> str:
    """Normalize URL by lowercasing scheme/domain and stripping trailing slashes."""
    if not url:
        return ""
    cleaned = url.strip().lower()
    # Strip trailing slash to equate '/path' and '/path/'
    return cleaned.rstrip("/")


def generate_dedup_key(record: ScrapedRecord) -> str:
    """Generate a canonical composite deduplication key based on record source.

    Strategies:
        - Books to Scrape:
            Composite of normalized (source + title + source_url).
            Guarantees that book editions or same-titled books with distinct product
            URLs are preserved, while identical listings are flagged.
        - Quotes to Scrape:
            Composite of normalized (source + quote_text + author).
            Guarantees that the exact same quote by the same author appearing across
            multiple pages or tags is detected as a duplicate.
        - Fallback:
            Composite of normalized (source + name_or_title + source_url).
    """
    norm_source = _normalize_string_for_key(record.source)

    if record.source == "Books to Scrape":
        norm_title = _normalize_string_for_key(record.name_or_title)
        norm_url = _normalize_url_for_key(record.source_url)
        return f"{norm_source}::{norm_title}::{norm_url}"

    if record.source == "Quotes to Scrape":
        norm_text = _normalize_string_for_key(record.name_or_title)
        norm_author = _normalize_string_for_key(record.author or "")
        return f"{norm_source}::{norm_text}::{norm_author}"

    # Generic fallback
    norm_name = _normalize_string_for_key(record.name_or_title)
    norm_url = _normalize_url_for_key(record.source_url)
    return f"{norm_source}::{norm_name}::{norm_url}"


def deduplicate_records(
    records: Iterable[ScrapedRecord],
) -> Tuple[List[ScrapedRecord], List[ScrapedRecord], int]:
    """Identify and separate duplicate records using normalized domain keys.

    Args:
        records: Iterable of ScrapedRecord instances.

    Returns:
        Tuple containing:
            1. unique_records (list of first-seen ScrapedRecord instances)
            2. duplicate_records (list of redundant ScrapedRecord instances)
            3. duplicate_count (integer count of duplicates removed)
    """
    seen_keys: Set[str] = set()
    unique_records: List[ScrapedRecord] = []
    duplicate_records: List[ScrapedRecord] = []

    for record in records:
        key = generate_dedup_key(record)
        if key in seen_keys:
            duplicate_records.append(record)
            logger.info(
                "Duplicate detected for source '%s' with key: %s",
                record.source,
                key,
            )
        else:
            seen_keys.add(key)
            unique_records.append(record)

    return (unique_records, duplicate_records, len(duplicate_records))
