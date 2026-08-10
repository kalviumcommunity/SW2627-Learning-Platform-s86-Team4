import pandas as pd
import numpy as np
import os
import json
from datetime import datetime
from sqlalchemy.orm import Session
from backend.models.models import Dataset, DatasetMetadata, Category, SearchData, CourseView, Enrollment

# Create directories if not exists
os.makedirs("datasets/uploads", exist_ok=True)

def parse_file_to_df(filepath: str) -> pd.DataFrame:
    """Parses a CSV or Excel file into a pandas DataFrame."""
    ext = os.path.splitext(filepath)[1].lower()
    if ext == '.csv':
        df = pd.read_csv(filepath)
    elif ext in ['.xls', '.xlsx']:
        df = pd.read_excel(filepath)
    else:
        raise ValueError(f"Unsupported file extension: {ext}")
    return df

def generate_dataset_metadata(df: pd.DataFrame) -> dict:
    """Generates preview metadata (rows, columns, unique values, missing values, duplicates)."""
    row_count = len(df)
    col_count = len(df.columns)
    
    # Calculate duplicate count
    duplicate_count = int(df.duplicated().sum())
    
    # Calculate missing values count
    missing_count = int(df.isna().sum().sum() + (df == "").sum().sum())
    
    columns_info = []
    for col in df.columns:
        # Standardize datatype names
        col_type = str(df[col].dtype)
        # Unique values
        unique_vals = int(df[col].nunique())
        # Missing values in this column
        missing_in_col = int(df[col].isna().sum() + (df[col] == "").sum())
        
        columns_info.append({
            "name": col,
            "type": col_type,
            "missing_count": missing_in_col,
            "unique_count": unique_vals
        })
        
    return {
        "row_count": row_count,
        "col_count": col_count,
        "duplicate_count": duplicate_count,
        "missing_count": missing_count,
        "columns": columns_info
    }

def clean_dataframe(df: pd.DataFrame, strategy: str = "drop", remove_duplicates: bool = True, standardize: bool = True) -> pd.DataFrame:
    """Cleans a DataFrame based on user strategy."""
    df_clean = df.copy()
    
    # Remove duplicates
    if remove_duplicates:
        df_clean = df_clean.drop_duplicates()
        
    # Handle missing values
    # We only care about missing values in vital columns: action, user_id, timestamp, course_id, course_name, category
    vital_cols = [c for c in ["action", "user_id", "timestamp", "course_id", "course_name", "category"] if c in df_clean.columns]
    
    if strategy == "drop":
        # Drop rows where any vital column is empty
        for col in vital_cols:
            df_clean = df_clean[df_clean[col].notna() & (df_clean[col] != "")]
    elif strategy == "fill_defaults":
        # Fill missing values with default placeholders
        defaults = {
            "search_keyword": "unknown",
            "course_id": "C_UNKNOWN",
            "course_name": "Unknown Course",
            "category": "General",
            "user_id": "U_UNKNOWN",
            "action": "view"
        }
        for col in df_clean.columns:
            if col in defaults:
                df_clean[col] = df_clean[col].fillna(defaults[col]).replace("", defaults[col])
    elif strategy == "fill_na":
        # Just simple fillna with empty string or forward fill
        df_clean = df_clean.fillna("").replace(np.nan, "")
        
    # Standardize column values (Title Case for course names and categories)
    if standardize:
        if "course_name" in df_clean.columns:
            # fillna first, convert to string
            df_clean["course_name"] = df_clean["course_name"].fillna("").astype(str).apply(
                lambda x: x.title() if x else ""
            )
        if "category" in df_clean.columns:
            df_clean["category"] = df_clean["category"].fillna("").astype(str).apply(
                lambda x: x.title() if x else ""
            )
        if "action" in df_clean.columns:
            df_clean["action"] = df_clean["action"].fillna("").astype(str).str.lower()
            
    return df_clean

def populate_db_tables_from_df(db: Session, dataset_id: int, df: pd.DataFrame):
    """Populates categories, searches, views, and enrollments tables from a DataFrame."""
    # 1. Clear existing database logs for this dataset
    db.query(Category).filter(Category.dataset_id == dataset_id).delete()
    db.query(SearchData).filter(SearchData.dataset_id == dataset_id).delete()
    db.query(CourseView).filter(CourseView.dataset_id == dataset_id).delete()
    db.query(Enrollment).filter(Enrollment.dataset_id == dataset_id).delete()
    db.commit()
    
    # 2. Extract categories
    if "category" in df.columns:
        cats = df["category"].dropna().unique()
        for cat in cats:
            if str(cat).strip() != "":
                db.add(Category(dataset_id=dataset_id, name=str(cat).strip()))
        db.commit()
        
    # 3. Import logs
    # To optimize insertion, we can batch insert
    searches_batch = []
    views_batch = []
    enrolls_batch = []
    
    for _, row in df.iterrows():
        action = str(row.get("action", "")).strip().lower()
        if action in ["view", "course_view", "click", "page_view"]:
            action = "view"
        elif action in ["enroll", "enrollment", "signup", "sign_up", "purchase"]:
            action = "enroll"
        elif action in ["search", "query"]:
            action = "search"
        ts_val = row.get("timestamp", None)
        
        # Parse timestamp
        if pd.isna(ts_val) or str(ts_val).strip() == "":
            continue
            
        try:
            ts = pd.to_datetime(ts_val).to_pydatetime()
        except Exception:
            # Fallback to current time if parsing fails
            ts = datetime.utcnow()
            
        user_id = str(row.get("user_id", "U_UNKNOWN")).strip()
        search_kw = str(row.get("search_keyword", "")) if not pd.isna(row.get("search_keyword", "")) else ""
        course_id = str(row.get("course_id", "")) if not pd.isna(row.get("course_id", "")) else ""
        course_name = str(row.get("course_name", "")) if not pd.isna(row.get("course_name", "")) else ""
        category = str(row.get("category", "General")) if not pd.isna(row.get("category", "")) else "General"
        
        if action == "search":
            searches_batch.append(SearchData(
                dataset_id=dataset_id,
                timestamp=ts,
                user_id=user_id,
                search_keyword=search_kw,
                course_id=course_id if course_id else None
            ))
        elif action == "view":
            views_batch.append(CourseView(
                dataset_id=dataset_id,
                timestamp=ts,
                user_id=user_id,
                course_id=course_id,
                course_name=course_name,
                category=category,
                search_keyword=search_kw
            ))
        elif action == "enroll":
            enrolls_batch.append(Enrollment(
                dataset_id=dataset_id,
                timestamp=ts,
                user_id=user_id,
                course_id=course_id,
                course_name=course_name,
                category=category,
                search_keyword=search_kw
            ))
            
    # Bulk insert
    if searches_batch:
        db.bulk_save_objects(searches_batch)
    if views_batch:
        db.bulk_save_objects(views_batch)
    if enrolls_batch:
        db.bulk_save_objects(enrolls_batch)
        
    db.commit()
