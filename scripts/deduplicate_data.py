"""Duplicate detection and record deduplication workflow.

This module is adapted for the Course Conversion Analytics Dashboard.
It detects exact duplicates, identifies near duplicates using course
conversion business keys, removes duplicate records with auditable rules,
and writes processed output files for downstream analytics.

Usage:
    python scripts/deduplicate_data.py
"""
from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple

import numpy as np
import pandas as pd


ROOT_DIR = Path(__file__).resolve().parents[1]
RAW_FILE = ROOT_DIR / "data" / "raw" / "data_with_duplicates.csv"
PROCESSED_FILE = ROOT_DIR / "data" / "processed" / "deduplicated_data.csv"
OUTPUT_DIR = ROOT_DIR / "output"
LOG_DIR = ROOT_DIR / "logs"
AUDIT_FILE = OUTPUT_DIR / "removed_duplicates_audit.csv"
AUDIT_SUMMARY_FILE = OUTPUT_DIR / "dedup_audit_summary.json"
SUMMARY_FILE = OUTPUT_DIR / "dedup_summary.json"

TIMESTAMP_COLUMNS = ("search_time", "preview_time", "enrollment_date")

NEAR_DUPLICATE_KEYS: Dict[str, List[str]] = {
    "course": ["course_id"],
    "search": ["user_id", "search_query"],
    "preview": ["user_id", "course_id"],
    "enrollment": ["user_id", "course_id"],
}


def configure_logging() -> logging.Logger:
    """Configure console and file logging for the deduplication workflow."""
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    logger = logging.getLogger("deduplicate_data")
    logger.setLevel(logging.INFO)
    logger.handlers.clear()

    formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    file_handler = logging.FileHandler(LOG_DIR / "deduplicate_data.log", encoding="utf-8")
    file_handler.setFormatter(formatter)

    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger


logger = configure_logging()


def current_timestamp() -> str:
    """Return an ISO 8601 UTC timestamp for audit files."""
    return datetime.now(timezone.utc).isoformat()


def load_dataset(file_path: Path = RAW_FILE) -> pd.DataFrame:
    """Load the duplicate sample dataset.

    Args:
        file_path: CSV path containing course conversion records.

    Returns:
        Loaded DataFrame with empty strings converted to missing values.

    Raises:
        FileNotFoundError: If the source file does not exist.
        ValueError: If the dataset is empty.
    """
    if not file_path.exists():
        raise FileNotFoundError(f"Input file not found: {file_path}")

    df = pd.read_csv(file_path, dtype=str, keep_default_na=True)
    df = df.replace(r"^\s*$", np.nan, regex=True)

    if df.empty:
        raise ValueError("Input dataset is empty; deduplication cannot continue.")

    logger.info("Loaded %s rows from %s", len(df), file_path)
    return df


def detect_exact_duplicates(df: pd.DataFrame) -> Tuple[int, pd.DataFrame]:
    """Detect rows where every column value is identical.

    Args:
        df: Input DataFrame.

    Returns:
        Tuple containing the number of duplicate rows and duplicate rows.
    """
    duplicate_mask = df.duplicated(keep="first")
    duplicates = df.loc[duplicate_mask].copy()
    number_of_duplicates = int(duplicate_mask.sum())

    print("\n===== Exact Duplicate Detection Report =====")
    print(f"Rows scanned: {len(df)}")
    print(f"Exact duplicate rows found: {number_of_duplicates}")

    if duplicates.empty:
        print("No exact duplicate rows were found.")
    else:
        print("\nDuplicate rows:")
        print(duplicates.to_string(index=False))

    logger.info("Detected %s exact duplicate rows", number_of_duplicates)
    return number_of_duplicates, duplicates


def detect_near_duplicates(df: pd.DataFrame, key_columns: Iterable[str]) -> pd.DataFrame:
    """Detect duplicate records using a business-key column set.

    Near duplicates are records that refer to the same logical business
    event but may differ in completeness, timestamps, or non-key details.

    Args:
        df: Input DataFrame.
        key_columns: Columns that define the duplicate business key.

    Returns:
        DataFrame containing all records that belong to duplicate key groups.
    """
    keys = list(key_columns)
    missing_keys = [column for column in keys if column not in df.columns]
    if missing_keys:
        raise KeyError(f"Missing key columns for near duplicate detection: {missing_keys}")

    duplicate_mask = df.duplicated(subset=keys, keep=False)
    duplicates = df.loc[duplicate_mask].copy()

    print("\n===== Near Duplicate Detection Report =====")
    print(f"Business key columns: {', '.join(keys)}")
    print(f"Near duplicate rows found: {len(duplicates)}")

    if duplicates.empty:
        print("No near duplicate business-key groups were found.")
    else:
        group_count = int(duplicates.groupby(keys, dropna=False).ngroups)
        print(f"Duplicate business-key groups found: {group_count}")
        print("\nSample duplicate groups:")
        print(duplicates.head(12).to_string(index=False))

    logger.info("Detected %s near duplicate rows using keys %s", len(duplicates), keys)
    return duplicates


