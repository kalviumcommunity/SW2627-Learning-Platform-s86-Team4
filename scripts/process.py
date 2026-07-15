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


OUTLIER_RULES = {
    "session_minutes": {
        "method": "iqr",
        "action": "cap",
        "reason": "Session length can have valid long tails; capping limits skew while preserving rows.",
    },
    "price": {
        "method": "iqr",
        "action": "flag",
        "reason": "Premium pricing can be legitimate; keep values and flag anomalies for segment analysis.",
    },
    "rating": {
        "method": "zscore",
        "action": "remove",
        "threshold": 3.0,
        "reason": "Extreme rating anomalies are likely data quality issues and are removed.",
    },
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


def _detect_iqr_outliers(series):
    """
    Detect outliers using the IQR rule and return mask with clip bounds.
    """
    q1 = series.quantile(0.25)
    q3 = series.quantile(0.75)
    iqr = q3 - q1

    if pd.isna(iqr) or iqr == 0:
        mask = pd.Series(False, index=series.index)
        return mask, None, None

    lower_bound = q1 - 1.5 * iqr
    upper_bound = q3 + 1.5 * iqr
    mask = (series < lower_bound) | (series > upper_bound)
    return mask, lower_bound, upper_bound


def _detect_zscore_outliers(series, threshold=3.0):
    """
    Detect outliers using Z-score and return mask with equivalent clip bounds.
    """
    mean_value = series.mean()
    std_value = series.std(ddof=0)

    if pd.isna(std_value) or std_value == 0:
        mask = pd.Series(False, index=series.index)
        return mask, None, None

    z_scores = ((series - mean_value) / std_value).abs()
    lower_bound = mean_value - threshold * std_value
    upper_bound = mean_value + threshold * std_value
    mask = z_scores > threshold
    return mask, lower_bound, upper_bound


def _apply_outlier_rules(df):
    """
    Apply per-column outlier strategies and return an audit trail.
    """
    outlier_audit = []
    working_df = df.copy()

    for column, rule in OUTLIER_RULES.items():
        if column not in working_df.columns:
            continue

        numeric_series = pd.to_numeric(working_df[column], errors="coerce")
        method = rule.get("method", "iqr")
        action = rule.get("action", "flag")

        if method == "iqr":
            outlier_mask, lower_bound, upper_bound = _detect_iqr_outliers(numeric_series)
        elif method == "zscore":
            threshold = float(rule.get("threshold", 3.0))
            outlier_mask, lower_bound, upper_bound = _detect_zscore_outliers(
                numeric_series,
                threshold=threshold,
            )
        else:
            raise ValueError(f"Unsupported outlier method '{method}' for column '{column}'")

        outlier_mask = outlier_mask.fillna(False)
        flag_column = f"is_{column}_outlier"
        working_df[flag_column] = outlier_mask.astype("int64")

        rows_before_action = len(working_df)

        if action == "cap":
            if lower_bound is not None and upper_bound is not None:
                working_df[column] = numeric_series.clip(lower=lower_bound, upper=upper_bound)
        elif action == "remove":
            working_df = working_df.loc[~outlier_mask].copy()
        elif action == "flag":
            pass
        else:
            raise ValueError(f"Unsupported outlier action '{action}' for column '{column}'")

        rows_after_action = len(working_df)
        outlier_count = int(outlier_mask.sum())

        outlier_audit.append(
            {
                "column": column,
                "method": method,
                "action": action,
                "outlier_count": outlier_count,
                "rows_removed": int(rows_before_action - rows_after_action),
                "lower_bound": None if lower_bound is None else float(lower_bound),
                "upper_bound": None if upper_bound is None else float(upper_bound),
                "reason": rule.get("reason", "No reason provided."),
            }
        )

    return working_df, outlier_audit


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

    # -----------------------------
    # Outlier Detection and Handling
    # -----------------------------
    df, outlier_audit = _apply_outlier_rules(df)
    df.attrs["outlier_audit"] = outlier_audit

    total_outliers_flagged = sum(item["outlier_count"] for item in outlier_audit)
    total_rows_removed = sum(item["rows_removed"] for item in outlier_audit)
    logging.info(
        "Outlier handling complete. Outliers flagged: %s, rows removed: %s",
        total_outliers_flagged,
        total_rows_removed,
    )

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