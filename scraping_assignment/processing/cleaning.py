"""Data cleaning utilities for web scraping pipelines."""

import re
from typing import Any, Iterable, List, Optional
from urllib.parse import urlparse, urlunparse

from models.data_model import ScrapedRecord

RATING_MAP = {
    "zero": 0,
    "one": 1,
    "two": 2,
    "three": 3,
    "four": 4,
    "five": 5,
}

MISSING_SENTINELS = {"", "none", "null", "n/a", "na", "nan", "nil", "undefined"}


def normalize_missing_value(val: Any) -> Optional[Any]:
    """Normalize sentinel missing representations ('', 'N/A', 'None', etc.) to Python None.

    Args:
        val: Any value to inspect.

    Returns:
        None if value is a known missing sentinel, otherwise original value.
    """
    if val is None:
        return None
    if isinstance(val, str):
        cleaned = val.strip().lower()
        if cleaned in MISSING_SENTINELS:
            return None
    return val


def normalize_whitespace(text: Optional[str]) -> Optional[str]:
    """Collapse consecutive whitespace characters and strip outer spaces.

    Args:
        text: Raw input string.

    Returns:
        Collapsed string or None if input is empty or None.
    """
    if text is None:
        return None
    # Replace non-breaking spaces and collapse all whitespace to single spaces
    text = text.replace("\xa0", " ")
    collapsed = re.sub(r"\s+", " ", text).strip()
    return collapsed if collapsed else None


def clean_text(text: Optional[str]) -> Optional[str]:
    """Thoroughly clean text by normalizing whitespace and handling curly/smart quotes.

    Args:
        text: Raw text string.

    Returns:
        Cleaned text string or None.
    """
    if text is None:
        return None

    # Replace common Unicode typographic characters with standard ASCII equivalents
    replacements = {
        "\u2018": "'",  # Left single quotation mark
        "\u2019": "'",  # Right single quotation mark
        "\u201c": '"',  # Left double quotation mark
        "\u201d": '"',  # Right double quotation mark
        "\u2014": " - ",  # Em dash
        "\u2013": " - ",  # En dash
        "\u2026": "...",  # Horizontal ellipsis
    }
    for char, repl in replacements.items():
        text = text.replace(char, repl)

    text = normalize_whitespace(text)
    return normalize_missing_value(text)


def normalize_url(url: Optional[str]) -> Optional[str]:
    """Normalize a URL by trimming whitespace, stripping fragments, and ensuring valid scheme/netloc.

    Args:
        url: Raw URL string.

    Returns:
        Normalized URL string, or None if invalid.
    """
    if not url or not isinstance(url, str):
        return None

    cleaned = url.strip()
    try:
        parsed = urlparse(cleaned)
        if not parsed.scheme or not parsed.netloc:
            return None
        # Reconstruct without fragment (#section) to canonicalize
        normalized = urlunparse((
            parsed.scheme.lower(),
            parsed.netloc.lower(),
            parsed.path,
            parsed.params,
            parsed.query,
            "",  # Remove fragment
        ))
        return normalized
    except Exception:
        return None


def parse_price(price_raw: Any) -> Optional[float]:
    """Extract a numeric float price from raw currency strings or numbers.

    Examples:
        '£51.77' -> 51.77
        '$19.99' -> 19.99
        '51.77'  -> 51.77
        None     -> None

    Args:
        price_raw: Raw price representation (str, int, float, etc.).

    Returns:
        Parsed float rounded to 2 decimal places, or None if missing or unparseable.
    """
    if price_raw is None:
        return None

    if isinstance(price_raw, (int, float)):
        val = float(price_raw)
        return round(val, 2) if val >= 0 else None

    if isinstance(price_raw, str):
        # Find first floating point or integer pattern
        match = re.search(r"(\d+(?:\.\d+)?)", price_raw)
        if match:
            try:
                val = float(match.group(1))
                return round(val, 2)
            except ValueError:
                return None

    return None


def normalize_rating(rating_raw: Any) -> Optional[int]:
    """Normalize rating representation into an integer between 1 and 5.

    Handles textual words ('One', 'Two', 'Three', 'Four', 'Five') as well as
    numeric values and digit strings.

    Args:
        rating_raw: Raw rating (e.g. 'Three', 3, '3', 3.0).

    Returns:
        Integer between 1 and 5, or None if unavailable/out of bounds.
    """
    if rating_raw is None:
        return None

    # Handle numeric inputs
    if isinstance(rating_raw, (int, float)):
        int_val = int(rating_raw)
        return int_val if 1 <= int_val <= 5 else None

    if isinstance(rating_raw, str):
        cleaned = rating_raw.strip().lower()

        # Check word-based mapping
        if cleaned in RATING_MAP:
            val = RATING_MAP[cleaned]
            return val if 1 <= val <= 5 else None

        # Check digit string
        if cleaned.isdigit():
            int_val = int(cleaned)
            return int_val if 1 <= int_val <= 5 else None

    return None


def normalize_tags(tags_raw: Any) -> Optional[str]:
    """Normalize tags into a clean, comma-separated string.

    Accepts an iterable of strings (e.g. ['books', 'reading']) or a delimited string.

    Args:
        tags_raw: List of tags or delimited string.

    Returns:
        Normalized comma-separated string (e.g. 'books, reading') or None if empty.
    """
    if tags_raw is None:
        return None

    tag_list: List[str] = []
    if isinstance(tags_raw, str):
        raw_split = tags_raw.split(",")
        tag_list = [t.strip().lower() for t in raw_split if t.strip()]
    elif isinstance(tags_raw, Iterable):
        for item in tags_raw:
            if isinstance(item, str) and item.strip():
                tag_list.append(item.strip().lower())

    if not tag_list:
        return None

    # Deduplicate while preserving order
    seen = set()
    unique_tags = []
    for tag in tag_list:
        if tag not in seen:
            seen.add(tag)
            unique_tags.append(tag)

    return ", ".join(unique_tags) if unique_tags else None


def clean_record(record: ScrapedRecord) -> ScrapedRecord:
    """Apply cleaning transformations to all fields of a ScrapedRecord.

    Returns:
        A new ScrapedRecord instance with standardized, cleaned values.
    """
    return ScrapedRecord(
        source=clean_text(record.source) or "",
        source_url=normalize_url(record.source_url) or record.source_url,
        name_or_title=clean_text(record.name_or_title) or "",
        category=clean_text(record.category),
        price=parse_price(record.price),
        rating=normalize_rating(record.rating),
        author=clean_text(record.author),
        tags=normalize_tags(record.tags),
        description=clean_text(record.description),
        scraped_at=record.scraped_at.strip() if record.scraped_at else "",
    )
