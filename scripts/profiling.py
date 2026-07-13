"""
profiling.py

Purpose:
--------
This module provides a production-grade, highly modular, and configurable 
data profiling utility for Pandas DataFrames. It is designed to act as a 
pre-analysis quality gate, identifying schema statistics, missing values,
duplicates, data type breakdowns, statistical summaries, outliers, validity
rules, and quality alerts.

Design Philosophy:
------------------
1. Modular Architecture: Each profiling dimension (Overview, Missing, etc.)
   has a dedicated method.
2. Production Quality: Includes type hints, robust error handling, PEP 8 compliance,
   and clean separation of concerns.
3. Configurable: Validity checks can be easily configured using standard rules.
4. Exportable: Reports can be exported to JSON, CSV, or multi-tab Excel sheets.
"""

from __future__ import annotations

import os
import json
import re
import logging
from datetime import datetime, date
import difflib
from typing import Any, Dict, List, Union, Optional

import numpy as np
import pandas as pd

# Set up logging for this module
logger = logging.getLogger(__name__)


class ProfilerJSONEncoder(json.JSONEncoder):
    """
    Custom JSON Encoder to handle NumPy types, Pandas Timestamps,
    and missing values (NaN) during JSON serialization.
    """
    def default(self, obj: Any) -> Any:
        if isinstance(obj, (np.integer, np.int64, np.int32, np.int16, np.int8)):
            return int(obj)
        elif isinstance(obj, (np.floating, np.float64, np.float32, np.float16)):
            if np.isnan(obj) or np.isinf(obj):
                return None
            return float(obj)
        elif isinstance(obj, (np.ndarray,)):
            return obj.tolist()
        elif isinstance(obj, (pd.Timestamp, datetime, date)):
            return obj.isoformat()
        elif isinstance(obj, pd.Series):
            return obj.to_dict()
        elif pd.isna(obj):
            return None
        try:
            return super().default(obj)
        except TypeError:
            return str(obj)


