"""
process.py

Purpose:
--------
This module cleans and processes the raw dataset.
"""

import logging
import pandas as pd


def clean_text_column(series, lowercase=True, strip=True, remove_special=False, mapping=None):
    """
    Reusable text cleaning helper for consistent string normalization.
    """
    result = series.astype("string")

    if strip:
        result = result.str.strip()

    if lowercase:
        result = result.str.lower()

    if mapping:
        result = result.map(mapping).fillna(result)

    if remove_special:
        result = result.str.replace(r"[^a-zA-Z0-9 ]", "", regex=True)

    return result


TEXT_NORMALIZATION_MAPS = {
    "category": {
        "data science": "Data Science",
        "datascience": "Data Science",
        "programming": "Programming",
        "web development": "Web Development",
        "webdevelopment": "Web Development",
        "database": "Database",
        "ai": "AI",
    },
    "search_query": {
        "b2b": "b2b",
        "b 2 b": "b2b",
        "b2 b": "b2b",
        "business-to-business": "b2b",
    },
}


DATETIME_COLUMN_FORMATS = {
    "transaction_date": "%Y-%m-%d %H:%M:%S",
    "date": "%Y-%m-%d",
    "search_time": "%Y-%m-%dT%H:%M:%S",
    "preview_time": "%Y-%m-%dT%H:%M:%S",
    "enrollment_date": "%Y-%m-%dT%H:%M:%S",
}


def _parse_datetime_columns(df):
    """
    Parse known datetime columns and raise if invalid values are found.
    """
    parsed_columns = []

    for column, dt_format in DATETIME_COLUMN_FORMATS.items():
        if column not in df.columns:
            continue

        parsed = pd.to_datetime(df[column], format=dt_format, errors="coerce")
        invalid_mask = parsed.isna() & df[column].notna()

        if invalid_mask.any():
            bad_values = sorted(df.loc[invalid_mask, column].astype(str).unique().tolist())
            raise ValueError(
                f"Invalid datetime values found in {column} (expected {dt_format}): {bad_values}"
            )

        df[column] = parsed
        parsed_columns.append(column)

    return parsed_columns


def _add_datetime_features(df, source_column):
    """
    Create reusable time-based features from a parsed datetime column.
    """
    df["day_of_week"] = df[source_column].dt.day_name()
    df["day_of_week_num"] = df[source_column].dt.dayofweek
    df["hour_of_day"] = df[source_column].dt.hour
    df["week_number"] = df[source_column].dt.isocalendar().week.astype("int64")
    df["month"] = df[source_column].dt.month
    df["quarter"] = df[source_column].dt.quarter

    reference_day = pd.Timestamp.now().normalize()
    df["days_since_event"] = (reference_day - df[source_column].dt.normalize()).dt.days


def _build_weekly_summary(df, datetime_column):
    """
    Build weekly aggregations using a datetime index.
    """
    ts_df = df.set_index(datetime_column).sort_index()
    weekly = {}

    if "price" in ts_df.columns:
        weekly["weekly_price_sum"] = {
            idx.strftime("%Y-%m-%d"): float(value)
            for idx, value in ts_df["price"].resample("W").sum().round(2).items()
        }

    if "preview_clicked" in ts_df.columns:
        weekly["weekly_previews"] = {
            idx.strftime("%Y-%m-%d"): int(value)
            for idx, value in ts_df["preview_clicked"].astype("Int64").resample("W").sum().items()
        }

    if "enrolled" in ts_df.columns:
        weekly["weekly_enrollments"] = {
            idx.strftime("%Y-%m-%d"): int(value)
            for idx, value in ts_df["enrolled"].astype("Int64").resample("W").sum().items()
        }

    return weekly


def _strip_currency_and_convert(series):
    """
    Remove common currency formatting and convert the series to numeric.
    """
    cleaned = (
        series.astype("string")
        .str.replace(r"[$,]", "", regex=True)
        .str.strip()
    )
    numeric = pd.to_numeric(cleaned, errors="coerce")
    invalid_mask = cleaned.notna() & numeric.isna()
    return numeric, cleaned, invalid_mask


def _convert_to_boolean(series):
    """
    Convert common boolean encodings to pandas boolean values.
    """
    normalized = series.astype("string").str.strip().str.lower()
    mapping = {
        "yes": True,
        "no": False,
        "true": True,
        "false": False,
        "1": True,
        "0": False,
    }
    converted = normalized.map(mapping)
    invalid_mask = normalized.notna() & converted.isna()
    return converted.astype("boolean"), normalized, invalid_mask


