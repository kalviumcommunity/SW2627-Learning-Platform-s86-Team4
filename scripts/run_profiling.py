"""
run_profiling.py

Purpose:
--------
This script runs the data profiling module on the course engagement dataset.
It configures quality and validity rules, runs the profiler, outputs a
console summary of the findings, and exports detailed reports.
"""

import os
import sys
import logging
from pprint import pprint

# Reconfigure output streams to handle Unicode characters (like emojis) on Windows
for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

# Ensure the scripts directory is in python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from ingest import ingest_data
from profiling import DatasetProfiler

# Configure Logging for runner
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def main():
    # Define paths
    raw_data_path = "data/raw/course_engagement.csv"
    reports_output_dir = "reports"
    report_base_name = "course_engagement_profiling"

    print("=" * 60)
    print("🚀 Starting Data Profiling Execution")
    print("=" * 60)

    # 1. Load Dataset
    try:
        df = ingest_data(raw_data_path)
    except Exception as e:
        logger.error(f"Failed to load dataset: {e}")
        sys.exit(1)

    # 2. Instantiate Profiler
    profiler = DatasetProfiler(df)

    # 3. Define Validity Validation Rules
    # These rules target common dataset quality issues:
    # - Negative session minutes (invalid session length)
    # - Negative pricing (invalid commercial transactions)
    # - Future dates (temporal errors)
    # - Strict regex formats for user IDs (e.g. U001, U010, U100) and Course IDs (e.g. C101)
    validity_rules = {
        "session_minutes": {"min_value": 0},
        "price": {"min_value": 0},
        "rating": {"min_value": 0.0, "max_value": 5.0},
        "date": {"allow_future_dates": False},
        "user_id": {"regex": r"^U\d{3}$"},
        "course_id": {"regex": r"^C\d{3}$"},
        "search_query": {"check_empty_strings": True}
    }

    # 4. Run full profiling suite
    print("\n🔍 Running analysis profiling pipelines...")
    results = profiler.run_all(validity_rules=validity_rules)

    # 5. Output Console Summaries
    print("\n=== DATASET OVERVIEW ===")
    print(f"Total Rows:     {results['overview']['num_rows']}")
    print(f"Total Columns:  {results['overview']['num_columns']}")
    print(f"Memory Footprint: {results['overview']['memory_usage']}")

    print("\n=== MISSING VALUE ANALYSIS ===")
    for item in results["missing_values"]:
        print(f"• {item['column']}: {item['null_count']} nulls ({item['null_percentage']}%)")

    print("\n=== DUPLICATE ANALYSIS ===")
    print(f"Duplicate Rows: {results['duplicates']['duplicate_count']} ({results['duplicates']['duplicate_percentage']}%)")

    print("\n=== CATEGORICAL DISCREPANCIES DETECTED ===")
    cat_discrepancies = False
    for col, data in results["categorical"].items():
        if data["has_discrepancies"]:
            cat_discrepancies = True
            print(f"• Column: '{col}'")
            if data["casing_discrepancies"]:
                print("  Casing inconsistencies:")
                for item in data["casing_discrepancies"]:
                    print(f"    - Normalized: '{item['normalized_value']}', Variants: {item['variants']}")
            if data["spelling_discrepancies"]:
                print("  Spelling/Fuzzy similarity alerts:")
                for item in data["spelling_discrepancies"]:
                    print(f"    - '{item['value1']}' vs '{item['value2']}' (similarity: {item['similarity_score']})")
    if not cat_discrepancies:
        print("No casing/spelling inconsistencies detected.")

    print("\n=== VALIDITY VIOLATIONS DETECTED ===")
    if results["validity"]:
        for col, data in results["validity"].items():
            print(f"• Column: '{col}' - {data['total_violations']} violations ({data['violation_percentage']}%)")
            for violation in data["sample_violations"]:
                print(f"    - Index {violation['index']}: Value = {violation['value']} | Reason: {violation['reason']}")
    else:
        print("No validity violations detected.")

    print("\n=== DATA QUALITY ASSESSMENT ALERTS ===")
    if results["quality_assessment"]:
        for idx, alert in enumerate(results["quality_assessment"], 1):
            print(f"[{idx}] {alert['severity']} - {alert['type']} ({alert['column']}): {alert['message']}")
    else:
        print("🎉 Dataset passed all quality threshold checks successfully!")

    # 6. Export Reports
    print("\n💾 Exporting reports...")
    saved_files = profiler.export_report(
        output_dir=reports_output_dir,
        base_name=report_base_name,
        formats=["json", "csv", "excel"]
    )

    print("\n=== EXPORTED FILE LOCATIONS ===")
    for path in saved_files:
        print(f"✅ Saved: {path}")

    print("\n" + "=" * 60)
    print("🎉 Profiling run completed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
