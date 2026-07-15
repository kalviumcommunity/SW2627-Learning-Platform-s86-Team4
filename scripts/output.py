"""
output.py

Purpose:
--------
This module is responsible for saving the cleaned dataset
and generating a simple analysis report.
"""

import os
import logging


def _count_truthy(series):
    """
    Count truthy values across common boolean encodings.
    """
    normalized = series.astype(str).str.strip().str.lower()
    return normalized.isin({"yes", "true", "1"}).sum()


def _write_report_value(file_handle, key, value, indent_level=0):
    """
    Write nested report values with readable indentation.
    """
    indent = "    " * indent_level
    if isinstance(value, dict):
        file_handle.write(f"{indent}{key}:\n")
        for nested_key, nested_value in value.items():
            _write_report_value(file_handle, nested_key, nested_value, indent_level + 1)
    elif isinstance(value, list):
        file_handle.write(f"{indent}{key}:\n")
        for item in value:
            if isinstance(item, dict):
                for nested_key, nested_value in item.items():
                    _write_report_value(file_handle, nested_key, nested_value, indent_level + 1)
            else:
                file_handle.write(f"{indent}    - {item}\n")
    else:
        file_handle.write(f"{indent}{key}: {value}\n")


def generate_report(df):
    """
    Generates summary statistics from the cleaned dataset.

    Parameters
    ----------
    df : pandas.DataFrame

    Returns
    -------
    dict
        Dictionary containing analysis results.
    """

    total_records = len(df)

    total_previews = _count_truthy(df["preview_clicked"])

    total_enrollments = _count_truthy(df["enrolled"])

    conversion_rate = 0

    if total_previews != 0:
        conversion_rate = (total_enrollments / total_previews) * 100

    most_viewed = (
        df["course_name"]
        .value_counts()
        .idxmax()
    )

    report = {
        "Total Records": total_records,
        "Preview Clicks": total_previews,
        "Enrollments": total_enrollments,
        "Preview to Enrollment Conversion (%)": round(conversion_rate, 2),
        "Most Viewed Course": most_viewed,
        "Type Enforcement": df.attrs.get("type_enforcement", {}),
        "Datetime Feature Engineering": df.attrs.get("datetime_features", {}),
        "Weekly Time Series Summary": df.attrs.get("weekly_time_series", {}),
    }

    return report


def save_clean_data(df, output_path):
    """
    Saves cleaned dataset.

    Parameters
    ----------
    df : pandas.DataFrame

    output_path : str
    """

    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    df.to_csv(output_path, index=False)

    logging.info(f"Cleaned dataset saved at {output_path}")

    print("✅ Cleaned dataset saved.")


def save_report(report, report_path):
    """
    Saves analysis report.

    Parameters
    ----------
    report : dict

    report_path : str
    """

    os.makedirs(os.path.dirname(report_path), exist_ok=True)

    with open(report_path, "w") as file:

        file.write("ONLINE LEARNING PLATFORM REPORT\n")
        file.write("=" * 40)
        file.write("\n\n")

        for key, value in report.items():
            _write_report_value(file, key, value)
            file.write("\n")

    logging.info(f"Report saved at {report_path}")

    print("✅ Report generated.")