"""
output.py

Purpose:
--------
This module is responsible for saving the cleaned dataset
and generating a simple analysis report.
"""

import os
import logging


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

    total_previews = (
        df["preview_clicked"]
        .astype(str)
        .str.lower()
        .eq("yes")
        .sum()
    )

    total_enrollments = (
        df["enrolled"]
        .astype(str)
        .str.lower()
        .eq("yes")
        .sum()
    )

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
        "Most Viewed Course": most_viewed
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
            file.write(f"{key}: {value}\n")

    logging.info(f"Report saved at {report_path}")

    print("✅ Report generated.")