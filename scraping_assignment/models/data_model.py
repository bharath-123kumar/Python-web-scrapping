"""Standardized data model for records scraped across multiple sources."""

from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional


@dataclass
class ScrapedRecord:
    """Standardized representation of a single scraped record.

    Attributes:
        source: Name of the origin website (e.g., 'Books to Scrape' or 'Quotes to Scrape').
        source_url: Canonical absolute URL where the item was scraped.
        name_or_title: Book title or quote text.
        category: Category/genre if available, otherwise None.
        price: Cleaned numeric price (e.g., 51.77) if available, otherwise None.
        rating: Integer rating from 1 to 5 if available, otherwise None.
        author: Author name if available (e.g. for quotes), otherwise None.
        tags: Comma-separated tag list if available, otherwise None.
        description: Textual description if available, otherwise None.
        scraped_at: ISO 8601 UTC timestamp string when the record was extracted.
    """

    source: str
    source_url: str
    name_or_title: str
    category: Optional[str] = None
    price: Optional[float] = None
    rating: Optional[int] = None
    author: Optional[str] = None
    tags: Optional[str] = None
    description: Optional[str] = None
    scraped_at: str = ""

    # Canonical order of columns for export
    COLUMN_ORDER: List[str] = (
        "source",
        "source_url",
        "name_or_title",
        "category",
        "price",
        "rating",
        "author",
        "tags",
        "description",
        "scraped_at",
    )

    def to_dict(self) -> Dict[str, Any]:
        """Convert the record to a dictionary ordered according to COLUMN_ORDER."""
        raw_dict = asdict(self)
        return {col: raw_dict.get(col) for col in self.COLUMN_ORDER}

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "ScrapedRecord":
        """Construct a ScrapedRecord instance from a dictionary."""
        valid_fields = {
            "source",
            "source_url",
            "name_or_title",
            "category",
            "price",
            "rating",
            "author",
            "tags",
            "description",
            "scraped_at",
        }
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)