class DatasetProfiler:
    """
    A comprehensive DataFrame profiling engine that generates structural,
    statistical, and quality assessments of datasets.
    """

    def __init__(self, df: pd.DataFrame):
        """
        Initializes the profiler with a Pandas DataFrame.

        Args:
            df (pd.DataFrame): The dataset to profile.
        
        Raises:
            ValueError: If the input is not a pandas DataFrame.
        """
        if not isinstance(df, pd.DataFrame):
            raise ValueError("Input must be a pandas DataFrame.")
        
        # Keep a copy of the dataframe to prevent side-effects
        self.df = df.copy()
        self.results: Dict[str, Any] = {}

    def get_memory_usage_str(self) -> str:
        """
        Calculates the total memory usage of the DataFrame in bytes
        and returns a human-readable string (KB, MB, GB).

        Returns:
            str: Human-readable memory footprint.
        """
        try:
            # We use deep=True to inspect object/string column memory footprints
            total_bytes = self.df.memory_usage(deep=True).sum()
        except Exception as e:
            logger.warning(f"Deep memory calculation failed: {e}. Falling back to standard memory usage.")
            total_bytes = self.df.memory_usage().sum()

        if total_bytes < 1024:
            return f"{total_bytes} B"
        elif total_bytes < 1024 * 1024:
            return f"{total_bytes / 1024:.2f} KB"
        elif total_bytes < 1024 * 1024 * 1024:
            return f"{total_bytes / (1024 * 1024):.2f} MB"
        else:
            return f"{total_bytes / (1024 * 1024 * 1024):.2f} GB"

    def profile_overview(self) -> Dict[str, Any]:
        """
        Generates basic metadata and structural overview of the dataset.

        Returns:
            Dict[str, Any]: Basic metadata of the DataFrame.
        """
        logger.info("Generating dataset overview statistics...")
        
        overview = {
            "num_rows": len(self.df),
            "num_columns": len(self.df.columns),
            "memory_usage": self.get_memory_usage_str(),
            "column_names": list(self.df.columns),
            "dtypes": {col: str(dtype) for col, dtype in self.df.dtypes.items()}
        }
        
        self.results["overview"] = overview
        return overview

    def profile_missing_values(self) -> List[Dict[str, Any]]:
        """
        Analyzes the count and percentage of missing values in each column.
        Sorts the result in descending order by highest null percentage.

        Returns:
            List[Dict[str, Any]]: A list of dictionaries representing null stats per column.
        """
        logger.info("Analyzing missing values...")
        total_rows = len(self.df)
        null_analysis = []

        if total_rows == 0:
            for col in self.df.columns:
                null_analysis.append({
                    "column": col,
                    "null_count": 0,
                    "null_percentage": 0.0
                })
            self.results["missing_values"] = null_analysis
            return null_analysis

        null_counts = self.df.isnull().sum()
        
        for col, count in null_counts.items():
            percentage = (count / total_rows) * 100
            null_analysis.append({
                "column": col,
                "null_count": int(count),
                "null_percentage": round(float(percentage), 2)
            })

        # Sort columns by highest null percentage descending
        null_analysis.sort(key=lambda x: x["null_percentage"], reverse=True)
        
        self.results["missing_values"] = null_analysis
        return null_analysis

    def profile_duplicates(self, identify_records: bool = False) -> Dict[str, Any]:
        """
        Calculates the exact duplicate row count and duplicate percentage.
        Optionally returns indices and rows that are duplicates.

        Args:
            identify_records (bool): If True, returns a sample of duplicate records.

        Returns:
            Dict[str, Any]: Summary of duplicates in the DataFrame.
        """
        logger.info("Performing duplicate rows analysis...")
        total_rows = len(self.df)
        
        if total_rows == 0:
            duplicate_summary = {
                "duplicate_count": 0,
                "duplicate_percentage": 0.0,
                "sample_duplicates": []
            }
            self.results["duplicates"] = duplicate_summary
            return duplicate_summary

        duplicate_mask = self.df.duplicated()
        duplicate_count = int(duplicate_mask.sum())
        duplicate_percentage = (duplicate_count / total_rows) * 100 if total_rows > 0 else 0.0

        duplicate_summary = {
            "duplicate_count": duplicate_count,
            "duplicate_percentage": round(float(duplicate_percentage), 2)
        }

        if identify_records and duplicate_count > 0:
            # Extract first 5 duplicate rows as dictionaries for inspection
            sample_df = self.df[duplicate_mask].head(5)
            duplicate_summary["sample_duplicates"] = sample_df.to_dict(orient="records")
        else:
            duplicate_summary["sample_duplicates"] = []

        self.results["duplicates"] = duplicate_summary
        return duplicate_summary

    def profile_numerical(self) -> Dict[str, Dict[str, Any]]:
        """
        Profiles numerical columns, collecting mean, median, standard deviation,
        minimum, maximum, and quantiles (25%, 50%, 75%).

        Returns:
            Dict[str, Dict[str, Any]]: Descriptive statistics for each numeric column.
        """
        logger.info("Profiling numerical columns...")
        
        # Get numerical columns
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        numerical_summary: Dict[str, Dict[str, Any]] = {}

        if not numeric_cols:
            self.results["numerical"] = numerical_summary
            return numerical_summary

        # Compute descriptive statistics using pandas
        desc_df = self.df[numeric_cols].describe(percentiles=[0.25, 0.5, 0.75])
        
        for col in numeric_cols:
            series = self.df[col]
            # Handle standard metrics and custom counts
            numerical_summary[col] = {
                "count": int(desc_df.loc["count", col]),
                "mean": float(desc_df.loc["mean", col]) if pd.notna(desc_df.loc["mean", col]) else None,
                "std": float(desc_df.loc["std", col]) if pd.notna(desc_df.loc["std", col]) else None,
                "min": float(desc_df.loc["min", col]) if pd.notna(desc_df.loc["min", col]) else None,
                "q25": float(desc_df.loc["25%", col]) if pd.notna(desc_df.loc["25%", col]) else None,
                "median": float(desc_df.loc["50%", col]) if pd.notna(desc_df.loc["50%", col]) else None,
                "q75": float(desc_df.loc["75%", col]) if pd.notna(desc_df.loc["75%", col]) else None,
                "max": float(desc_df.loc["max", col]) if pd.notna(desc_df.loc["max", col]) else None,
                "skew": float(series.skew()) if pd.notna(series.skew()) else None,
                "kurtosis": float(series.kurtosis()) if pd.notna(series.kurtosis()) else None
            }

        self.results["numerical"] = numerical_summary
        return numerical_summary

    def _detect_casing_discrepancies(self, col: str) -> List[Dict[str, Any]]:
        """
        Helper method to find category values that differ only by leading/trailing 
        whitespace or capitalization (e.g. 'Yes', 'yes', ' yes ').
        """
        non_null_series = self.df[col].dropna().astype(str)
        unique_values = non_null_series.unique()
        
        # Group unique values by their normalized key (lowercase and stripped)
        normalized_groups: Dict[str, List[str]] = {}
        for val in unique_values:
            norm_key = val.strip().lower()
            normalized_groups.setdefault(norm_key, []).append(val)
        
        discrepancies = []
        for norm_key, variants in normalized_groups.items():
            if len(variants) > 1:
                # Calculate aggregate counts of variants
                variant_counts = non_null_series[non_null_series.isin(variants)].value_counts().to_dict()
                discrepancies.append({
                    "normalized_value": norm_key,
                    "variants": {str(k): int(v) for k, v in variant_counts.items()}
                })
        
        return discrepancies

    def _detect_spelling_discrepancies(self, col: str, threshold: float = 0.85) -> List[Dict[str, Any]]:
        """
        Helper method to find category values that have high spelling similarity
        using difflib.SequenceMatcher. Operates on unique values.
        """
        unique_vals = self.df[col].dropna().astype(str).unique().tolist()
        
        # If cardinality is too high, skip to avoid O(N^2) complexity
        if len(unique_vals) > 50 or len(unique_vals) < 2:
            return []

        spelling_alerts = []
        checked_pairs = set()

        for i in range(len(unique_vals)):
            for j in range(i + 1, len(unique_vals)):
                v1, v2 = unique_vals[i], unique_vals[j]
                
                # Skip if already normalized casing check would catch it
                if v1.strip().lower() == v2.strip().lower():
                    continue

                # Measure string similarity ratio
                ratio = difflib.SequenceMatcher(None, v1, v2).ratio()
                if ratio >= threshold:
                    pair_key = tuple(sorted([v1, v2]))
                    if pair_key not in checked_pairs:
                        checked_pairs.add(pair_key)
                        spelling_alerts.append({
                            "value1": v1,
                            "value2": v2,
                            "similarity_score": round(ratio, 3)
                        })

        return spelling_alerts

    def profile_categorical(self, max_freq_items: int = 10) -> Dict[str, Dict[str, Any]]:
        """
        Profiles categorical and object columns. Computes cardinality, most
        frequent values, frequency distributions, and checks for casing or 
        spelling inconsistencies.

        Args:
            max_freq_items (int): Max number of items to list in frequency distribution.

        Returns:
            Dict[str, Dict[str, Any]]: Categorical profile metrics.
        """
        logger.info("Profiling categorical columns...")
        
        # Get categorical and object columns
        cat_cols = self.df.select_dtypes(include=["object", "category", "bool"]).columns.tolist()
        categorical_summary: Dict[str, Dict[str, Any]] = {}

        for col in cat_cols:
            series = self.df[col]
            num_unique = int(series.nunique(dropna=True))
            
            # Retrieve value frequencies
            freq_dist = series.value_counts(dropna=True)
            most_frequent = freq_dist.index[0] if not freq_dist.empty else None
            most_frequent_count = int(freq_dist.iloc[0]) if not freq_dist.empty else 0
            
            # Format frequency distribution as a dictionary
            distribution_sample = {str(k): int(v) for k, v in freq_dist.head(max_freq_items).items()}

            # Inconsistency Checks
            casing_discrepancies = self._detect_casing_discrepancies(col)
            spelling_discrepancies = self._detect_spelling_discrepancies(col)

            categorical_summary[col] = {
                "num_unique": num_unique,
                "most_frequent_value": most_frequent,
                "most_frequent_count": most_frequent_count,
                "frequency_distribution": distribution_sample,
                "casing_discrepancies": casing_discrepancies,
                "spelling_discrepancies": spelling_discrepancies,
                "has_discrepancies": len(casing_discrepancies) > 0 or len(spelling_discrepancies) > 0
            }

        self.results["categorical"] = categorical_summary
        return categorical_summary

    def check_validity(self, rules: Dict[str, Any]) -> Dict[str, Any]:
        """
        Validates column contents against configurable business logic rules.

        Supported Rules:
            - `min_value` (numeric): Lower bound limit.
            - `max_value` (numeric): Upper bound limit.
            - `allow_future_dates` (bool): If False, flags dates ahead of now.
            - `regex` (str): Regular expression pattern validation.
            - `check_empty_strings` (bool): Checks for blank/whitespace strings.

        Returns:
            Dict[str, Any]: Mapping of column names to failed rule counts and lists of violations.
        """
        logger.info("Executing configurable data validity checks...")
        validity_report: Dict[str, Any] = {}
        total_rows = len(self.df)

        if total_rows == 0:
            self.results["validity"] = validity_report
            return validity_report

        # Loop through columns and apply their corresponding rules
        for col, col_rules in rules.items():
            if col not in self.df.columns:
                logger.warning(f"Validity check column '{col}' not found in DataFrame. Skipping.")
                continue

            violations = []
            series = self.df[col]

            for rule_name, rule_value in col_rules.items():
                if rule_name == "min_value":
                    invalid_mask = pd.to_numeric(series, errors="coerce") < rule_value
                    invalid_indices = self.df.index[invalid_mask & series.notna()].tolist()
                    for idx in invalid_indices:
                        violations.append({
                            "index": idx,
                            "value": series.loc[idx],
                            "reason": f"Value less than minimum threshold of {rule_value}"
                        })

                elif rule_name == "max_value":
                    invalid_mask = pd.to_numeric(series, errors="coerce") > rule_value
                    invalid_indices = self.df.index[invalid_mask & series.notna()].tolist()
                    for idx in invalid_indices:
                        violations.append({
                            "index": idx,
                            "value": series.loc[idx],
                            "reason": f"Value greater than maximum threshold of {rule_value}"
                        })

                elif rule_name == "allow_future_dates" and rule_value is False:
                    parsed_dates = pd.to_datetime(series, errors="coerce")
                    today_now = datetime.now()
                    invalid_mask = parsed_dates > today_now
                    invalid_indices = self.df.index[invalid_mask & series.notna()].tolist()
                    for idx in invalid_indices:
                        violations.append({
                            "index": idx,
                            "value": str(series.loc[idx]),
                            "reason": f"Date is in the future relative to execution time ({today_now.date()})"
                        })

                elif rule_name == "regex":
                    pattern = re.compile(str(rule_value))
                    invalid_mask = series.dropna().astype(str).apply(lambda x: not bool(pattern.match(x)))
                    invalid_indices = series.dropna()[invalid_mask].index.tolist()
                    for idx in invalid_indices:
                        violations.append({
                            "index": idx,
                            "value": str(series.loc[idx]),
                            "reason": f"Value does not match expected format pattern '{rule_value}'"
                        })

                elif rule_name == "check_empty_strings" and rule_value is True:
                    stripped_series = series.dropna().astype(str).str.strip()
                    invalid_mask = stripped_series == ""
                    invalid_indices = series.dropna()[invalid_mask].index.tolist()
                    for idx in invalid_indices:
                        violations.append({
                            "index": idx,
                            "value": repr(series.loc[idx]),
                            "reason": "String is empty or consists of only whitespace characters"
                        })

            if violations:
                validity_report[col] = {
                    "total_violations": len(violations),
                    "violation_percentage": round((len(violations) / total_rows) * 100, 2),
                    "sample_violations": violations[:5]  # Report top 5 sample violations to keep JSON small
                }

        self.results["validity"] = validity_report
        return validity_report

    def detect_outliers(self) -> Dict[str, Dict[str, Any]]:
        """
        Uses the Interquartile Range (IQR) method to identify outliers in numeric columns.
        Report contains outlier count, percentage, and outlier boundary ranges.

        Returns:
            Dict[str, Dict[str, Any]]: Outlier statistics per numeric column.
        """
        logger.info("Detecting numerical outliers using IQR method...")
        
        numeric_cols = self.df.select_dtypes(include=[np.number]).columns.tolist()
        outlier_summary: Dict[str, Dict[str, Any]] = {}
        total_rows = len(self.df)

        if total_rows == 0:
            self.results["outliers"] = outlier_summary
            return outlier_summary

        for col in numeric_cols:
            series = self.df[col].dropna()
            if series.empty:
                continue

            q25 = series.quantile(0.25)
            q75 = series.quantile(0.75)
            iqr = q75 - q25
            
            lower_bound = q25 - 1.5 * iqr
            upper_bound = q75 + 1.5 * iqr

            outliers_mask = (series < lower_bound) | (series > upper_bound)
            outlier_count = int(outliers_mask.sum())
            outlier_percentage = (outlier_count / total_rows) * 100 if total_rows > 0 else 0.0

            outlier_summary[col] = {
                "outlier_count": outlier_count,
                "outlier_percentage": round(float(outlier_percentage), 2),
                "lower_bound": float(lower_bound),
                "upper_bound": float(upper_bound),
                "iqr": float(iqr)
            }

        self.results["outliers"] = outlier_summary
        return outlier_summary

    def assess_quality(self) -> List[Dict[str, Any]]:
        """
        Performs automated quality assessment check relative to common data standards:
        - Columns with missing values > 30%.
        - Row duplication percentage > 5%.
        - Redundant columns (only one unique value).
        - High-cardinality categorical columns (unique count > 50% of records, excluding keys/IDs).
        - Numerical columns containing negative values when suspicious.
        - Numeric columns with high outlier density (>10% outliers).

        Returns:
            List[Dict[str, Any]]: List of generated alerts detailing data quality issues.
        """
        logger.info("Running quality assessment gates...")
        alerts = []

        overview = self.results.get("overview", self.profile_overview())
        missing = self.results.get("missing_values", self.profile_missing_values())
        duplicates = self.results.get("duplicates", self.profile_duplicates())
        categorical = self.results.get("categorical", self.profile_categorical())
        outliers = self.results.get("outliers", self.detect_outliers())
        validity = self.results.get("validity", {})

        total_rows = overview["num_rows"]

        # 1. Missing Values check
        for m in missing:
            if m["null_percentage"] > 30.0:
                alerts.append({
                    "type": "HIGH_MISSING_VALUES",
                    "severity": "CRITICAL",
                    "column": m["column"],
                    "message": f"Column contains {m['null_percentage']}% missing values (exceeds 30% limit)."
                })

        # 2. Duplicate Check
        if duplicates["duplicate_percentage"] > 5.0:
            alerts.append({
                "type": "HIGH_DUPLICATE_RATE",
                "severity": "WARNING",
                "column": "Dataset",
                "message": f"Dataset contains {duplicates['duplicate_percentage']}% duplicate rows (exceeds 5% limit)."
            })

        # 3. Columns with only one unique value (redundant columns)
        for col, stats in categorical.items():
            if stats["num_unique"] == 1:
                alerts.append({
                    "type": "REDUNDANT_COLUMN",
                    "severity": "WARNING",
                    "column": col,
                    "message": "Column contains only 1 unique value. It offers no variance."
                })

        # 4. High-cardinality check (potential ID variables that aren't marked as IDs)
        for col, stats in categorical.items():
            if not col.lower().endswith("id") and total_rows > 0:
                cardinality_ratio = stats["num_unique"] / total_rows
                if cardinality_ratio > 0.5:
                    alerts.append({
                        "type": "HIGH_CARDINALITY",
                        "severity": "WARNING",
                        "column": col,
                        "message": f"High cardinality categorical column: {stats['num_unique']} unique values in {total_rows} rows (ratio {cardinality_ratio:.2f})."
                    })

        # 5. Outliers and Suspicious numeric ranges check
        for col, stats in outliers.items():
            if stats["outlier_percentage"] > 10.0:
                alerts.append({
                    "type": "HIGH_OUTLIER_DENSITY",
                    "severity": "WARNING",
                    "column": col,
                    "message": f"Numerical column contains high outlier rate: {stats['outlier_percentage']}% outliers (exceeds 10% limit)."
                })

        # 6. Validity violations check
        for col, stats in validity.items():
            if stats["total_violations"] > 0:
                alerts.append({
                    "type": "VALIDITY_VIOLATIONS",
                    "severity": "CRITICAL",
                    "column": col,
                    "message": f"Column violated active validity rules in {stats['total_violations']} records ({stats['violation_percentage']}%)."
                })

        self.results["quality_assessment"] = alerts
        return alerts

    def run_all(self, validity_rules: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Executes the entire profiling pipeline sequentially.

        Args:
            validity_rules (Optional[Dict[str, Any]]): Config rules dict for validity.

        Returns:
            Dict[str, Any]: Consolidated profiling metrics output.
        """
        logger.info("Initializing full profiling run...")
        
        self.profile_overview()
        self.profile_missing_values()
        self.profile_duplicates(identify_records=True)
        self.profile_numerical()
        self.profile_categorical()
        
        if validity_rules:
            self.check_validity(validity_rules)
        else:
            self.results["validity"] = {}
            
        self.detect_outliers()
        self.assess_quality()

        logger.info("Profiling pipeline run complete.")
        return self.results

    def export_report(self, output_dir: str, base_name: str = "profiling_report", formats: List[str] = None) -> List[str]:
        """
        Exports the generated profile results to multiple output formats (JSON, CSV, Excel).

        Args:
            output_dir (str): Directory where the files will be saved.
            base_name (str): Core name of files.
            formats (List[str]): List containing 'json', 'csv', 'excel'. Defaults to all.

        Returns:
            List[str]: Paths to the generated export files.
        """
        if not self.results:
            logger.warning("No profiling results found. Running profiling before export.")
            self.run_all()

        if formats is None:
            formats = ["json", "csv", "excel"]

        os.makedirs(output_dir, exist_ok=True)
        saved_paths = []

        # 1. JSON Export
        if "json" in formats:
            json_path = os.path.join(output_dir, f"{base_name}.json")
            try:
                with open(json_path, "w", encoding="utf-8") as f:
                    json.dump(self.results, f, indent=4, cls=ProfilerJSONEncoder)
                logger.info(f"Saved profiling report as JSON: {json_path}")
                saved_paths.append(json_path)
            except Exception as e:
                logger.error(f"JSON export failed: {e}")

        # 2. CSV Export
        if "csv" in formats:
            csv_path = os.path.join(output_dir, f"{base_name}.csv")
            try:
                flat_data = []
                overview = self.results.get("overview", {})
                missing = {x["column"]: x for x in self.results.get("missing_values", [])}
                numerical = self.results.get("numerical", {})
                categorical = self.results.get("categorical", {})
                outliers = self.results.get("outliers", {})
                
                for col in overview.get("column_names", []):
                    dtype = overview.get("dtypes", {}).get(col, "unknown")
                    null_count = missing.get(col, {}).get("null_count", 0)
                    null_pct = missing.get(col, {}).get("null_percentage", 0.0)
                    
                    row_metrics = {
                        "column_name": col,
                        "data_type": dtype,
                        "null_count": null_count,
                        "null_percentage": null_pct,
                        "is_numeric": col in numerical,
                        "is_categorical": col in categorical
                    }
                    
                    if col in numerical:
                        row_metrics.update({
                            "mean": numerical[col].get("mean"),
                            "median": numerical[col].get("median"),
                            "min": numerical[col].get("min"),
                            "max": numerical[col].get("max"),
                            "std": numerical[col].get("std"),
                            "outlier_count": outliers.get(col, {}).get("outlier_count", 0),
                            "outlier_percentage": outliers.get(col, {}).get("outlier_percentage", 0.0)
                        })
                    else:
                        row_metrics.update({
                            "mean": None, "median": None, "min": None, "max": None, "std": None,
                            "outlier_count": None, "outlier_percentage": None
                        })
                        
                    if col in categorical:
                        row_metrics.update({
                            "unique_values": categorical[col].get("num_unique"),
                            "most_frequent_value": categorical[col].get("most_frequent_value"),
                            "most_frequent_count": categorical[col].get("most_frequent_count")
                        })
                    else:
                        row_metrics.update({
                            "unique_values": None,
                            "most_frequent_value": None,
                            "most_frequent_count": None
                        })
                        
                    flat_data.append(row_metrics)
                    
                flat_df = pd.DataFrame(flat_data)
                flat_df.to_csv(csv_path, index=False)
                logger.info(f"Saved profiling report as CSV: {csv_path}")
                saved_paths.append(csv_path)
                
            except Exception as e:
                logger.error(f"CSV export failed: {e}")

        # 3. Excel Export
        if "excel" in formats:
            excel_path = os.path.join(output_dir, f"{base_name}.xlsx")
            try:
                with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
                    overview = self.results.get("overview", {})
                    overview_df = pd.DataFrame([
                        {"Metric": "Number of Rows", "Value": overview.get("num_rows")},
                        {"Metric": "Number of Columns", "Value": overview.get("num_columns")},
                        {"Metric": "Memory Footprint", "Value": overview.get("memory_usage")},
                        {"Metric": "Generated Timestamp", "Value": datetime.now().isoformat()}
                    ])
                    overview_df.to_excel(writer, sheet_name="Overview", index=False)

                    schema_df = pd.DataFrame([
                        {"Column Name": col, "Data Type": dtype}
                        for col, dtype in overview.get("dtypes", {}).items()
                    ])
                    schema_df.to_excel(writer, sheet_name="Schema", index=False)

                    missing_df = pd.DataFrame(self.results.get("missing_values", []))
                    missing_df.to_excel(writer, sheet_name="Missing Values", index=False)

                    dup = self.results.get("duplicates", {})
                    dup_df = pd.DataFrame([
                        {"Metric": "Duplicate Rows Count", "Value": dup.get("duplicate_count")},
                        {"Metric": "Duplicate Percentage (%)", "Value": dup.get("duplicate_percentage")}
                    ])
                    dup_df.to_excel(writer, sheet_name="Duplicates", index=False)

                    num_summary = self.results.get("numerical", {})
                    if num_summary:
                        num_df = pd.DataFrame.from_dict(num_summary, orient="index")
                        num_df.index.name = "column"
                        num_df.reset_index().to_excel(writer, sheet_name="Numerical Stats", index=False)

                    cat_summary = self.results.get("categorical", {})
                    if cat_summary:
                        cat_list = []
                        for col, stat in cat_summary.items():
                            cat_list.append({
                                "column": col,
                                "unique_values": stat.get("num_unique"),
                                "most_frequent_val": stat.get("most_frequent_value"),
                                "most_frequent_freq": stat.get("most_frequent_count"),
                                "has_discrepancies": stat.get("has_discrepancies")
                            })
                        cat_df = pd.DataFrame(cat_list)
                        cat_df.to_excel(writer, sheet_name="Categorical Stats", index=False)

                    outlier_summary = self.results.get("outliers", {})
                    if outlier_summary:
                        outlier_df = pd.DataFrame.from_dict(outlier_summary, orient="index")
                        outlier_df.index.name = "column"
                        outlier_df.reset_index().to_excel(writer, sheet_name="Outliers", index=False)

                    val_summary = self.results.get("validity", {})
                    val_rows = []
                    for col, stat in val_summary.items():
                        for item in stat.get("sample_violations", []):
                            val_rows.append({
                                "Column": col,
                                "Index": item.get("index"),
                                "Value": item.get("value"),
                                "Reason": item.get("reason"),
                                "Column Total Violations": stat.get("total_violations"),
                                "Column Violation Pct (%)": stat.get("violation_percentage")
                            })
                    val_df = pd.DataFrame(val_rows)
                    if val_df.empty:
                        val_df = pd.DataFrame(columns=["Column", "Index", "Value", "Reason"])
                    val_df.to_excel(writer, sheet_name="Validity Checks", index=False)

                    alerts = self.results.get("quality_assessment", [])
                    alerts_df = pd.DataFrame(alerts)
                    if alerts_df.empty:
                        alerts_df = pd.DataFrame(columns=["type", "severity", "column", "message"])
                    alerts_df.to_excel(writer, sheet_name="Quality Assessment", index=False)

                logger.info(f"Saved profiling report as Excel: {excel_path}")
                saved_paths.append(excel_path)
            except Exception as e:
                logger.error(f"Excel export failed: {e}")
        return saved_paths


# ----------------------------------------------------------------------
# Standalone Wrapper Functions for Direct Study Guide Alignment
# ----------------------------------------------------------------------

def profile_nulls_and_duplicates(df: pd.DataFrame) -> dict:
    """
    Computes null counts, null percentages per column, and exact duplicate row counts.

    Args:
        df (pd.DataFrame): Input dataset.

    Returns:
        dict: Containing null stats per column and exact duplicate counts.
    """
    profiler = DatasetProfiler(df)
    null_stats = profiler.profile_missing_values()
    dup_stats = profiler.profile_duplicates(identify_records=False)
    
    result = {}
    for item in null_stats:
        col = item["column"]
        result[col] = {
            "nulls": item["null_count"],
            "null_%": item["null_percentage"]
        }
    result["exact_duplicates"] = dup_stats["duplicate_count"]
    return result


def profile_numerical(df: pd.DataFrame) -> dict:
    """
    Profiles numerical columns to collect min, max, mean, and median stats.

    Args:
        df (pd.DataFrame): Input dataset.

    Returns:
        dict: Descriptive statistics for numerical columns.
    """
    profiler = DatasetProfiler(df)
    num_stats = profiler.profile_numerical()
    
    result = {}
    for col, stats in num_stats.items():
        result[col] = {
            "min": stats["min"],
            "max": stats["max"],
            "mean": round(stats["mean"], 2) if stats["mean"] is not None else None,
            "median": stats["median"]
        }
    return result


def identify_issues(df: pd.DataFrame, null_threshold: float = 30, dup_threshold: float = 5) -> list:
    """
    Identifies high null percentages and duplicate records beyond specified thresholds.

    Args:
        df (pd.DataFrame): Input dataset.
        null_threshold (float): Null percentage limit (defaults to 30%).
        dup_threshold (float): Duplicate percentage limit (defaults to 5%).

    Returns:
        list: Identified data quality issues and metadata.
    """
    profiler = DatasetProfiler(df)
    null_stats = profiler.profile_missing_values()
    dup_stats = profiler.profile_duplicates()
    
    issues = []
    for item in null_stats:
        if item["null_percentage"] > null_threshold:
            issues.append({
                "column": item["column"],
                "type": "High nulls",
                "value": f"{item['null_percentage']:.1f}%"
            })
            
    if dup_stats["duplicate_percentage"] > dup_threshold:
        issues.append({
            "type": "High duplicates",
            "value": f"{dup_stats['duplicate_percentage']:.1f}%"
        })
        
    return issues

