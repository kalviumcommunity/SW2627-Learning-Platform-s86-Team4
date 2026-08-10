import streamlit as st
import pandas as pd
import numpy as np
import os
import shutil
import json
import re
from datetime import datetime
import plotly.graph_objects as go
from sqlalchemy.orm import Session

# Import backend/database modules
from backend.database.db import SessionLocal
from backend.models.models import User, Dataset, DatasetMetadata
from backend.services.auth_service import get_password_hash, verify_password

# Import analytics modules
from analytics.utils import (
    parse_file_to_df, 
    generate_dataset_metadata, 
    clean_dataframe, 
    populate_db_tables_from_df
)
from analytics.analysis import (
    get_kpis, 
    get_course_performance, 
    get_search_analytics, 
    get_category_analysis, 
    get_time_trends, 
    get_business_insights,
    get_advanced_eda_metrics
)
from analytics.charts import (
    get_funnel_chart,
    get_category_bar_chart,
    get_time_line_chart,
    get_views_vs_enrollments_scatter,
    get_category_pie_chart,
    get_hourly_heatmap
)

# ----------------------------------------------------
# Configuration
# ----------------------------------------------------
st.set_page_config(
    page_title="CourseInsight – Course Analytics Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)

UPLOAD_DIR = "datasets/uploads"
os.makedirs(UPLOAD_DIR, exist_ok=True)

# Custom Premium Styling
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'Inter', sans-serif;
    }
    .metric-card {
        background-color: #ffffff;
        border: 1px solid #e2e8f0;
        border-radius: 12px;
        padding: 20px;
        box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05), 0 2px 4px -1px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s, box-shadow 0.2s;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 10px 15px -3px rgba(0, 0, 0, 0.05), 0 4px 6px -2px rgba(0, 0, 0, 0.05);
    }
    .metric-value {
        font-size: 28px;
        font-weight: 700;
        color: #1e1b4b;
        margin-bottom: 4px;
    }
    .metric-label {
        font-size: 13px;
        font-weight: 500;
        color: #64748b;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
    .insight-card {
        background-color: #f8fafc;
        border-left: 4px solid #4f46e5;
        border-radius: 4px;
        padding: 12px 16px;
        margin-bottom: 12px;
    }
</style>
""", unsafe_allow_html=True)

# Helper function to get database session
def get_db_session():
    db = SessionLocal()
    try:
        return db
    except Exception as e:
        st.error(f"Database connection error: {e}")
        return None

# Password Strength Check
def validate_password_strength(password: str):
    if len(password) < 8:
        return False, "Password must be at least 8 characters long."
    if not re.search(r"[A-Z]", password):
        return False, "Password must contain at least one uppercase letter."
    if not re.search(r"[a-z]", password):
        return False, "Password must contain at least one lowercase letter."
    if not re.search(r"\d", password):
        return False, "Password must contain at least one digit."
    if not re.search(r"[!@#$%^&*(),.?\":{}|<>]", password):
        return False, "Password must contain at least one special character (e.g. !@#$%^&*)."
    return True, ""

# ----------------------------------------------------
# Session State Initialization
# ----------------------------------------------------
if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "user_id" not in st.session_state:
    st.session_state.user_id = None
if "username" not in st.session_state:
    st.session_state.username = None
if "active_dataset_id" not in st.session_state:
    st.session_state.active_dataset_id = None
if "auth_view" not in st.session_state:
    st.session_state.auth_view = "home"

# ----------------------------------------------------
# Dataset Helper Functions
# ----------------------------------------------------
def seed_sample_dataset(db: Session, user_id: int):
    """Seeds the sample dataset for a user if they do not have one."""
    sample_path = "datasets/sample_dataset.csv"
    if not os.path.exists(sample_path):
        return None
    
    unique_filename = f"user_{user_id}_default_sample_dataset.csv"
    dest_path = os.path.join(UPLOAD_DIR, unique_filename)
    
    # If the user's specific sample file already exists on disk, we just verify DB entry
    if not os.path.exists(dest_path):
        shutil.copy(sample_path, dest_path)
        
    # Check if entry is in DB
    dataset = db.query(Dataset).filter(
        Dataset.uploaded_by_user_id == user_id,
        Dataset.filename == "sample_dataset.csv"
    ).first()
    
    if not dataset:
        try:
            df = pd.read_csv(dest_path)
            metadata = generate_dataset_metadata(df)
            
            dataset = Dataset(
                filename="sample_dataset.csv",
                filepath=dest_path,
                uploaded_by_user_id=user_id,
                row_count=metadata["row_count"],
                col_count=metadata["col_count"],
                is_active=True
            )
            db.add(dataset)
            db.commit()
            db.refresh(dataset)
            
            db_metadata = DatasetMetadata(
                dataset_id=dataset.id,
                columns_json=json.dumps(metadata["columns"]),
                duplicate_count=metadata["duplicate_count"],
                missing_count=metadata["missing_count"]
            )
            db.add(db_metadata)
            db.commit()
            
            populate_db_tables_from_df(db, dataset.id, df)
        except Exception as e:
            db.rollback()
            st.error(f"Error seeding sample dataset: {e}")
            return None
    return dataset

def set_active_dataset(db: Session, user_id: int, dataset_id: int):
    db.query(Dataset).filter(Dataset.uploaded_by_user_id == user_id).update({"is_active": False})
    dataset = db.query(Dataset).filter(Dataset.id == dataset_id, Dataset.uploaded_by_user_id == user_id).first()
    if dataset:
        dataset.is_active = True
        db.commit()
        # Repopulate tables for this dataset
        df = parse_file_to_df(dataset.filepath)
        populate_db_tables_from_df(db, dataset.id, df)
        st.session_state.active_dataset_id = dataset_id
        return True
    return False

# ----------------------------------------------------
# MAIN UI FLOW
# ----------------------------------------------------
db = get_db_session()

if not st.session_state.logged_in:
    if st.session_state.auth_view == "home":
        # Render Premium landing home page
        st.markdown("""
        <div style="text-align: center; padding: 2.5rem 0 1.5rem 0;">
            <h1 style="font-size: 3.5rem; font-weight: 800; color: #4f46e5; margin-bottom: 0.5rem; letter-spacing: -0.025em;">📊 CourseInsight</h1>
            <p style="font-size: 1.25rem; color: #475569; max-width: 800px; margin: 0 auto; line-height: 1.6; font-weight: 400;">
                Transform raw student activity logs into actionable business intelligence. Track course views, pinpoint enrollment drop-offs, and optimize conversion performance.
            </p>
        </div>
        """, unsafe_allow_html=True)
        
        # Navigation buttons layout
        col_btn1, col_btn2 = st.columns(2)
        with col_btn1:
            if st.button("🔑 Sign In to Dashboard", use_container_width=True, type="primary"):
                st.session_state.auth_view = "login"
                st.rerun()
        with col_btn2:
            if st.button("📝 Create an Account", use_container_width=True):
                st.session_state.auth_view = "register"
                st.rerun()
                
        st.markdown("<hr style='margin: 2rem 0; border-color: rgba(148, 163, 184, 0.15);'/>", unsafe_allow_html=True)
        
        # Details grid
        col_info1, col_info2 = st.columns(2)
        with col_info1:
            st.markdown("""
            ### 💡 What is CourseInsight?
            **CourseInsight** is a premium analytics platform built specifically for course creators, universities, and training administrators. 
            By parsing student logs (search terms, preview clicks, and signups), it builds a clear visualization of the user conversion pipeline.
            
            ### 📈 Key Benefits & Use Cases
            * **Funnel Visualization**: Instantly see where potential students drop off before completing enrollment.
            * **Interactive Explanatory Analysis**: Filter dashboards by category or individual courses to compare metrics.
            * **Clean Data Instantly**: Detect and handle duplicate records or missing cells with zero coding.
            * **Automated Recommendations**: Get rule-based actionable insights on low-performing categories and popular search terms.
            """)
            
        with col_info2:
            st.markdown("""
            ### ⚙️ How It Works
            
            1. **Secure Registration** 📝  
               Create an account in seconds. The platform automatically seeds your profile with a default sample dataset.
            
            2. **Manage Data Log Files** 📤  
               Upload your raw interaction logs (CSV or Excel). View and delete datasets, or swap the active file with a single click.
            
            3. **Run Cleaning Pipelines** 🧹  
               Preview column datatypes, null checks, and duplicate counts. Apply strategies to standardize or drop missing rows.
            
            4. **Analyze Insights & KPIs** 📊  
               View overall conversion metrics, correlation charts, outlier activities, and rolling averages, then export results to CSV.
            """)
            
    elif st.session_state.auth_view == "login":
        st.markdown("<h2 style='text-align: center; color: #4f46e5; margin-top: 2rem; margin-bottom: 0.5rem;'>🔑 Access Your Dashboard</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 1.5rem;'>Enter your credentials to enter the workspace</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1.6, 1])
        with col2:
            if st.button("⬅ Back to Home", use_container_width=True):
                st.session_state.auth_view = "home"
                st.rerun()
                
            st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
            with st.form("login_form"):
                st.markdown("<h4 style='margin-top: 0; margin-bottom: 1rem; color: #1e1b4b;'>Sign In</h4>", unsafe_allow_html=True)
                username = st.text_input("Username")
                password = st.text_input("Password", type="password")
                submit_login = st.form_submit_button("Sign In", use_container_width=True)
                
                if submit_login:
                    if not username or not password:
                        st.error("Please enter both username and password.")
                    else:
                        user = db.query(User).filter(User.username == username).first()
                        if user and verify_password(password, user.hashed_password):
                            st.session_state.logged_in = True
                            st.session_state.user_id = user.id
                            st.session_state.username = user.username
                            
                            # Seed and make active sample dataset if they don't have datasets
                            seed_sample_dataset(db, user.id)
                            active_ds = db.query(Dataset).filter(
                                Dataset.uploaded_by_user_id == user.id,
                                Dataset.is_active == True
                            ).first()
                            if active_ds:
                                st.session_state.active_dataset_id = active_ds.id
                            
                            st.success(f"Welcome back, {username}!")
                            st.rerun()
                        else:
                            st.error("Incorrect username or password.")
                            
    elif st.session_state.auth_view == "register":
        st.markdown("<h2 style='text-align: center; color: #4f46e5; margin-top: 2rem; margin-bottom: 0.5rem;'>📝 Create a Workspace</h2>", unsafe_allow_html=True)
        st.markdown("<p style='text-align: center; color: #64748b; margin-bottom: 1.5rem;'>Register to access your personal dashboard</p>", unsafe_allow_html=True)
        
        col1, col2, col3 = st.columns([1, 1.6, 1])
        with col2:
            if st.button("⬅ Back to Home", use_container_width=True):
                st.session_state.auth_view = "home"
                st.rerun()
                
            st.markdown("<div style='margin-top: 1rem;'></div>", unsafe_allow_html=True)
            with st.form("register_form"):
                st.markdown("<h4 style='margin-top: 0; margin-bottom: 1rem; color: #1e1b4b;'>Create Account</h4>", unsafe_allow_html=True)
                reg_username = st.text_input("Username")
                reg_email = st.text_input("Email")
                reg_password = st.text_input("Password (min 8 characters, uppercase, lowercase, digit, special)", type="password")
                submit_reg = st.form_submit_button("Create Account", use_container_width=True)
                
                if submit_reg:
                    if not reg_username or not reg_email or not reg_password:
                        st.error("All fields are required.")
                    else:
                        is_strong, err_msg = validate_password_strength(reg_password)
                        if not is_strong:
                            st.error(err_msg)
                        else:
                            # Check if user already exists
                            existing = db.query(User).filter(
                                (User.username == reg_username) | (User.email == reg_email)
                            ).first()
                            if existing:
                                st.error("Username or email already registered.")
                            else:
                                try:
                                    new_user = User(
                                        username=reg_username,
                                        email=reg_email,
                                        hashed_password=get_password_hash(reg_password)
                                    )
                                    db.add(new_user)
                                    db.commit()
                                    db.refresh(new_user)
                                    
                                    # Auto seed sample dataset
                                    seed_sample_dataset(db, new_user.id)
                                    
                                    st.success("Account created successfully! Redirecting you to Login...")
                                    st.session_state.auth_view = "login"
                                    st.rerun()
                                except Exception as e:
                                    db.rollback()
                                    st.error(f"Error creating account: {e}")

else:
    # ----------------------------------------------------
    # LOGGED IN DASHBOARD
    # ----------------------------------------------------
    
    # 1. Fetch current datasets
    user_datasets = db.query(Dataset).filter(Dataset.uploaded_by_user_id == st.session_state.user_id).all()
    
    # Auto-fallback session state active dataset if needed
    if not st.session_state.active_dataset_id and user_datasets:
        active_ds = next((d for d in user_datasets if d.is_active), user_datasets[0])
        st.session_state.active_dataset_id = active_ds.id
        set_active_dataset(db, st.session_state.user_id, active_ds.id)
    
    active_dataset = db.query(Dataset).filter(Dataset.id == st.session_state.active_dataset_id).first()
    
    # 2. Side Panel Configuration
    with st.sidebar:
        st.markdown(f"### 👋 Welcome, **{st.session_state.username}**")
        st.markdown("---")
        
        # Dataset Selection Dropdown
        if user_datasets:
            ds_names = [d.filename for d in user_datasets]
            active_index = next((i for i, d in enumerate(user_datasets) if d.id == st.session_state.active_dataset_id), 0)
            
            selected_ds_name = st.selectbox(
                "📂 Select Active Dataset",
                options=ds_names,
                index=active_index
            )
            
            # Update state if changed
            selected_ds = next((d for d in user_datasets if d.filename == selected_ds_name), None)
            if selected_ds and selected_ds.id != st.session_state.active_dataset_id:
                set_active_dataset(db, st.session_state.user_id, selected_ds.id)
                st.success(f"Switched to '{selected_ds_name}'")
                st.rerun()
        else:
            st.warning("No datasets available. Please upload one below or refresh.")
            
        st.markdown("---")
        
        # Quick logout
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.logged_in = False
            st.session_state.user_id = None
            st.session_state.username = None
            st.session_state.active_dataset_id = None
            st.rerun()

    # 3. Main Tabs Layout
    st.markdown("<h1 style='color: #1e1b4b; margin-bottom: 4px;'>📊 CourseInsight Platform</h1>", unsafe_allow_html=True)
    if active_dataset:
        st.markdown(f"<p style='color: #64748b; margin-top: 0;'>Active Dataset: <b>{active_dataset.filename}</b></p>", unsafe_allow_html=True)
    
    tab_dashboard, tab_clean, tab_advanced, tab_uploads = st.tabs([
        "📈 Analytics Dashboard", 
        "🧹 Data Cleaning & Preview", 
        "🔬 Advanced Stats & Insights", 
        "📤 Dataset Manager"
    ])
    
    # ----------------------------------------------------
    # TAB 1: ANALYTICS DASHBOARD
    # ----------------------------------------------------
    with tab_dashboard:
        if not active_dataset:
            st.info("No active dataset. Please upload one in the 'Dataset Manager' tab.")
        else:
            # 1. Filters
            # Load unique courses and categories for filters
            from backend.models.models import Category, CourseView, Enrollment
            
            # Fetch all categories available for this dataset
            categories = db.query(Category).filter(Category.dataset_id == active_dataset.id).all()
            cat_list = ["All Categories"] + [c.name for c in categories]
            
            # Fetch unique courses
            views_courses = db.query(CourseView.course_name).filter(CourseView.dataset_id == active_dataset.id).distinct().all()
            enroll_courses = db.query(Enrollment.course_name).filter(Enrollment.dataset_id == active_dataset.id).distinct().all()
            course_set = sorted(list(set([c[0] for c in views_courses + enroll_courses if c[0]])))
            course_list = ["All Courses"] + course_set
            
            col_filter1, col_filter2, col_filter3 = st.columns(3)
            with col_filter1:
                filter_cat = st.selectbox("Category Filter", cat_list)
            with col_filter2:
                filter_course = st.selectbox("Course Filter", course_list)
            with col_filter3:
                # We can do date range filter
                # Find min/max timestamp from db
                min_view = db.query(CourseView.timestamp).filter(CourseView.dataset_id == active_dataset.id).order_by(CourseView.timestamp.asc()).first()
                max_view = db.query(CourseView.timestamp).filter(CourseView.dataset_id == active_dataset.id).order_by(CourseView.timestamp.desc()).first()
                
                min_date = min_view[0].date() if min_view else datetime.today().date()
                max_date = max_view[0].date() if max_view else datetime.today().date()
                
                date_range = st.date_input("Date Range Filter", value=(min_date, max_date), min_value=min_date, max_value=max_date)
            
            # Parse filter params
            param_cat = None if filter_cat == "All Categories" else filter_cat
            # Map course name back to ID if we had an ID mapping, otherwise just filter by name
            # Let's map course name filter to course_id in SQL queries. 
            # We can find the course_id matching the course_name:
            param_course_id = None
            if filter_course != "All Courses":
                match = db.query(CourseView.course_id).filter(
                    CourseView.dataset_id == active_dataset.id,
                    CourseView.course_name == filter_course
                ).first()
                if match:
                    param_course_id = match[0]
                else:
                    match = db.query(Enrollment.course_id).filter(
                        Enrollment.dataset_id == active_dataset.id,
                        Enrollment.course_name == filter_course
                    ).first()
                    if match:
                        param_course_id = match[0]
                        
            start_str = None
            end_str = None
            if isinstance(date_range, tuple) and len(date_range) == 2:
                start_str = date_range[0].strftime("%Y-%m-%d")
                end_str = date_range[1].strftime("%Y-%m-%d")
            
            # Fetch KPIs
            kpis = get_kpis(db, active_dataset.id, category=param_cat, start_date=start_str, end_date=end_str, course_id=param_course_id)
            
            st.markdown("### 📊 Key Performance Indicators (KPIs)")
            col_kpi1, col_kpi2, col_kpi3, col_kpi4 = st.columns(4)
            
            with col_kpi1:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{kpis['total_searches']:,}</div>
                    <div class="metric-label">Total Searches</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col_kpi2:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{kpis['total_views']:,}</div>
                    <div class="metric-label">Course Views</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col_kpi3:
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{kpis['total_enrollments']:,}</div>
                    <div class="metric-label">Enrollments</div>
                </div>
                """, unsafe_allow_html=True)
                
            with col_kpi4:
                conv_val = f"{kpis['conversion_rate']:.2f}%" if kpis['conversion_rate'] > 0 else "0.00%"
                st.markdown(f"""
                <div class="metric-card">
                    <div class="metric-value">{conv_val}</div>
                    <div class="metric-label">Overall Conversion</div>
                </div>
                """, unsafe_allow_html=True)

            col_kpi5, col_kpi6, col_kpi7 = st.columns(3)
            with col_kpi5:
                st.markdown(f"""
                <div class="metric-card" style="margin-top: 15px;">
                    <div class="metric-value">{kpis['avg_views_per_course']:.1f}</div>
                    <div class="metric-label">Avg Views / Course</div>
                </div>
                """, unsafe_allow_html=True)
            with col_kpi6:
                st.markdown(f"""
                <div class="metric-card" style="margin-top: 15px;">
                    <div class="metric-value" style="font-size: 18px; line-height: 1.5; height: 42px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{kpis['highest_viewed_course'] or 'N/A'}">
                        {kpis['highest_viewed_course'] or 'N/A'}
                    </div>
                    <div class="metric-label">Highest Viewed Course</div>
                </div>
                """, unsafe_allow_html=True)
            with col_kpi7:
                st.markdown(f"""
                <div class="metric-card" style="margin-top: 15px;">
                    <div class="metric-value" style="font-size: 18px; line-height: 1.5; height: 42px; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;" title="{kpis['lowest_conversion_course'] or 'N/A'}">
                        {kpis['lowest_conversion_course'] or 'N/A'}
                    </div>
                    <div class="metric-label">Lowest Conversion Course</div>
                </div>
                """, unsafe_allow_html=True)

            st.markdown("---")
            st.markdown("### 📈 Data Visualizations")
            
            # Row 1 of charts
            col_chart1, col_chart2 = st.columns(2)
            with col_chart1:
                funnel_dict = get_funnel_chart(db, active_dataset.id, category=param_cat, start_date=start_str, end_date=end_str, course_id=param_course_id)
                st.plotly_chart(go.Figure(funnel_dict), use_container_width=True)
                
            with col_chart2:
                bar_dict = get_category_bar_chart(db, active_dataset.id, category=param_cat, start_date=start_str, end_date=end_str, course_id=param_course_id)
                st.plotly_chart(go.Figure(bar_dict), use_container_width=True)

            # Row 2 of charts
            col_chart3, col_chart4 = st.columns(2)
            with col_chart3:
                line_dict = get_time_line_chart(db, active_dataset.id, category=param_cat, start_date=start_str, end_date=end_str, course_id=param_course_id)
                st.plotly_chart(go.Figure(line_dict), use_container_width=True)
                
            with col_chart4:
                scatter_dict = get_views_vs_enrollments_scatter(db, active_dataset.id, category=param_cat, start_date=start_str, end_date=end_str, course_id=param_course_id)
                st.plotly_chart(go.Figure(scatter_dict), use_container_width=True)

            # Row 3 of charts
            col_chart5, col_chart6 = st.columns(2)
            with col_chart5:
                pie_dict = get_category_pie_chart(db, active_dataset.id, category=param_cat, start_date=start_str, end_date=end_str, course_id=param_course_id)
                st.plotly_chart(go.Figure(pie_dict), use_container_width=True)
                
            with col_chart6:
                heatmap_dict = get_hourly_heatmap(db, active_dataset.id, category=param_cat, start_date=start_str, end_date=end_str, course_id=param_course_id)
                st.plotly_chart(go.Figure(heatmap_dict), use_container_width=True)

    # ----------------------------------------------------
    # TAB 2: DATA CLEANING & PREVIEW
    # ----------------------------------------------------
    with tab_clean:
        if not active_dataset:
            st.info("No active dataset loaded.")
        else:
            meta = db.query(DatasetMetadata).filter(DatasetMetadata.dataset_id == active_dataset.id).first()
            
            st.markdown("### 📊 Dataset Overview")
            
            col_stat1, col_stat2, col_stat3, col_stat4 = st.columns(4)
            with col_stat1:
                st.metric("Total Rows", f"{active_dataset.row_count:,}")
            with col_stat2:
                st.metric("Total Columns", active_dataset.col_count)
            with col_stat3:
                st.metric("Duplicate Rows", f"{meta.duplicate_count:,}" if meta else "N/A")
            with col_stat4:
                st.metric("Missing Cell Count", f"{meta.missing_count:,}" if meta else "N/A")
                
            # Column metadata list
            if meta and meta.columns_json:
                st.markdown("#### 📂 Columns & Types")
                cols_data = json.loads(meta.columns_json)
                df_cols = pd.DataFrame(cols_data)
                # Rename columns for presentation
                df_cols = df_cols.rename(columns={
                    "name": "Column Name",
                    "type": "Data Type",
                    "missing_count": "Missing Value Count",
                    "unique_count": "Unique Value Count"
                })
                st.dataframe(df_cols, hide_index=True, use_container_width=True)
            
            # DataFrame preview
            try:
                df_preview = parse_file_to_df(active_dataset.filepath)
                st.markdown("#### 🔍 First 10 Rows Preview")
                st.dataframe(df_preview.head(10), use_container_width=True)
            except Exception as e:
                st.error(f"Error reading file preview: {e}")
                df_preview = None
            
            # Cleaning controls
            if df_preview is not None:
                st.markdown("---")
                st.markdown("### 🧹 Clean Your Dataset")
                
                with st.form("cleaning_form"):
                    strategy = st.selectbox(
                        "Missing Values Strategy",
                        options=["Drop rows with missing values", "Fill with default placeholders", "Fill NaN only"],
                        index=0
                    )
                    
                    remove_dups = st.checkbox("Remove duplicate rows", value=True)
                    stand_cols = st.checkbox("Standardize column values (Title Case categories & course names)", value=True)
                    
                    submit_cleaning = st.form_submit_button("🧹 Run Dataset Cleaning")
                    
                    if submit_cleaning:
                        # Translate strategy name
                        clean_strategy = "drop"
                        if strategy == "Fill with default placeholders":
                            clean_strategy = "fill_defaults"
                        elif strategy == "Fill NaN only":
                            clean_strategy = "fill_na"
                            
                        with st.spinner("Cleaning dataset and rebuilding tables..."):
                            try:
                                cleaned_df = clean_dataframe(
                                    df_preview,
                                    strategy=clean_strategy,
                                    remove_duplicates=remove_dups,
                                    standardize=stand_cols
                                )
                                
                                # Write to disk
                                ext = os.path.splitext(active_dataset.filepath)[1].lower()
                                if ext == '.csv':
                                    cleaned_df.to_csv(active_dataset.filepath, index=False)
                                else:
                                    cleaned_df.to_excel(active_dataset.filepath, index=False)
                                    
                                # Re-generate metadata
                                new_meta_info = generate_dataset_metadata(cleaned_df)
                                active_dataset.row_count = new_meta_info["row_count"]
                                active_dataset.col_count = new_meta_info["col_count"]
                                
                                # Update DB records
                                if meta:
                                    meta.columns_json = json.dumps(new_meta_info["columns"])
                                    meta.duplicate_count = new_meta_info["duplicate_count"]
                                    meta.missing_count = new_meta_info["missing_count"]
                                else:
                                    new_meta = DatasetMetadata(
                                        dataset_id=active_dataset.id,
                                        columns_json=json.dumps(new_meta_info["columns"]),
                                        duplicate_count=new_meta_info["duplicate_count"],
                                        missing_count=new_meta_info["missing_count"]
                                    )
                                    db.add(new_meta)
                                    
                                db.commit()
                                
                                # Repopulate analysis log tables
                                populate_db_tables_from_df(db, active_dataset.id, cleaned_df)
                                
                                st.success("Dataset cleaned and analysis database updated successfully!")
                                st.rerun()
                            except Exception as e:
                                db.rollback()
                                st.error(f"Cleaning failed: {e}")

    # ----------------------------------------------------
    # TAB 3: ADVANCED STATS & INSIGHTS
    # ----------------------------------------------------
    with tab_advanced:
        if not active_dataset:
            st.info("No active dataset loaded.")
        else:
            # 1. Advanced EDA Metrics
            st.markdown("### 🔬 Exploratory Data Analysis & Statistics")
            
            insights_data = get_advanced_eda_metrics(db, active_dataset.id)
            
            col_adv1, col_adv2 = st.columns(2)
            with col_adv1:
                st.markdown("#### 🔗 views & enrollments Correlation")
                corr_data = insights_data.get("correlation", {})
                corr_coef = corr_data.get("coefficient", 0.0)
                corr_strength = corr_data.get("strength", "No Data")
                st.metric("Pearson Correlation Coefficient", f"{corr_coef:.3f}")
                st.caption(f"**Relationship Strength**: {corr_strength}")
                st.markdown("""
                * **Values close to 1**: Strong positive correlation (more views = more enrollments).
                * **Values close to -1**: Strong negative correlation (more views = fewer enrollments).
                * **Values close to 0**: No linear correlation.
                """)
                
            with col_adv2:
                st.markdown("#### 📉 Time-Series Outliers")
                outliers = insights_data.get("anomalous_outliers", [])
                if outliers:
                    df_outliers = pd.DataFrame(outliers)
                    df_outliers = df_outliers.rename(columns={
                        "date": "Date",
                        "views": "Views Count",
                        "status": "Anomaly Status",
                        "lower_bound": "Lower Bound (IQR)",
                        "upper_bound": "Upper Bound (IQR)"
                    })
                    st.dataframe(df_outliers, hide_index=True, use_container_width=True)
                else:
                    st.info("No anomalous outlier days detected in this dataset.")
                    
            st.markdown("---")
            st.markdown("### 💡 Business Insights & Action Items")
            
            # Rule-based business insights
            biz_insights = get_business_insights(db, active_dataset.id)
            if biz_insights:
                for ins in biz_insights:
                    st.markdown(f"""
                    <div class="insight-card">
                        <strong>{ins.get('title', 'Insight')}</strong><br/>
                        <span style="color: #475569; font-size: 14px;">{ins.get('description', '')}</span>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.info("Not enough data to calculate business insights.")
                
            # Sharing Option
            st.markdown("---")
            st.markdown("### 📧 Share Report")
            with st.form("share_report_form"):
                email = st.text_input("Recipient Email Address")
                submit_share = st.form_submit_button("Queue Report Email Delivery")
                if submit_share:
                    if not email:
                        st.error("Please enter a valid email address.")
                    else:
                        # Mock background task queueing
                        st.success(f"Dummy Email sent successfully to **{email}**!")

    # ----------------------------------------------------
    # TAB 4: DATASET MANAGER
    # ----------------------------------------------------
    with tab_uploads:
        st.markdown("### 📤 Upload New Dataset")
        uploaded_file = st.file_uploader("Upload CSV or Excel dataset", type=["csv", "xlsx", "xls"])
        
        if uploaded_file is not None:
            # Check if this file name already exists in user's records to prevent conflict
            existing_file = db.query(Dataset).filter(
                Dataset.uploaded_by_user_id == st.session_state.user_id,
                Dataset.filename == uploaded_file.name
            ).first()
            
            if existing_file:
                st.warning(f"File '{uploaded_file.name}' already exists. Uploading will save it as a new version.")
                
            if st.button("🚀 Upload & Analyze Dataset", use_container_width=True):
                # Save file
                timestamp_str = datetime.now().strftime("%Y%m%d%H%M%S")
                unique_filename = f"user_{st.session_state.user_id}_{timestamp_str}_{uploaded_file.name}"
                filepath = os.path.join(UPLOAD_DIR, unique_filename)
                
                try:
                    with open(filepath, "wb") as f:
                        f.write(uploaded_file.getbuffer())
                        
                    # Parse and verify
                    df = parse_file_to_df(filepath)
                    metadata = generate_dataset_metadata(df)
                    
                    # Create DB entries
                    new_ds = Dataset(
                        filename=uploaded_file.name,
                        filepath=filepath,
                        uploaded_by_user_id=st.session_state.user_id,
                        row_count=metadata["row_count"],
                        col_count=metadata["col_count"],
                        is_active=False
                    )
                    db.add(new_ds)
                    db.commit()
                    db.refresh(new_ds)
                    
                    db_metadata = DatasetMetadata(
                        dataset_id=new_ds.id,
                        columns_json=json.dumps(metadata["columns"]),
                        duplicate_count=metadata["duplicate_count"],
                        missing_count=metadata["missing_count"]
                    )
                    db.add(db_metadata)
                    db.commit()
                    
                    # Make it active automatically
                    set_active_dataset(db, st.session_state.user_id, new_ds.id)
                    
                    st.success(f"Successfully uploaded and activated '{uploaded_file.name}'!")
                    st.rerun()
                except Exception as e:
                    db.rollback()
                    if os.path.exists(filepath):
                        os.remove(filepath)
                    st.error(f"Failed to process uploaded file: {e}")
                    
        st.markdown("---")
        st.markdown("### 🗂 Your Uploaded Datasets")
        
        # Reload dataset list
        user_datasets = db.query(Dataset).filter(Dataset.uploaded_by_user_id == st.session_state.user_id).all()
        
        if user_datasets:
            for ds in user_datasets:
                col_name, col_rows, col_status, col_actions = st.columns([3, 2, 2, 3])
                
                with col_name:
                    st.markdown(f"**{ds.filename}**")
                    st.caption(f"Uploaded: {ds.uploaded_at.strftime('%Y-%m-%d %H:%M')}")
                with col_rows:
                    st.markdown(f"Rows: **{ds.row_count:,}**")
                    st.caption(f"Cols: {ds.col_count}")
                with col_status:
                    if ds.is_active:
                        st.markdown("🟢 **Active**")
                    else:
                        st.markdown("⚪ Inactive")
                with col_actions:
                    col_act1, col_act2, col_act3 = st.columns(3)
                    with col_act1:
                        if not ds.is_active:
                            if st.button("🔌 Active", key=f"act_{ds.id}"):
                                set_active_dataset(db, st.session_state.user_id, ds.id)
                                st.success(f"Activated {ds.filename}")
                                st.rerun()
                    with col_act2:
                        # Delete action
                        if st.button("🗑️ Delete", key=f"del_{ds.id}"):
                            # If active, set session state active_dataset_id to None
                            if ds.is_active:
                                st.session_state.active_dataset_id = None
                                
                            # Delete file
                            if os.path.exists(ds.filepath):
                                try:
                                    os.remove(ds.filepath)
                                except Exception:
                                    pass
                            db.delete(ds)
                            db.commit()
                            st.success(f"Deleted {ds.filename}")
                            st.rerun()
                    with col_act3:
                        # Export / Download dataset
                        try:
                            df_export = parse_file_to_df(ds.filepath)
                            csv_data = df_export.to_csv(index=False).encode('utf-8')
                            st.download_button(
                                label="📥 Export",
                                data=csv_data,
                                file_name=f"export_{ds.filename}",
                                mime="text/csv",
                                key=f"exp_{ds.id}"
                            )
                        except Exception as e:
                            st.error("Export error")
                st.markdown("<hr style='margin: 8px 0; border-color: rgba(0,0,0,0.05);'/>", unsafe_allow_html=True)
        else:
            st.info("You haven't uploaded any datasets yet.")
            
# Close DB session on script exit
if db:
    db.close()
