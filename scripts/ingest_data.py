"""Data ingestion utilities for Course Conversion Analytics Dashboard.

Provides CSV/JSON ingestion functions with robust error handling,
encoding/delimiter fallbacks, and dataset documentation utilities.

Usage: python scripts/ingest_data.py
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Iterable, Optional

import pandas as pd


# Configure module logger
logger = logging.getLogger("ingest")
logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
handler.setFormatter(formatter)
logger.addHandler(handler)


def ingest_csv(
    filepath: str,
    delimiter: str = ",",
    encoding: str = "utf-8",
    dtype_dict: Optional[Dict[str, object]] = None,
) -> pd.DataFrame:
    """Read a CSV file with explicit delimiter, encoding and dtypes.

    Prints a success message and basic dataset info on success. Handles
    common errors and re-raises unexpected exceptions.

    Args:
        filepath: Path to CSV file.
        delimiter: Field delimiter to use.
        encoding: File encoding.
        dtype_dict: Optional mapping of column dtypes for pandas.

    Returns:
        Loaded DataFrame.
    """
    path = Path(filepath)
    try:
        df = pd.read_csv(path, delimiter=delimiter, encoding=encoding, dtype=dtype_dict)
    except FileNotFoundError as exc:
        logger.error("File not found: %s", filepath)
        raise
    except UnicodeDecodeError as exc:
        logger.error("Encoding error for file %s: %s", filepath, exc)
        raise
    except Exception:
        logger.exception("Unexpected error reading CSV %s", filepath)
        raise

    print("✓ File Loaded")
    print(f"Number of rows: {df.shape[0]}")
    print(f"Number of columns: {df.shape[1]}")
    print(f"Column names: {list(df.columns)}")
    return df


def ingest_json(filepath: str, is_nested: bool = False) -> pd.DataFrame:
    """Load JSON data into a DataFrame.

    If `is_nested` is True, uses `pandas.json_normalize` to flatten nested records.
    """
    path = Path(filepath)
    try:
        with path.open("r", encoding="utf-8") as fh:
            raw = json.load(fh)
    except FileNotFoundError:
        logger.error("JSON file not found: %s", filepath)
        raise
    except json.JSONDecodeError:
        logger.error("Invalid JSON in file: %s", filepath)
        raise

    if is_nested:
        df = pd.json_normalize(raw)
    else:
        df = pd.DataFrame(raw)

    print(f"Loaded JSON: {filepath} -> shape={df.shape}")
    return df


def ingest_csv_with_fallback(
    filepath: str,
    delimiters: Optional[Iterable[str]] = None,
    encodings: Optional[Iterable[str]] = None,
    dtype_dict: Optional[Dict[str, object]] = None,
) -> pd.DataFrame:
    """Try multiple encoding and delimiter combinations until one succeeds.

    Returns the successfully loaded DataFrame or raises the last exception.
    """
    if delimiters is None:
        delimiters = [",", ";", "\t", "|"]
    if encodings is None:
        encodings = ["utf-8", "latin-1", "iso-8859-1", "cp1252"]

    last_exc: Optional[Exception] = None
    for enc in encodings:
        for delim in delimiters:
            try:
                logger.info("Trying encoding=%s delimiter=%r for %s", enc, delim, filepath)
                df = pd.read_csv(filepath, encoding=enc, delimiter=delim, dtype=dtype_dict)
                print("✓ File Loaded")
                print(f"Used encoding={enc} delimiter={repr(delim)}")
                print(f"Shape: {df.shape}")
                return df
            except (UnicodeDecodeError, pd.errors.ParserError, ValueError) as exc:
                last_exc = exc
                logger.debug("Attempt failed encoding=%s delim=%r: %s", enc, delim, exc)
                continue

    logger.error("All encodings/delimiters failed for %s", filepath)
    if last_exc is not None:
        raise last_exc
    raise RuntimeError("Failed to load CSV for unknown reasons")


def document_ingestion(df: pd.DataFrame, source_file: str) -> None:
    """Print a brief documentation summary for an ingested dataset.

    Includes shape, dtypes, missing value counts, first 3 rows, and memory usage.
    """
    print("\n=== Dataset Documentation ===")
    print(f"Dataset: {source_file}")
    print(f"Shape: {df.shape}")
    print("\nData types:")
    print(df.dtypes)
    print("\nMissing values per column:")
    print(df.isna().sum())
    print("\nFirst 3 rows:")
    print(df.head(3).to_string(index=False))
    mem = df.memory_usage(deep=True).sum()
    print(f"\nMemory usage: {mem} bytes")
    print("=== End Documentation ===\n")


def _ensure_processed_dir(base_dir: Path) -> Path:
    processed = base_dir / "data" / "processed"
    processed.mkdir(parents=True, exist_ok=True)
    return processed


def main() -> None:
    """Main ingestion routine for the Course Conversion Analytics Dashboard.

    Loads the project datasets from `data/raw/`, documents them, and writes
    processed copies to `data/processed/`.
    """
    base = Path(__file__).resolve().parents[1]
    raw_dir = base / "data" / "raw"
    processed_dir = _ensure_processed_dir(base)

    # File paths
    files = {
        "courses": raw_dir / "courses.csv",
        "search_logs": raw_dir / "search_logs.csv",
        "preview_logs": raw_dir / "preview_logs.csv",
        "enrollments": raw_dir / "enrollments.json",
    }

    try:
        courses = ingest_csv_with_fallback(files["courses"])
        document_ingestion(courses, str(files["courses"]))
        courses.to_csv(processed_dir / "courses.csv", index=False)

        search_logs = ingest_csv_with_fallback(files["search_logs"])  # small table
        document_ingestion(search_logs, str(files["search_logs"]))
        search_logs.to_csv(processed_dir / "search_logs.csv", index=False)

        preview_logs = ingest_csv_with_fallback(files["preview_logs"])  # small table
        document_ingestion(preview_logs, str(files["preview_logs"]))
        preview_logs.to_csv(processed_dir / "preview_logs.csv", index=False)

        enrollments = ingest_json(files["enrollments"])  # assume simple array of objects
        document_ingestion(enrollments, str(files["enrollments"]))
        enrollments.to_json(processed_dir / "enrollments.json", orient="records", date_format="iso")

    except Exception as exc:
        logger.exception("Ingestion failed: %s", exc)
        raise

    print("All datasets ingested and saved to data/processed/")


if __name__ == "__main__":
    main()
