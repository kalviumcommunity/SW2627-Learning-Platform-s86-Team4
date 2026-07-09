"""
main.py

Purpose:
--------
This is the entry point of the project.

Workflow:
1. Configure logging
2. Load dataset
3. Process dataset
4. Generate analysis
5. Save cleaned dataset
6. Save report
"""

import os
import logging

from ingest import ingest_data
from process import process_data
from output import save_clean_data, generate_report, save_report


# -----------------------------
# Configuration
# -----------------------------
RAW_DATA_PATH = "data/raw/course_engagement.csv"
CLEAN_DATA_PATH = "data/processed/clean_course_engagement.csv"
REPORT_PATH = "reports/analysis_report.txt"
LOG_PATH = "logs/workflow.log"


# -----------------------------
# Logging Configuration
# -----------------------------
os.makedirs("logs", exist_ok=True)

logging.basicConfig(
    filename=LOG_PATH,
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)


def main():
    """
    Runs the complete data engineering workflow.
    """

    logging.info("=" * 50)
    logging.info("Application Started")

    try:

        # Step 1 : Load Dataset
        df = ingest_data(RAW_DATA_PATH)

        # Step 2 : Clean Dataset
        clean_df = process_data(df)

        # Step 3 : Generate Report
        report = generate_report(clean_df)

        # Step 4 : Save Clean Data
        save_clean_data(clean_df, CLEAN_DATA_PATH)

        # Step 5 : Save Report
        save_report(report, REPORT_PATH)

        logging.info("Application Completed Successfully")

        print("\n🎉 Workflow Completed Successfully!")

    except Exception as error:

        logging.exception(f"Application Failed : {error}")

        print(f"\n❌ Error : {error}")


# -----------------------------
# Entry Point
# -----------------------------
if __name__ == "__main__":
    main()