"""Main execution entrypoint for Multi-Source Web Scraping & Data Consolidation Pipeline."""

import argparse
import json
import logging
import sys
import time
from pathlib import Path
from typing import Any, Dict, List

import pandas as pd

# Ensure package imports resolve reliably regardless of invocation working directory
CURRENT_DIR = Path(__file__).resolve().parent
if str(CURRENT_DIR) not in sys.path:
    sys.path.insert(0, str(CURRENT_DIR))

from models.data_model import ScrapedRecord
from processing.cleaning import clean_record
from processing.deduplication import deduplicate_records
from processing.validation import validate_records
from scrapers.books_scraper import BooksScraper
from scrapers.quotes_scraper import QuotesScraper


def configure_logging(log_file: Path, debug: bool = False) -> logging.Logger:
    """Set up structured logging with simultaneous console and rotating/file handlers."""
    log_file.parent.mkdir(parents=True, exist_ok=True)

    level = logging.DEBUG if debug else logging.INFO
    formatter = logging.Formatter(
        "[%(asctime)s] [%(levelname)s] [%(name)s]: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    root_logger = logging.getLogger()
    root_logger.setLevel(level)

    # Clear existing handlers to prevent duplicate outputs
    root_logger.handlers.clear()

    # File handler (logs/scraper.log)
    file_handler = logging.FileHandler(str(log_file), mode="w", encoding="utf-8")
    file_handler.setFormatter(formatter)
    file_handler.setLevel(level)
    root_logger.addHandler(file_handler)

    # Console stdout handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    console_handler.setLevel(level)
    root_logger.addHandler(console_handler)

    return logging.getLogger("pipeline")


def run_pipeline(
    books_max_pages: int | None = None,
    quotes_max_pages: int | None = None,
    scrape_details: bool = False,
    delay: float = 0.2,
    output_dir: Path | None = None,
    logs_dir: Path | None = None,
) -> Dict[str, Any]:
    """Execute the end-to-end multi-source web scraping and consolidation pipeline."""
    start_time = time.time()

    base_dir = CURRENT_DIR
    output_path = output_dir or (base_dir / "output")
    logs_path = logs_dir or (base_dir / "logs")

    output_path.mkdir(parents=True, exist_ok=True)
    logs_path.mkdir(parents=True, exist_ok=True)

    logger = configure_logging(logs_path / "scraper.log")
    logger.info("=" * 60)
    logger.info("STARTING MULTI-SOURCE WEB SCRAPING & CONSOLIDATION PIPELINE")
    logger.info("=" * 60)

    # Tracking metrics per source
    sources_metrics: Dict[str, Dict[str, Any]] = {
        "Books to Scrape": {
            "pages_attempted": 0,
            "records_collected": 0,
            "records_after_cleaning": 0,
            "records_rejected": 0,
            "duplicates_detected": 0,
        },
        "Quotes to Scrape": {
            "pages_attempted": 0,
            "records_collected": 0,
            "records_after_cleaning": 0,
            "records_rejected": 0,
            "duplicates_detected": 0,
        },
    }
    failed_pages: List[str] = []

    # ---------------------------------------------------------
    # STAGE 1: SCRAPING (ISOLATED EXECUTION)
    # ---------------------------------------------------------
    books_records: List[ScrapedRecord] = []
    logger.info("--- Stage 1A: Scraping Books to Scrape ---")
    try:
        books_scraper = BooksScraper(delay=delay, scrape_details=scrape_details)
        books_records = books_scraper.scrape(max_pages=books_max_pages)
        sources_metrics["Books to Scrape"]["pages_attempted"] = books_scraper.pages_attempted
        sources_metrics["Books to Scrape"]["records_collected"] = len(books_records)
        failed_pages.extend(books_scraper.failed_pages)
        books_scraper.close()
    except Exception as exc:
        logger.exception("Critical unexpected error scraping Books to Scrape: %s", exc)

    quotes_records: List[ScrapedRecord] = []
    logger.info("--- Stage 1B: Scraping Quotes to Scrape ---")
    try:
        quotes_scraper = QuotesScraper(delay=delay)
        quotes_records = quotes_scraper.scrape(max_pages=quotes_max_pages)
        sources_metrics["Quotes to Scrape"]["pages_attempted"] = quotes_scraper.pages_attempted
        sources_metrics["Quotes to Scrape"]["records_collected"] = len(quotes_records)
        failed_pages.extend(quotes_scraper.failed_pages)
        quotes_scraper.close()
    except Exception as exc:
        logger.exception("Critical unexpected error scraping Quotes to Scrape: %s", exc)

    # ---------------------------------------------------------
    # STAGE 2: CLEANING
    # ---------------------------------------------------------
    logger.info("--- Stage 2: Data Cleaning & Normalization ---")
    cleaned_books = [clean_record(rec) for rec in books_records]
    cleaned_quotes = [clean_record(rec) for rec in quotes_records]

    sources_metrics["Books to Scrape"]["records_after_cleaning"] = len(cleaned_books)
    sources_metrics["Quotes to Scrape"]["records_after_cleaning"] = len(cleaned_quotes)

    # ---------------------------------------------------------
    # STAGE 3: VALIDATION
    # ---------------------------------------------------------
    logger.info("--- Stage 3: Integrity Validation ---")
    val_books = validate_records(cleaned_books)
    val_quotes = validate_records(cleaned_quotes)

    sources_metrics["Books to Scrape"]["records_rejected"] = val_books.total_invalid
    sources_metrics["Quotes to Scrape"]["records_rejected"] = val_quotes.total_invalid

    logger.info(
        "Books validation: %d valid, %d rejected",
        val_books.total_valid,
        val_books.total_invalid,
    )
    logger.info(
        "Quotes validation: %d valid, %d rejected",
        val_quotes.total_valid,
        val_quotes.total_invalid,
    )

    # ---------------------------------------------------------
    # STAGE 4: DEDUPLICATION
    # ---------------------------------------------------------
    logger.info("--- Stage 4: Deduplication ---")
    unique_books, dupes_books, count_dupes_books = deduplicate_records(val_books.valid_records)
    unique_quotes, dupes_quotes, count_dupes_quotes = deduplicate_records(val_quotes.valid_records)

    sources_metrics["Books to Scrape"]["duplicates_detected"] = count_dupes_books
    sources_metrics["Quotes to Scrape"]["duplicates_detected"] = count_dupes_quotes

    logger.info(
        "Books deduplication: %d unique, %d duplicates removed",
        len(unique_books),
        count_dupes_books,
    )
    logger.info(
        "Quotes deduplication: %d unique, %d duplicates removed",
        len(unique_quotes),
        count_dupes_quotes,
    )

    # ---------------------------------------------------------
    # STAGE 5: CONSOLIDATION & EXPORT
    # ---------------------------------------------------------
    logger.info("--- Stage 5: Consolidation & Output Generation ---")
    final_records: List[ScrapedRecord] = unique_books + unique_quotes

    # Generate CSV with Pandas
    csv_file = output_path / "final_dataset.csv"
    if final_records:
        records_dicts = [r.to_dict() for r in final_records]
        df = pd.DataFrame(records_dicts)
    else:
        # Create empty DataFrame with prescribed columns
        df = pd.DataFrame(columns=list(ScrapedRecord.COLUMN_ORDER))

    # Reindex columns to guarantee canonical ordering
    df = df.reindex(columns=list(ScrapedRecord.COLUMN_ORDER))
    df.to_csv(csv_file, index=False, encoding="utf-8")
    logger.info("Saved final dataset to %s (%d rows)", csv_file, len(df))

    # ---------------------------------------------------------
    # STAGE 6: SUMMARY METRICS REPORT
    # ---------------------------------------------------------
    execution_time = round(time.time() - start_time, 2)
    total_collected = len(books_records) + len(quotes_records)
    total_cleaned = len(cleaned_books) + len(cleaned_quotes)
    total_rejected = val_books.total_invalid + val_quotes.total_invalid
    total_dupes = count_dupes_books + count_dupes_quotes
    final_count = len(final_records)

    summary_report: Dict[str, Any] = {
        "execution_time_seconds": execution_time,
        "sources": sources_metrics,
        "total_records_collected": total_collected,
        "total_records_after_cleaning": total_cleaned,
        "total_records_rejected": total_rejected,
        "total_duplicates": total_dupes,
        "final_record_count": final_count,
        "failed_pages": failed_pages,
    }

    summary_file = output_path / "summary_report.json"
    with open(summary_file, "w", encoding="utf-8") as f:
        json.dump(summary_report, f, indent=2)
    logger.info("Saved summary report to %s", summary_file)

    # ---------------------------------------------------------
    # CONSOLE METRICS DISPLAY
    # ---------------------------------------------------------
    print("\n" + "=" * 60)
    print("PIPELINE EXECUTION SUMMARY")
    print("=" * 60)
    print(f"Total Execution Time: {execution_time} seconds")
    print(f"Total Records Collected: {total_collected}")
    print(f"Total Records Cleaned:   {total_cleaned}")
    print(f"Total Records Rejected:  {total_rejected}")
    print(f"Total Duplicates:        {total_dupes}")
    print(f"Final Consolidated Rows: {final_count}")
    print("-" * 60)
    for source_name, metrics in sources_metrics.items():
        print(f"[{source_name}]")
        print(f"  Pages Attempted:    {metrics['pages_attempted']}")
        print(f"  Collected:          {metrics['records_collected']}")
        print(f"  After Cleaning:     {metrics['records_after_cleaning']}")
        print(f"  Rejected:           {metrics['records_rejected']}")
        print(f"  Duplicates:         {metrics['duplicates_detected']}")
    if failed_pages:
        print(f"Failed Pages ({len(failed_pages)}): {failed_pages}")
    else:
        print("Failed Pages: None (100% network success)")
    print("=" * 60 + "\n")

    logger.info("Pipeline execution completed successfully.")
    return summary_report


def main() -> None:
    """CLI parsing and pipeline trigger."""
    parser = argparse.ArgumentParser(
        description="Multi-Source Web Scraping & Data Consolidation Pipeline"
    )
    parser.add_argument(
        "--books-max-pages",
        type=int,
        default=None,
        help="Maximum pages to scrape from Books to Scrape (default: None, scrape all pages)",
    )
    parser.add_argument(
        "--quotes-max-pages",
        type=int,
        default=None,
        help="Maximum pages to scrape from Quotes to Scrape (default: None, scrape all pages)",
    )
    parser.add_argument(
        "--scrape-details",
        action="store_true",
        default=False,
        help="Visit each book detail page for category & description (slower)",
    )
    parser.add_argument(
        "--delay",
        type=float,
        default=0.2,
        help="Polite delay between consecutive requests in seconds (default: 0.2)",
    )

    args = parser.parse_args()

    try:
        run_pipeline(
            books_max_pages=args.books_max_pages,
            quotes_max_pages=args.quotes_max_pages,
            scrape_details=args.scrape_details,
            delay=args.delay,
        )
    except KeyboardInterrupt:
        print("\nPipeline interrupted by user.")
        sys.exit(1)
    except Exception as exc:
        print(f"\nFatal pipeline failure: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
