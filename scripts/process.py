"""
process.py

Purpose:
--------
This module cleans and processes the raw dataset.
"""

import logging
import pandas as pd


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
        df[column] = df[column].astype(str).str.strip()

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
    if "session_minutes" in df.columns:
        df["session_minutes"] = pd.to_numeric(
            df["session_minutes"],
            errors="coerce"
        )

    if "price" in df.columns:
        df["price"] = pd.to_numeric(
            df["price"],
            errors="coerce"
        )

    if "rating" in df.columns:
        df["rating"] = pd.to_numeric(
            df["rating"],
            errors="coerce"
        )

    if "date" in df.columns:
        df["date"] = pd.to_datetime(
            df["date"],
            errors="coerce"
        )

    logging.info("Data types converted.")

    # -----------------------------
    # Remove invalid records
    # -----------------------------
    if "session_minutes" in df.columns:
        df = df[df["session_minutes"] >= 0]

    if "price" in df.columns:
        df = df[df["price"] >= 0]

    logging.info("Invalid records removed.")

    cleaned_rows = len(df)

    logging.info(f"Rows before cleaning : {original_rows}")
    logging.info(f"Rows after cleaning  : {cleaned_rows}")

    print("✅ Data cleaned successfully.")

    return df