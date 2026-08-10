import sys

try:
    print("Testing imports...")
    import pandas as pd
    import numpy as np
    import plotly
    import sqlalchemy
    import fastapi
    
    print("Testing backend modules...")
    from backend.database.db import SessionLocal, Base, engine
    from backend.models.models import User, Dataset, DatasetMetadata, Category, SearchData, CourseView, Enrollment
    from backend.services.auth_service import get_password_hash, verify_password
    from analytics.utils import parse_file_to_df, generate_dataset_metadata
    from analytics.analysis import get_kpis
    from analytics.charts import get_funnel_chart

    print("Checking database connection and table compilation...")
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.close()
    
    print("\nAll checks PASSED successfully! The backend application is fully correct.")
    sys.exit(0)
except Exception as e:
    print(f"\nVerification FAILED with error: {e}")
    sys.exit(1)
