"""Missing value analysis and imputation utilities for Course Conversion Analytics Dashboard.

This module provides functions to analyze missingness, apply several
imputation strategies, document decisions, validate the results, and
save a cleaned dataset ready for downstream analytics.

Usage:
    python scripts/handle_missing.py
"""
from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Dict, Iterable, List, Tuple

import numpy as np
import pandas as pd


logger = logging.getLogger("handle_missing")
logger.setLevel(logging.INFO)
ch = logging.StreamHandler()
ch.setFormatter(logging.Formatter("%(asctime)s - %(levelname)s - %(message)s"))
logger.addHandler(ch)


def analyze_missing_values(df: pd.DataFrame) -> pd.DataFrame:
    """Generate a missing-value report for the given DataFrame.

    The returned DataFrame contains: column, dtype, null_count, null_pct,
    and business_meaning (a short description of the column's business role).

    Args:
        df: Input DataFrame.

    Returns:
        A DataFrame summarizing missingness and column metadata.
    """
    total = len(df)
    report_rows: List[Dict[str, object]] = []

    # Provide short business meanings for known columns
    business_meanings = {
        "enrollment_id": "Unique enrollment record identifier",
        "user_id": "Unique user identifier",
        "course_id": "Unique course identifier",
        "course_name": "Display name of the course",
        "category": "Course category/subject area",
        "instructor": "Course instructor name",
        "price": "Course price in USD",
        "rating": "Course average rating",
        "search_query": "Search text entered by user",
        "search_time": "Timestamp of search event",
        "preview_clicked": "Whether a user clicked preview",
        "preview_time": "Timestamp of preview event",
        "enrollment_status": "Status (active, cancelled, pending)",
        "enrollment_date": "Timestamp of enrollment event",
    }

    for col in df.columns:
        null_count = int(df[col].isna().sum())
        null_pct = float(100 * null_count / total) if total else 0.0
        dtype = str(df[col].dtype)
        business = business_meanings.get(col, "")
        report_rows.append(
            {
                "column": col,
                "dtype": dtype,
                "null_count": null_count,
                "null_pct": round(null_pct, 2),
                "business_meaning": business,
            }
        )

    report_df = pd.DataFrame(report_rows)

    # Print professional report
    print("\n===== Missing Value Analysis Report =====")
    print(f"Total rows: {total}\n")
    print(report_df.to_string(index=False))
    print("===== End Report =====\n")

    return report_df


def impute_mean_median(df: pd.DataFrame, columns: Iterable[str], use_median: bool = True) -> pd.DataFrame:
    """Impute numerical columns using median (default) or mean.

    Args:
        df: Input DataFrame.
        columns: Iterable of column names to impute.
        use_median: If True use median, else use mean.

    Returns:
        DataFrame with imputed columns (a copy).
    """
    out = df.copy()
    strategy = "median" if use_median else "mean"
    for col in columns:
        if col not in out.columns:
            logger.warning("Column %s not in DataFrame - skipping mean/median imputation", col)
            continue
        if not pd.api.types.is_numeric_dtype(out[col]):
            logger.warning("Column %s is not numeric - skipping", col)
            continue
        if out[col].isna().all():
            # if all values are missing, impute 0 to avoid NaNs, but log risk
            fill_val = 0
            logger.warning("Column %s has all values missing; imputing 0", col)
        else:
            fill_val = float(out[col].median()) if use_median else float(out[col].mean())
        out[col] = out[col].fillna(fill_val)
        logger.info("Imputed %s using %s -> %s", col, strategy, fill_val)
    return out


