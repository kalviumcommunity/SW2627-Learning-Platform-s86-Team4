"""
ingest.py

Purpose:
--------
This module is responsible for reading the raw dataset from disk.
It validates that the file exists and returns a Pandas DataFrame.
"""

import os
import logging
import pandas as pd


def ingest_data(file_path):
    """
    Reads the CSV dataset and returns it as a Pandas DataFrame.

    Args:
        file_path (str):
            Path to the CSV file.

    Returns:
        pd.DataFrame:
            Loaded dataset.

    Raises:
        FileNotFoundError:
            If the CSV file does not exist.

        Exception:
            Any unexpected error while reading the file.
    """

    try:
        # Check if file exists
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Dataset not found: {file_path}")

        # Read CSV
        df = pd.read_csv(file_path)

        logging.info(f"Dataset loaded successfully.")
        logging.info(f"Rows: {len(df)}")
        logging.info(f"Columns: {len(df.columns)}")

        print("✅ Dataset loaded successfully.")

        return df

    except FileNotFoundError as error:
        logging.error(error)
        raise

    except Exception as error:
        logging.error(f"Unexpected Error: {error}")
        raise