"""
Dataset intake validation for the Course Conversion Analytics Dashboard.

This script acts as a quality gate before downstream data processing starts.
"""

from __future__ import annotations

import json
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import chardet
import pandas as pd


for stream in (sys.stdout, sys.stderr):
    if hasattr(stream, "reconfigure"):
        stream.reconfigure(encoding="utf-8")

# Configuration
PROJECT_ROOT = Path(__file__).resolve().parents[1]
INPUT_FILE = PROJECT_ROOT / "data" / "raw" / "course_data.csv"
OUTPUT_REPORT = PROJECT_ROOT / "output" / "intake_report.json"
LOG_FILE = PROJECT_ROOT / "logs" / "intake_validation.log"
EXPECTED_COLUMNS = [
    "user_id",
    "search_query",
    "course_id",
    "course_name",
    "category",
    "preview_clicked",
    "enrolled",
    "search_time",
]
ALLOWED_FORMATS = {".csv", ".json", ".xlsx"}


LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(LOG_FILE, encoding="utf-8"),
        logging.StreamHandler(),
    ],
)
logger = logging.getLogger(__name__)


def validate_file_exists(filepath: Path) -> bool:
    """Check that the source file exists and is not empty."""
    logger.info("Validating source file exists: %s", filepath)

    if not filepath.exists():
        raise FileNotFoundError(f"Input file does not exist: {filepath}")

    if not filepath.is_file():
        raise ValueError(f"Input path is not a file: {filepath}")

    if filepath.stat().st_size == 0:
        raise ValueError(f"Input file is empty: {filepath}")

    print("✓ File exists")
    return True


def validate_file_format(filepath: Path) -> str:
    """Validate that the file extension is one of csv, json, or xlsx."""
    logger.info("Validating source file format: %s", filepath.suffix)
    extension = filepath.suffix.lower()

    if extension not in ALLOWED_FORMATS:
        allowed = ", ".join(sorted(ALLOWED_FORMATS))
        raise ValueError(f"Invalid file format '{extension}'. Allowed formats: {allowed}")

    print("✓ Format valid")
    return extension.lstrip(".")


def validate_schema(df: pd.DataFrame, expected_columns: list[str]) -> dict[str, Any]:
    """Detect missing and unexpected columns in the loaded dataset."""
    logger.info("Validating dataset schema")
    actual_columns = list(df.columns)
    missing_columns = [column for column in expected_columns if column not in actual_columns]
    unexpected_columns = [column for column in actual_columns if column not in expected_columns]

    schema_result = {
        "status": "PASS" if not missing_columns and not unexpected_columns else "FAIL",
        "missing_columns": missing_columns,
        "unexpected_columns": unexpected_columns,
    }

    if schema_result["status"] == "FAIL":
        raise ValueError(
            "Schema validation failed. "
            f"Missing columns: {missing_columns}. "
            f"Unexpected columns: {unexpected_columns}."
        )

    print("✓ Schema valid")
    return schema_result


def detect_encoding(filepath: Path) -> dict[str, Any]:
    """Detect file encoding with chardet and return encoding plus confidence."""
    logger.info("Detecting source file encoding")

    with filepath.open("rb") as file:
        sample = file.read()

    detection = chardet.detect(sample)
    encoding = detection.get("encoding") or "unknown"
    confidence = round(float(detection.get("confidence") or 0.0), 4)

    print("✓ Encoding detected")
    return {"encoding": encoding, "confidence": confidence}


def capture_dataset_stats(filepath: Path, df: pd.DataFrame) -> dict[str, Any]:
    """Capture row count, column count, file size in MB, and bytes."""
    logger.info("Collecting source dataset statistics")
    file_size_bytes = filepath.stat().st_size

    stats = {
        "rows": int(df.shape[0]),
        "columns": int(df.shape[1]),
        "file_size_mb": round(file_size_bytes / (1024 * 1024), 4),
        "bytes": file_size_bytes,
    }

    print("✓ Statistics collected")
    return stats


def load_dataset(filepath: Path) -> pd.DataFrame:
    """Load a supported intake file into a pandas DataFrame."""
    logger.info("Loading dataset with pandas")
    extension = filepath.suffix.lower()

    if extension == ".csv":
        return pd.read_csv(filepath)
    if extension == ".json":
        return pd.read_json(filepath)
    if extension == ".xlsx":
        return pd.read_excel(filepath)

    raise ValueError(f"Unsupported file extension: {extension}")


def save_report(report: dict[str, Any]) -> None:
    """Write the intake validation report to disk as formatted JSON."""
    OUTPUT_REPORT.parent.mkdir(parents=True, exist_ok=True)
    with OUTPUT_REPORT.open("w", encoding="utf-8") as file:
        json.dump(report, file, indent=4)
        file.write("\n")


def generate_intake_report(filepath: Path, expected_columns: list[str]) -> dict[str, Any]:
    """Run all intake validations, collect metadata, and save the JSON report."""
    logger.info("Starting dataset intake validation")
    report: dict[str, Any] = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "filepath": str(filepath),
        "validations": {
            "file_exists": "NOT_RUN",
            "format": "NOT_RUN",
            "schema": "NOT_RUN",
            "encoding": "NOT_RUN",
        },
        "statistics": {},
    }

    try:
        validate_file_exists(filepath)
        report["validations"]["file_exists"] = "PASS"

        file_format = validate_file_format(filepath)
        report["validations"]["format"] = "PASS"
        report["format"] = file_format

        df = load_dataset(filepath)

        schema_result = validate_schema(df, expected_columns)
        report["validations"]["schema"] = schema_result["status"]
        report["schema_details"] = {
            "missing_columns": schema_result["missing_columns"],
            "unexpected_columns": schema_result["unexpected_columns"],
        }

        encoding_result = detect_encoding(filepath)
        report["validations"]["encoding"] = "PASS"
        report["encoding_details"] = encoding_result

        report["statistics"] = capture_dataset_stats(filepath, df)
        report["status"] = "PASS"

        save_report(report)
        print("✓ Intake report generated")
        logger.info("Intake validation completed successfully")
        return report

    except Exception as error:
        logger.exception("Intake validation failed")
        report["status"] = "FAIL"
        report["error"] = str(error)
        save_report(report)
        print(f"FAIL: {error}")
        raise


def main() -> None:
    """Run the configured dataset intake validation quality gate."""
    try:
        generate_intake_report(INPUT_FILE, EXPECTED_COLUMNS)
        print("PASS: Dataset intake validation completed successfully.")
    except Exception:
        print("FAIL: Dataset intake validation did not pass.")
        raise SystemExit(1)


if __name__ == "__main__":
    main()