def detect_near_duplicates_by_dataset(df: pd.DataFrame) -> pd.DataFrame:
    """Detect near duplicates across all supported dataset types."""
    duplicate_frames: List[pd.DataFrame] = []

    print("\n===== Dataset-Level Near Duplicate Scan =====")
    for dataset_name, keys in NEAR_DUPLICATE_KEYS.items():
        subset = df.loc[df["dataset_name"] == dataset_name].copy()
        if subset.empty:
            continue

        dataset_duplicates = detect_near_duplicates(subset, keys)
        if not dataset_duplicates.empty:
            dataset_duplicates["near_duplicate_rule"] = f"{dataset_name}: {', '.join(keys)}"
            duplicate_frames.append(dataset_duplicates)

    if not duplicate_frames:
        return pd.DataFrame(columns=list(df.columns) + ["near_duplicate_rule"])

    return pd.concat(duplicate_frames, ignore_index=True)


def remove_exact_duplicates(
    df: pd.DataFrame, keep: object = "first"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Remove exact duplicate records.

    Args:
        df: Input DataFrame.
        keep: Duplicate retention rule accepted by pandas: "first", "last", or False.

    Returns:
        Tuple of cleaned DataFrame and removed records.
    """
    if keep not in {"first", "last", False}:
        raise ValueError("keep must be one of: 'first', 'last', False")

    rows_before = len(df)
    removed_mask = df.duplicated(keep=keep)
    removed = df.loc[removed_mask].copy()
    cleaned = df.drop_duplicates(keep=keep).copy()
    rows_after = len(cleaned)
    rows_removed = rows_before - rows_after
    removal_percentage = (rows_removed / rows_before * 100) if rows_before else 0.0

    print("\n===== Exact Duplicate Removal Report =====")
    print(f"Keep strategy: {keep}")
    print(f"Rows before: {rows_before}")
    print(f"Rows after: {rows_after}")
    print(f"Rows removed: {rows_removed}")
    print(f"Removal percentage: {removal_percentage:.2f}%")

    if not removed.empty:
        removed["deduplication_reason"] = "Exact duplicate: every column matched"
        removed["deduplication_strategy"] = f"exact_keep_{keep}"

    logger.info("Removed %s exact duplicate rows", rows_removed)
    return cleaned, removed


def _timestamp_column_for_dataset(dataset_name: str, columns: Iterable[str]) -> Optional[str]:
    """Select the best timestamp column for a dataset."""
    dataset_timestamp_map = {
        "search": "search_time",
        "preview": "preview_time",
        "enrollment": "enrollment_date",
    }
    preferred = dataset_timestamp_map.get(dataset_name)
    if preferred in columns:
        return preferred

    for column in TIMESTAMP_COLUMNS:
        if column in columns:
            return column
    return None


def _select_most_complete_group_record(
    group: pd.DataFrame, dataset_name: str
) -> Tuple[int, pd.DataFrame]:
    """Return the retained index and removed records for one near-duplicate group."""
    scored = group.copy()
    scored["_completeness_score"] = scored.notna().sum(axis=1)

    timestamp_column = _timestamp_column_for_dataset(dataset_name, scored.columns)
    if timestamp_column:
        scored["_event_timestamp"] = pd.to_datetime(
            scored[timestamp_column], errors="coerce"
        )
    else:
        scored["_event_timestamp"] = pd.NaT

    scored = scored.sort_values(
        by=["_completeness_score", "_event_timestamp"],
        ascending=[False, False],
        kind="mergesort",
    )

    keep_index = int(scored.index[0])
    removed = group.drop(index=keep_index).copy()
    return keep_index, removed


def remove_near_duplicates(
    df: pd.DataFrame,
    key_columns: Iterable[str],
    keep_strategy: str = "most_complete",
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Remove near duplicates using business-key grouping.

    Business reasoning for `most_complete`: the retained record should have
    the strongest analytical value. The workflow keeps the row with the
    fewest missing values because complete records preserve more course,
    learner, and funnel context. If records are equally complete, the newest
    event timestamp is retained because it usually reflects the latest state
    of the learner interaction or enrollment.

    Args:
        df: Input DataFrame for a single logical dataset.
        key_columns: Columns that define a near-duplicate business key.
        keep_strategy: One of "most_complete", "first", or "last".

    Returns:
        Tuple of cleaned DataFrame and removed near-duplicate records.
    """
    if keep_strategy not in {"most_complete", "first", "last"}:
        raise ValueError("keep_strategy must be one of: most_complete, first, last")

    keys = list(key_columns)
    if df.empty:
        return df.copy(), df.copy()

    dataset_name = str(df["dataset_name"].dropna().iloc[0]) if "dataset_name" in df else ""
    duplicate_mask = df.duplicated(subset=keys, keep=False)

    if keep_strategy in {"first", "last"}:
        removed_mask = df.duplicated(subset=keys, keep=keep_strategy)
        removed = df.loc[removed_mask].copy()
        cleaned = df.drop_duplicates(subset=keys, keep=keep_strategy).copy()
    else:
        keep_indexes: List[int] = []
        removed_frames: List[pd.DataFrame] = []

        duplicate_groups = df.loc[duplicate_mask].groupby(keys, dropna=False, sort=False)
        for _, group in duplicate_groups:
            keep_index, removed_group = _select_most_complete_group_record(
                group, dataset_name
            )
            keep_indexes.append(keep_index)
            removed_frames.append(removed_group)

        non_duplicate = df.loc[~duplicate_mask].copy()
        retained_duplicates = df.loc[keep_indexes].copy() if keep_indexes else df.head(0)
        cleaned = pd.concat([non_duplicate, retained_duplicates], ignore_index=False)
        cleaned = cleaned.sort_index().copy()
        removed = (
            pd.concat(removed_frames, ignore_index=False)
            if removed_frames
            else df.head(0).copy()
        )

    if not removed.empty:
        removed["deduplication_reason"] = (
            "Near duplicate: same business key; kept most complete/latest record"
        )
        removed["deduplication_strategy"] = f"near_{keep_strategy}"

    print("\n===== Near Duplicate Removal Report =====")
    print(f"Dataset: {dataset_name or 'unspecified'}")
    print(f"Business key columns: {', '.join(keys)}")
    print(f"Keep strategy: {keep_strategy}")
    print(f"Rows before: {len(df)}")
    print(f"Rows after: {len(cleaned)}")
    print(f"Rows removed: {len(removed)}")

    logger.info(
        "Removed %s near duplicates for dataset %s using %s",
        len(removed),
        dataset_name,
        keep_strategy,
    )
    return cleaned, removed


def remove_near_duplicates_by_dataset(
    df: pd.DataFrame, keep_strategy: str = "most_complete"
) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Apply near-duplicate removal separately to each dataset_name."""
    cleaned_frames: List[pd.DataFrame] = []
    removed_frames: List[pd.DataFrame] = []

    for dataset_name, subset in df.groupby("dataset_name", dropna=False, sort=False):
        dataset_label = str(dataset_name)
        keys = NEAR_DUPLICATE_KEYS.get(dataset_label)

        if not keys:
            cleaned_frames.append(subset.copy())
            continue

        cleaned_subset, removed_subset = remove_near_duplicates(
            subset.copy(), keys, keep_strategy=keep_strategy
        )
        cleaned_frames.append(cleaned_subset)
        if not removed_subset.empty:
            removed_frames.append(removed_subset)

    cleaned = pd.concat(cleaned_frames, ignore_index=True) if cleaned_frames else df.copy()
    removed = (
        pd.concat(removed_frames, ignore_index=True)
        if removed_frames
        else pd.DataFrame(columns=list(df.columns))
    )
    return cleaned, removed


def log_removed_duplicates(
    removed_records: pd.DataFrame,
    dataset_name: str,
    deduplication_strategy: str,
    reason: str,
    audit_file: Path = AUDIT_FILE,
    summary_file: Path = AUDIT_SUMMARY_FILE,
) -> Dict[str, object]:
    """Save removed duplicate records and write an audit summary.

    Args:
        removed_records: DataFrame containing removed duplicate records.
        dataset_name: Dataset or workflow name.
        deduplication_strategy: Strategy used to remove records.
        reason: Business reason for removal.
        audit_file: CSV destination for removed records.
        summary_file: JSON destination for audit metadata.

    Returns:
        Audit metadata dictionary.
    """
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    audit_df = removed_records.copy()
    audit_df["audit_timestamp"] = current_timestamp()
    audit_df["dataset_name_audited"] = dataset_name
    audit_df["audit_reason"] = reason

    audit_df.to_csv(audit_file, index=False)

    summary = {
        "timestamp": current_timestamp(),
        "records_removed": int(len(removed_records)),
        "reason": reason,
        "dataset_name": dataset_name,
        "deduplication_strategy": deduplication_strategy,
        "audit_file_location": str(audit_file),
    }

    with summary_file.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    print("\n===== Removed Duplicate Audit =====")
    print(f"Records removed: {summary['records_removed']}")
    print(f"Audit CSV: {audit_file}")
    print(f"Audit summary JSON: {summary_file}")

    logger.info("Saved duplicate audit files to %s and %s", audit_file, summary_file)
    return summary


def compare_before_after(
    before_df: pd.DataFrame,
    after_df: pd.DataFrame,
    duplicate_records_removed: int,
    summary_file: Path = SUMMARY_FILE,
) -> Dict[str, object]:
    """Generate a before-and-after deduplication summary.

    Args:
        before_df: Original dataset before duplicate removal.
        after_df: Dataset after duplicate removal.
        duplicate_records_removed: Count of duplicate records removed.
        summary_file: JSON destination for summary.

    Returns:
        Summary metadata dictionary.
    """
    rows_before = int(len(before_df))
    rows_after = int(len(after_df))
    rows_removed = rows_before - rows_after
    removal_percentage = (rows_removed / rows_before * 100) if rows_before else 0.0

    summary = {
        "rows_before": rows_before,
        "rows_after": rows_after,
        "rows_removed": rows_removed,
        "removal_percentage": round(removal_percentage, 2),
        "nulls_before": int(before_df.isna().sum().sum()),
        "nulls_after": int(after_df.isna().sum().sum()),
        "duplicate_records_removed": int(duplicate_records_removed),
        "timestamp": current_timestamp(),
    }

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    with summary_file.open("w", encoding="utf-8") as file:
        json.dump(summary, file, indent=4)

    print("\n===== Before vs After Deduplication Summary =====")
    print(f"Rows before: {summary['rows_before']}")
    print(f"Rows after: {summary['rows_after']}")
    print(f"Rows removed: {summary['rows_removed']}")
    print(f"Removal percentage: {summary['removal_percentage']:.2f}%")
    print(f"Null values before: {summary['nulls_before']}")
    print(f"Null values after: {summary['nulls_after']}")
    print(f"Duplicate records removed: {summary['duplicate_records_removed']}")
    print(f"Summary JSON: {summary_file}")

    logger.info("Saved before/after summary to %s", summary_file)
    return summary


def save_processed_dataset(df: pd.DataFrame, file_path: Path = PROCESSED_FILE) -> None:
    """Save the deduplicated dataset for downstream analytics."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(file_path, index=False)
    logger.info("Saved deduplicated dataset to %s", file_path)


def run_deduplication_workflow() -> pd.DataFrame:
    """Run the complete duplicate detection and deduplication workflow."""
    original_df = load_dataset()

    detect_exact_duplicates(original_df)
    detect_near_duplicates_by_dataset(original_df)

    exact_cleaned_df, exact_removed_df = remove_exact_duplicates(
        original_df, keep="first"
    )

    near_cleaned_df, near_removed_df = remove_near_duplicates_by_dataset(
        exact_cleaned_df, keep_strategy="most_complete"
    )

    removed_records = pd.concat(
        [exact_removed_df, near_removed_df], ignore_index=True, sort=False
    )

    log_removed_duplicates(
        removed_records=removed_records,
        dataset_name="course_conversion_analytics",
        deduplication_strategy="exact_keep_first_then_near_most_complete",
        reason=(
            "Removed exact duplicates and near duplicates to preserve one "
            "trusted record per learner-course business event."
        ),
    )

    compare_before_after(
        before_df=original_df,
        after_df=near_cleaned_df,
        duplicate_records_removed=len(removed_records),
    )

    save_processed_dataset(near_cleaned_df)
    print("\nDeduplication completed successfully.")
    return near_cleaned_df


def main() -> None:
    """Entry point for command-line execution."""
    try:
        run_deduplication_workflow()
    except Exception as exc:
        logger.exception("Deduplication workflow failed: %s", exc)
        raise


if __name__ == "__main__":
    main()