def impute_mode(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Impute categorical columns using the mode (most frequent value).

    If mode cannot be found, fills with the literal 'Unknown'.
    """
    out = df.copy()
    for col in columns:
        if col not in out.columns:
            logger.warning("Column %s not in DataFrame - skipping mode imputation", col)
            continue
        try:
            mode_vals = out[col].mode(dropna=True)
            if not mode_vals.empty:
                fill_val = mode_vals.iloc[0]
            else:
                fill_val = "Unknown"
            out[col] = out[col].fillna(fill_val)
            logger.info("Imputed %s using mode -> %s", col, fill_val)
        except Exception:
            logger.exception("Failed to impute mode for %s", col)
            out[col] = out[col].fillna("Unknown")
    return out


def impute_forward_fill(df: pd.DataFrame, columns: Iterable[str]) -> pd.DataFrame:
    """Apply forward-fill imputation for time-series related columns.

    This performs a forward-fill across rows; it does not attempt to
    reorder data (assumes data is already in a meaningful sequence).
    """
    out = df.copy()
    try:
        out[columns] = out[columns].fillna(method="ffill")
        logger.info("Forward-filled columns: %s", list(columns))
    except Exception:
        logger.exception("Error during forward fill for columns: %s", list(columns))
    return out


def drop_rows_with_nulls(df: pd.DataFrame, critical_columns: Iterable[str]) -> pd.DataFrame:
    """Drop rows that are missing any of the critical identifier columns.

    Args:
        df: Input DataFrame.
        critical_columns: Columns that must be present (e.g., course_id, user_id).

    Returns:
        DataFrame with rows dropped.
    """
    out = df.copy()
    before = len(out)
    out = out.dropna(subset=list(critical_columns))
    after = len(out)
    logger.info("Dropped rows missing %s: %d -> %d", list(critical_columns), before, after)
    return out


def document_imputation_decisions(decisions: Dict[str, Dict[str, str]], out_path: Path) -> None:
    """Write imputation decisions to a JSON file.

    Args:
        decisions: Mapping from column -> {Strategy, Business Reason, Risk}.
        out_path: Destination JSON file path.
    """
    try:
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8") as fh:
            json.dump(decisions, fh, indent=2, ensure_ascii=False)
        logger.info("Wrote imputation decisions to %s", out_path)
    except Exception:
        logger.exception("Failed to write imputation decisions to %s", out_path)
        raise


def validate_imputation(df_before: pd.DataFrame, df_after: pd.DataFrame) -> None:
    """Compare dataset metrics before and after imputation and print tables.

    Displays rows before/after and null counts/percentages before/after.
    """
    rows_before = len(df_before)
    rows_after = len(df_after)

    nulls_before = df_before.isna().sum()
    nulls_after = df_after.isna().sum()

    pct_before = (nulls_before / rows_before * 100).round(2) if rows_before else nulls_before
    pct_after = (nulls_after / rows_after * 100).round(2) if rows_after else nulls_after

    summary = pd.DataFrame(
        {
            "nulls_before": nulls_before,
            "nulls_after": nulls_after,
            "pct_before": pct_before,
            "pct_after": pct_after,
        }
    )

    print("\n===== Imputation Validation =====")
    print(f"Rows before: {rows_before}")
    print(f"Rows after:  {rows_after}\n")
    print(summary.to_string())
    print("===== End Validation =====\n")


def _build_default_decisions() -> Dict[str, Dict[str, str]]:
    """Return a default decisions template for known columns.

    Consumers may modify or extend this dict prior to writing.
    """
    return {
        "price": {
            "Strategy": "Median",
            "Business Reason": "Median avoids distortion from expensive premium courses.",
            "Risk": "Low",
        },
        "rating": {
            "Strategy": "Median",
            "Business Reason": "Ratings are usually clustered between 3 and 5.",
            "Risk": "Low",
        },
        "category": {
            "Strategy": "Mode",
            "Business Reason": "Most common category preserves dataset consistency.",
            "Risk": "Medium",
        },
        "course_name": {
            "Strategy": "Mode",
            "Business Reason": "Mode preserves most frequent naming and keeps labels consistent.",
            "Risk": "Medium",
        },
        "search_query": {
            "Strategy": "Mode",
            "Business Reason": "Common search terms represent typical queries; unknowns are less useful.",
            "Risk": "Medium",
        },
        "enrollment_status": {
            "Strategy": "Mode",
            "Business Reason": "Keeps majority behaviour (e.g., active) visible for analytics.",
            "Risk": "Medium",
        },
        "search_time": {
            "Strategy": "Forward Fill",
            "Business Reason": "Search events are sequential; previous timestamp is the best guess.",
            "Risk": "Medium",
        },
        "preview_time": {
            "Strategy": "Forward Fill",
            "Business Reason": "Preview events typically follow a user session sequence.",
            "Risk": "Medium",
        },
        "enrollment_date": {
            "Strategy": "Forward Fill",
            "Business Reason": "Enrollment events follow user session ordering.",
            "Risk": "Medium",
        },
        "course_id": {
            "Strategy": "Drop Row",
            "Business Reason": "Cannot analyze course performance without course identifier.",
            "Risk": "Low",
        },
        "user_id": {
            "Strategy": "Drop Row",
            "Business Reason": "Cannot attribute activity to users without identifier.",
            "Risk": "Low",
        },
    }


def main() -> None:
    """Complete workflow for missing-value analysis and imputation.

    Loads `data/raw/missing_data.csv`, runs analysis, applies the
    imputation strategies described in the assignment, writes a JSON
    documenting decisions to `output/imputation_decisions.json`, validates
    the changes, and saves the cleaned data to
    `data/processed/cleaned_data.csv`.
    """
    base = Path(__file__).resolve().parents[1]
    raw = base / "data" / "raw" / "missing_data.csv"
    processed_dir = base / "data" / "processed"
    output_dir = base / "output"
    processed_dir.mkdir(parents=True, exist_ok=True)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        df = pd.read_csv(raw)
    except FileNotFoundError:
        logger.error("Missing input file: %s", raw)
        raise
    except Exception:
        logger.exception("Failed to load missing_data.csv")
        raise

    # Snapshot for validation
    df_before = df.copy()

    # TASK: Analyze
    _ = analyze_missing_values(df)

    # TASK: Drop critical rows
    df = drop_rows_with_nulls(df, ["course_id", "user_id"])

    # TASK: Median imputation for numeric columns
    df = impute_mean_median(df, ["price", "rating"], use_median=True)

    # TASK: Mode imputation for categorical columns
    df = impute_mode(df, ["category", "course_name", "search_query", "enrollment_status"])

    # TASK: Forward fill for time-series columns
    df = impute_forward_fill(df, ["search_time", "preview_time", "enrollment_date"])

    # TASK: Document decisions
    decisions = _build_default_decisions()
    # Augment with before/after null counts for transparency
    for col in list(decisions.keys()):
        before_nulls = int(df_before[col].isna().sum()) if col in df_before.columns else None
        after_nulls = int(df[col].isna().sum()) if col in df.columns else None
        decisions[col]["nulls_before"] = before_nulls
        decisions[col]["nulls_after"] = after_nulls

    document_imputation_decisions(decisions, output_dir / "imputation_decisions.json")

    # TASK: Validate
    validate_imputation(df_before, df)

    # TASK: Save cleaned dataset
    out_file = processed_dir / "cleaned_data.csv"
    try:
        df.to_csv(out_file, index=False)
        logger.info("Saved cleaned dataset to %s", out_file)
    except Exception:
        logger.exception("Failed to write cleaned dataset to %s", out_file)
        raise

    print("Imputation workflow complete. Cleaned data and documentation written.")


if __name__ == "__main__":
    main()