def process_data(df):
    """
    Cleans the input DataFrame.

    Parameters
    ----------
    df : pandas.DataFrame
        Raw dataset.

    Returns
    -------
    pandas.DataFrame
        Cleaned dataset.
    """

    logging.info("Starting data cleaning...")

    original_rows = len(df)
    before_dtypes = df.dtypes.astype(str).to_dict()
    type_changes = []

    # -----------------------------
    # Remove duplicate rows
    # -----------------------------
    duplicates = df.duplicated().sum()
    df = df.drop_duplicates()

    logging.info(f"Duplicate rows removed: {duplicates}")

    # -----------------------------
    # Remove leading/trailing spaces
    # -----------------------------
    object_columns = df.select_dtypes(include="object").columns

    for column in object_columns:
        df[column] = clean_text_column(df[column], lowercase=False, strip=True)

    text_columns = ["search_query", "category"]

    for column in text_columns:
        if column in df.columns:
            df[column] = clean_text_column(
                df[column],
                lowercase=True,
                strip=True,
                remove_special=True,
                mapping=TEXT_NORMALIZATION_MAPS.get(column),
            )

    logging.info("Whitespace removed.")

    # -----------------------------
    # Standardize Yes/No values
    # -----------------------------
    yes_no_columns = [
        "preview_clicked",
        "enrolled",
        "completed"
    ]

    for column in yes_no_columns:
        if column in df.columns:
            df[column] = (
                df[column]
                .str.lower()
                .replace({
                    "yes": "Yes",
                    "no": "No",
                    "true": "Yes",
                    "false": "No"
                })
            )

    logging.info("Standardized Yes/No values.")

    # -----------------------------
    # Handle missing values
    # -----------------------------
    if "rating" in df.columns:
        df["rating"] = df["rating"].fillna(0)

    if "search_query" in df.columns:
        df["search_query"] = df["search_query"].fillna("Unknown")

    if "session_minutes" in df.columns:
        median_session = df["session_minutes"].median()
        df["session_minutes"] = df["session_minutes"].fillna(median_session)

    logging.info("Missing values handled.")

    # -----------------------------
    # Convert Data Types
    # -----------------------------
    if "preview_clicked" in df.columns:
        df["preview_clicked"], normalized_preview, invalid_preview = _convert_to_boolean(
            df["preview_clicked"]
        )
        if invalid_preview.any():
            bad_values = sorted(normalized_preview[invalid_preview].dropna().unique().tolist())
            raise ValueError(
                f"Invalid boolean values found in preview_clicked: {bad_values}"
            )
        type_changes.append("preview_clicked: converted to boolean")

    if "enrolled" in df.columns:
        df["enrolled"], normalized_enrolled, invalid_enrolled = _convert_to_boolean(
            df["enrolled"]
        )
        if invalid_enrolled.any():
            bad_values = sorted(normalized_enrolled[invalid_enrolled].dropna().unique().tolist())
            raise ValueError(
                f"Invalid boolean values found in enrolled: {bad_values}"
            )
        type_changes.append("enrolled: converted to boolean")

    if "completed" in df.columns:
        df["completed"], normalized_completed, invalid_completed = _convert_to_boolean(
            df["completed"]
        )
        if invalid_completed.any():
            bad_values = sorted(normalized_completed[invalid_completed].dropna().unique().tolist())
            raise ValueError(
                f"Invalid boolean values found in completed: {bad_values}"
            )
        type_changes.append("completed: converted to boolean")

    if "session_minutes" in df.columns:
        df["session_minutes"] = pd.to_numeric(
            df["session_minutes"],
            errors="coerce"
        )
        type_changes.append("session_minutes: converted to numeric")

    if "price" in df.columns:
        df["price"], cleaned_price, invalid_price = _strip_currency_and_convert(
            df["price"]
        )
        df["price"] = df["price"].astype("float64")
        if invalid_price.any():
            bad_values = sorted(cleaned_price[invalid_price].dropna().unique().tolist())
            raise ValueError(
                f"Invalid currency values found in price: {bad_values}"
            )
        type_changes.append("price: stripped currency symbols and converted to numeric")

    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(
            df["rating"],
            errors="coerce"
        )
        type_changes.append("rating: converted to numeric")

    parsed_datetime_columns = _parse_datetime_columns(df)
    for column in parsed_datetime_columns:
        type_changes.append(f"{column}: parsed as datetime")

    logging.info("Data types converted.")

    # -----------------------------
    # Datetime Feature Engineering
    # -----------------------------
    datetime_source_column = None
    for candidate in ["transaction_date", "date", "search_time", "preview_time", "enrollment_date"]:
        if candidate in df.columns:
            datetime_source_column = candidate
            break

    if datetime_source_column is not None:
        _add_datetime_features(df, datetime_source_column)
        weekly_summary = _build_weekly_summary(df, datetime_source_column)
        df.attrs["datetime_features"] = {
            "source_column": datetime_source_column,
            "generated_columns": [
                "day_of_week",
                "day_of_week_num",
                "hour_of_day",
                "week_number",
                "month",
                "quarter",
                "days_since_event",
            ],
        }
        df.attrs["weekly_time_series"] = weekly_summary
        logging.info(
            "Datetime features created using %s and weekly resample summary prepared.",
            datetime_source_column,
        )

    # -----------------------------
    # Remove invalid records
    # -----------------------------
    if "session_minutes" in df.columns:
        df = df[df["session_minutes"] >= 0]

    if "price" in df.columns:
        df = df[df["price"] >= 0]

    logging.info("Invalid records removed.")

    cleaned_rows = len(df)
    after_dtypes = df.dtypes.astype(str).to_dict()

    type_report = {
        "before_dtypes": before_dtypes,
        "after_dtypes": after_dtypes,
        "conversions": type_changes,
    }
    df.attrs["type_enforcement"] = type_report

    logging.info(f"Rows before cleaning : {original_rows}")
    logging.info(f"Rows after cleaning  : {cleaned_rows}")
    logging.info(f"Type conversions applied: {', '.join(type_changes) if type_changes else 'none'}")

    print("✅ Data cleaned successfully.")

    return df