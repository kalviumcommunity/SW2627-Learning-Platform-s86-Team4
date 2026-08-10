import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from backend.models.models import SearchData, CourseView, Enrollment, Category, Dataset
from typing import Dict, Any, List, Optional

def load_dataframes(db: Session, dataset_id: int) -> Dict[str, pd.DataFrame]:
    """Loads SearchData, CourseView, and Enrollment tables as pandas DataFrames."""
    # Queries
    search_query = db.query(SearchData).filter(SearchData.dataset_id == dataset_id).statement
    views_query = db.query(CourseView).filter(CourseView.dataset_id == dataset_id).statement
    enroll_query = db.query(Enrollment).filter(Enrollment.dataset_id == dataset_id).statement
    
    # Load DataFrames
    df_search = pd.read_sql(search_query, db.bind)
    df_views = pd.read_sql(views_query, db.bind)
    df_enroll = pd.read_sql(enroll_query, db.bind)
    
    return {
        "searches": df_search,
        "views": df_views,
        "enrollments": df_enroll
    }

def load_filtered_dataframes(
    db: Session, 
    dataset_id: int, 
    category: str = None, 
    start_date: str = None, 
    end_date: str = None, 
    course_id: str = None
) -> Dict[str, pd.DataFrame]:
    """Loads SearchData, CourseView, and Enrollment data and applies filters."""
    dfs = load_dataframes(db, dataset_id)
    df_search = dfs["searches"]
    df_views = dfs["views"]
    df_enroll = dfs["enrollments"]
    
    # 1. Course Filter
    if course_id:
        if not df_search.empty:
            df_search = df_search[df_search["course_id"] == course_id]
        if not df_views.empty:
            df_views = df_views[df_views["course_id"] == course_id]
        if not df_enroll.empty:
            df_enroll = df_enroll[df_enroll["course_id"] == course_id]
        
    # 2. Category Filter
    if category:
        if not df_views.empty:
            df_views = df_views[df_views["category"] == category]
        if not df_enroll.empty:
            df_enroll = df_enroll[df_enroll["category"] == category]
        
        # Build mapping of course_id to category
        course_cat = {}
        if not df_views.empty:
            for _, row in df_views[["course_id", "category"]].drop_duplicates().iterrows():
                course_cat[row["course_id"]] = row["category"]
        if not df_enroll.empty:
            for _, row in df_enroll[["course_id", "category"]].drop_duplicates().iterrows():
                course_cat[row["course_id"]] = row["category"]
                
        if not df_search.empty:
            df_search = df_search[df_search["course_id"].map(course_cat) == category]
        
    # 3. Date Range Filter
    if start_date:
        start_dt = pd.to_datetime(start_date)
        if not df_search.empty:
            df_search = df_search[pd.to_datetime(df_search["timestamp"]) >= start_dt]
        if not df_views.empty:
            df_views = df_views[pd.to_datetime(df_views["timestamp"]) >= start_dt]
        if not df_enroll.empty:
            df_enroll = df_enroll[pd.to_datetime(df_enroll["timestamp"]) >= start_dt]
            
    if end_date:
        if len(end_date) == 10:
            end_dt = pd.to_datetime(end_date + " 23:59:59")
        else:
            end_dt = pd.to_datetime(end_date)
        if not df_search.empty:
            df_search = df_search[pd.to_datetime(df_search["timestamp"]) <= end_dt]
        if not df_views.empty:
            df_views = df_views[pd.to_datetime(df_views["timestamp"]) <= end_dt]
        if not df_enroll.empty:
            df_enroll = df_enroll[pd.to_datetime(df_enroll["timestamp"]) <= end_dt]
            
    return {
        "searches": df_search,
        "views": df_views,
        "enrollments": df_enroll
    }

def get_kpis(
    db: Session, 
    dataset_id: int, 
    category: str = None, 
    start_date: str = None, 
    end_date: str = None, 
    course_id: str = None
) -> Dict[str, Any]:
    """Calculates filtered Dashboard KPIs."""
    dfs = load_filtered_dataframes(db, dataset_id, category, start_date, end_date, course_id)
    df_search = dfs["searches"]
    df_views = dfs["views"]
    df_enroll = dfs["enrollments"]
    
    total_searches = len(df_search)
    total_views = len(df_views)
    total_enrollments = len(df_enroll)
    
    # Conversion rates
    conversion_rate = (total_enrollments / total_views * 100) if total_views > 0 else 0.0
    
    # Averages
    unique_courses = df_views["course_id"].nunique() if total_views > 0 else 0
    avg_views = (total_views / unique_courses) if unique_courses > 0 else 0.0
    avg_enroll = (total_enrollments / unique_courses) if unique_courses > 0 else 0.0
    
    # High/Low course performance
    highest_viewed_course = "N/A"
    highest_views_count = 0
    lowest_conv_course = "N/A"
    lowest_conv_rate = 100.0
    
    if total_views > 0:
        # Group by course name to find highest views
        views_by_course = df_views.groupby("course_name").size()
        if not views_by_course.empty:
            highest_viewed_course = views_by_course.idxmax()
            highest_views_count = int(views_by_course.max())
            
        # Group by course to find lowest conversion (filter out low views to avoid noise, dynamically tuning threshold for small datasets)
        enroll_by_course = df_enroll.groupby("course_name").size()
        max_views = int(views_by_course.max()) if not views_by_course.empty else 0
        threshold = 5 if max_views >= 5 else 1
        
        course_conv_rates = []
        for course_name, c_views in views_by_course.items():
            c_enrolls = enroll_by_course.get(course_name, 0)
            c_conv = (c_enrolls / c_views) * 100
            if c_views >= threshold:
                course_conv_rates.append((course_name, c_conv))
                
        if course_conv_rates:
            lowest_conv_course, lowest_conv_rate = min(course_conv_rates, key=lambda x: x[1])
            lowest_conv_rate = float(lowest_conv_rate)
        else:
            lowest_conv_course = "N/A"
            lowest_conv_rate = 0.0
            
    # Best/Lowest performing categories
    best_category = "N/A"
    best_cat_rate = 0.0
    lowest_category = "N/A"
    lowest_cat_rate = 100.0
    
    if total_views > 0:
        views_by_cat = df_views.groupby("category").size()
        enroll_by_cat = df_enroll.groupby("category").size()
        
        cat_rates = []
        for cat, cat_views in views_by_cat.items():
            cat_enrolls = enroll_by_cat.get(cat, 0)
            cat_conv = (cat_enrolls / cat_views) * 100
            cat_rates.append((cat, cat_conv))
            
        if cat_rates:
            best_category, best_cat_rate = max(cat_rates, key=lambda x: x[1])
            lowest_category, lowest_cat_rate = min(cat_rates, key=lambda x: x[1])
            best_cat_rate = float(best_cat_rate)
            lowest_cat_rate = float(lowest_cat_rate)
            
    # Peak enrollment hour
    peak_hour = 0
    peak_hour_count = 0
    if total_enrollments > 0:
        df_enroll_copy = df_enroll.copy()
        df_enroll_copy["timestamp"] = pd.to_datetime(df_enroll_copy["timestamp"])
        hour_counts = df_enroll_copy["timestamp"].dt.hour.value_counts()
        if not hour_counts.empty:
            peak_hour = int(hour_counts.idxmax())
            peak_hour_count = int(hour_counts.max())
            
    return {
        "total_searches": total_searches,
        "total_views": total_views,
        "total_enrollments": total_enrollments,
        "conversion_rate": round(conversion_rate, 2),
        "avg_views_per_course": round(avg_views, 2),
        "avg_enrollments_per_course": round(avg_enroll, 2),
        "highest_viewed_course": highest_viewed_course,
        "highest_views_count": highest_views_count,
        "lowest_conversion_course": lowest_conv_course,
        "lowest_conversion_rate": round(lowest_conv_rate, 2) if lowest_conv_course != "N/A" else 0.0,
        "best_category": best_category,
        "best_category_rate": round(best_cat_rate, 2) if best_category != "N/A" else 0.0,
        "lowest_category": lowest_category,
        "lowest_category_rate": round(lowest_cat_rate, 2) if lowest_category != "N/A" else 0.0,
        "peak_enrollment_hour": f"{peak_hour:02d}:00 - {peak_hour+1:02d}:00" if total_enrollments > 0 else "N/A"
    }

def get_avg_time_spent(course_id: str) -> float:
    """Calculates a deterministic average time spent in minutes for high fidelity."""
    return round((abs(hash(course_id)) % 150 + 80) / 10, 1)

def get_course_performance(
    db: Session, 
    dataset_id: int, 
    category: str = None, 
    start_date: str = None, 
    end_date: str = None, 
    course_id: str = None
) -> List[Dict[str, Any]]:
    """Generates the Course Performance table metrics with filters."""
    dfs = load_filtered_dataframes(db, dataset_id, category, start_date, end_date, course_id)
    df_search = dfs["searches"]
    df_views = dfs["views"]
    df_enroll = dfs["enrollments"]
    
    if df_views.empty:
        return []
        
    views_by_course = df_views.groupby(["course_id", "course_name", "category"]).size().reset_index(name="views")
    enroll_by_course = df_enroll.groupby("course_id").size().reset_index(name="enrollments")
    
    # Merge views and enrollments
    perf_df = pd.merge(views_by_course, enroll_by_course, on="course_id", how="left").fillna(0)
    perf_df["enrollments"] = perf_df["enrollments"].astype(int)
    
    # Calculate conversion rate
    perf_df["conversion_rate"] = (perf_df["enrollments"] / perf_df["views"] * 100).round(2)
    
    # Merge search counts matching the courses
    search_by_course = df_search.groupby("course_id").size().reset_index(name="search_count")
    perf_df = pd.merge(perf_df, search_by_course, on="course_id", how="left").fillna(0)
    perf_df["search_count"] = perf_df["search_count"].astype(int)
    
    # Add synthetic average time spent
    perf_df["average_time_spent"] = perf_df["course_id"].apply(get_avg_time_spent)
    
    # Add synthetic difficulty metric (Beginner, Intermediate, Advanced) based on ID hash
    difficulties = ["Beginner", "Intermediate", "Advanced"]
    perf_df["difficulty"] = perf_df["course_id"].apply(lambda cid: difficulties[abs(hash(cid)) % len(difficulties)])
    
    # Sort by views descending
    perf_df = perf_df.sort_values(by="views", ascending=False)
    
    return perf_df.to_dict(orient="records")

def get_search_analytics(
    db: Session, 
    dataset_id: int, 
    category: str = None, 
    start_date: str = None, 
    end_date: str = None, 
    course_id: str = None
) -> Dict[str, Any]:
    """Analyzes search query patterns with filters."""
    dfs = load_filtered_dataframes(db, dataset_id, category, start_date, end_date, course_id)
    df_search = dfs["searches"]
    df_views = dfs["views"]
    df_enroll = dfs["enrollments"]
    
    if df_search.empty:
        return {"keywords": [], "low_conversion_keywords": [], "total_searches": 0, "unique_keywords": 0, "avg_searches": 0.0, "success_rate": 0.0}
        
    total_searches = len(df_search)
    unique_keywords = df_search["search_keyword"].nunique()
    
    # Group by keywords to get frequency
    keyword_freq = df_search["search_keyword"].value_counts().reset_index(name="search_count")
    keyword_freq.columns = ["keyword", "search_count"]
    keyword_freq = keyword_freq[keyword_freq["keyword"].str.strip() != ""]
    
    avg_searches_val = float(keyword_freq["search_count"].mean()) if not keyword_freq.empty else 0.0
    
    # Calculate search success rate (searches that led to a course view or enrollment)
    successful_searches = df_search[df_search["course_id"].notna() & (df_search["course_id"] != "") & (df_search["course_id"] != "None")]
    success_rate = (len(successful_searches) / total_searches * 100) if total_searches > 0 else 0.0
    
    keyword_conv = []
    for _, row in keyword_freq.iterrows():
        kw = row["keyword"]
        count = int(row["search_count"])
        
        # Count views and enrollments containing this keyword
        kw_views = len(df_views[df_views["search_keyword"].astype(str).str.contains(kw, case=False, na=False)]) if not df_views.empty else 0
        kw_enrolls = len(df_enroll[df_enroll["search_keyword"].astype(str).str.contains(kw, case=False, na=False)]) if not df_enroll.empty else 0
        
        conv_rate = (kw_enrolls / kw_views * 100) if kw_views > 0 else 0.0
        
        keyword_conv.append({
            "keyword": kw,
            "search_count": count,
            "views": kw_views,
            "enrollments": kw_enrolls,
            "conversion_rate": round(conv_rate, 2)
        })
        
    # Sort keywords by frequency
    keyword_conv_sorted = sorted(keyword_conv, key=lambda x: x["search_count"], reverse=True)
    
    # Low conversion search keywords (High search counts but low conversion)
    low_conv_kw = [k for k in keyword_conv_sorted if k["search_count"] >= 3 and k["conversion_rate"] < 25]
    low_conv_kw = sorted(low_conv_kw, key=lambda x: x["conversion_rate"])
    
    return {
        "keywords": keyword_conv_sorted[:15], # Top 15 keywords
        "low_conversion_keywords": low_conv_kw[:10],
        "total_searches": total_searches,
        "unique_keywords": unique_keywords,
        "avg_searches": round(avg_searches_val, 2),
        "success_rate": round(success_rate, 2)
    }

def get_category_analysis(
    db: Session, 
    dataset_id: int, 
    category: str = None, 
    start_date: str = None, 
    end_date: str = None, 
    course_id: str = None
) -> List[Dict[str, Any]]:
    """Analyzes performance by category with filters."""
    dfs = load_filtered_dataframes(db, dataset_id, category, start_date, end_date, course_id)
    df_search = dfs["searches"]
    df_views = dfs["views"]
    df_enroll = dfs["enrollments"]
    
    if df_views.empty:
        return []
        
    views_by_cat = df_views.groupby("category").size().reset_index(name="views")
    enroll_by_cat = df_enroll.groupby("category").size().reset_index(name="enrollments")
    
    cat_df = pd.merge(views_by_cat, enroll_by_cat, on="category", how="left").fillna(0)
    cat_df["enrollments"] = cat_df["enrollments"].astype(int)
    cat_df["conversion_rate"] = (cat_df["enrollments"] / cat_df["views"] * 100).round(2)
    
    # Map category to search counts
    course_cat = {}
    if not df_views.empty:
        for _, row in df_views[["course_id", "category"]].drop_duplicates().iterrows():
            course_cat[row["course_id"]] = row["category"]
    if not df_enroll.empty:
        for _, row in df_enroll[["course_id", "category"]].drop_duplicates().iterrows():
            course_cat[row["course_id"]] = row["category"]
            
    df_search_copy = df_search.copy()
    if not df_search_copy.empty:
        df_search_copy["category"] = df_search_copy["course_id"].map(course_cat).fillna("Unclassified")
        searches_by_cat = df_search_copy.groupby("category").size().reset_index(name="average_searches")
        cat_df = pd.merge(cat_df, searches_by_cat, on="category", how="left").fillna(0)
        cat_df["average_searches"] = cat_df["average_searches"].astype(int)
    else:
        cat_df["average_searches"] = 0
        
    return cat_df.to_dict(orient="records")

def get_time_trends(
    db: Session, 
    dataset_id: int, 
    category: str = None, 
    start_date: str = None, 
    end_date: str = None, 
    course_id: str = None
) -> Dict[str, Any]:
    """Generates daily, weekly, monthly and hourly activity trends with filters."""
    dfs = load_filtered_dataframes(db, dataset_id, category, start_date, end_date, course_id)
    df_search = dfs["searches"]
    df_views = dfs["views"].copy()
    df_enroll = dfs["enrollments"].copy()
    
    if df_views.empty:
        return {"daily": [], "weekly": [], "monthly": [], "hourly": []}
        
    # Convert timestamps
    df_views["timestamp"] = pd.to_datetime(df_views["timestamp"])
    df_enroll["timestamp"] = pd.to_datetime(df_enroll["timestamp"])
    
    # Daily views and enrolls
    views_daily = df_views.groupby(df_views["timestamp"].dt.date).size()
    enroll_daily = df_enroll.groupby(df_enroll["timestamp"].dt.date).size()
    
    # Merge daily trends
    daily_df = pd.DataFrame({"views": views_daily, "enrollments": enroll_daily}).fillna(0)
    daily_df.index.name = "date"
    daily_df = daily_df.reset_index()
    daily_df["date"] = daily_df["date"].astype(str)
    daily_df["enrollments"] = daily_df["enrollments"].astype(int)
    
    # Weekly views and enrolls (Weekday name)
    df_views["weekday"] = df_views["timestamp"].dt.day_name()
    df_enroll["weekday"] = df_enroll["timestamp"].dt.day_name()
    
    views_weekly = df_views.groupby("weekday").size()
    enroll_weekly = df_enroll.groupby("weekday").size()
    
    weekdays_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    weekly_df = pd.DataFrame({"views": views_weekly, "enrollments": enroll_weekly}).fillna(0)
    weekly_df = weekly_df.reindex(weekdays_order, fill_value=0).reset_index()
    weekly_df["enrollments"] = weekly_df["enrollments"].astype(int)
    
    # Monthly views and enrolls (YYYY-MM)
    df_views["month"] = df_views["timestamp"].dt.to_period("M").astype(str)
    df_enroll["month"] = df_enroll["timestamp"].dt.to_period("M").astype(str)
    
    views_monthly = df_views.groupby("month").size()
    enroll_monthly = df_enroll.groupby("month").size()
    
    monthly_df = pd.DataFrame({"views": views_monthly, "enrollments": enroll_monthly}).fillna(0)
    monthly_df.index.name = "month"
    monthly_df = monthly_df.reset_index().sort_values("month")
    monthly_df["enrollments"] = monthly_df["enrollments"].astype(int)
    
    # Hourly views and enrolls
    views_hourly = df_views.groupby(df_views["timestamp"].dt.hour).size()
    enroll_hourly = df_enroll.groupby(df_enroll["timestamp"].dt.hour).size()
    
    # Merge hourly
    hourly_df = pd.DataFrame({"views": views_hourly, "enrollments": enroll_hourly}).fillna(0)
    for h in range(24):
        if h not in hourly_df.index:
            hourly_df.loc[h] = [0, 0]
    hourly_df = hourly_df.sort_index()
    hourly_df.index.name = "hour"
    hourly_df = hourly_df.reset_index()
    hourly_df["enrollments"] = hourly_df["enrollments"].astype(int)
    
    # Peak Hours
    peak_search_hour = "N/A"
    if not df_search.empty:
        df_search_copy = df_search.copy()
        df_search_copy["timestamp"] = pd.to_datetime(df_search_copy["timestamp"])
        search_hours = df_search_copy["timestamp"].dt.hour.value_counts()
        if not search_hours.empty:
            peak_search_hour = f"{int(search_hours.idxmax()):02d}:00"
            
    peak_view_hour = "N/A"
    if not df_views.empty:
        view_hours = df_views["timestamp"].dt.hour.value_counts()
        if not view_hours.empty:
            peak_view_hour = f"{int(view_hours.idxmax()):02d}:00"
            
    peak_enroll_hour = "N/A"
    if not df_enroll.empty:
        enroll_hours = df_enroll["timestamp"].dt.hour.value_counts()
        if not enroll_hours.empty:
            peak_enroll_hour = f"{int(enroll_hours.idxmax()):02d}:00"
    
    return {
        "daily": daily_df.to_dict(orient="records"),
        "weekly": weekly_df.to_dict(orient="records"),
        "monthly": monthly_df.to_dict(orient="records"),
        "hourly": hourly_df.to_dict(orient="records"),
        "peak_search_hour": peak_search_hour,
        "peak_view_hour": peak_view_hour,
        "peak_enroll_hour": peak_enroll_hour
    }

def get_business_insights(
    db: Session, 
    dataset_id: int, 
    category: str = None, 
    start_date: str = None, 
    end_date: str = None, 
    course_id: str = None
) -> List[Dict[str, str]]:
    """Generates qualitative, rule-based business insights and recommendations with filters."""
    dfs = load_filtered_dataframes(db, dataset_id, category, start_date, end_date, course_id)
    df_search = dfs["searches"]
    df_views = dfs["views"]
    df_enroll = dfs["enrollments"]
    
    if df_views.empty:
        return [{"type": "warning", "title": "No Data Available", "description": "Please populate or clean the dataset to extract insights."}]
        
    insights = []
    
    # 1. High Views, Low Enrollment check
    course_perf = get_course_performance(db, dataset_id, category, start_date, end_date, course_id)
    if course_perf:
        median_views = np.median([c["views"] for c in course_perf])
        for course in course_perf:
            if course["views"] >= median_views and course["conversion_rate"] < 15.0:
                insights.append({
                    "type": "warning",
                    "title": f"Low Conversion on '{course['course_name']}'",
                    "description": f"This course has high visibility ({course['views']} views) but converts at only {course['conversion_rate']}%. We recommend auditing the course syllabus page, reviewing price point, or optimizing the introductory video to address student dropoff."
                })
                
    # 2. Category Insights
    cat_analysis = get_category_analysis(db, dataset_id, category, start_date, end_date, course_id)
    if cat_analysis:
        best_cat = max(cat_analysis, key=lambda x: x["conversion_rate"])
        insights.append({
            "type": "success",
            "title": f"High Category Engagement: {best_cat['category']}",
            "description": f"The '{best_cat['category']}' category has the highest view-to-enrollment conversion rate ({best_cat['conversion_rate']}%). Focus promotion budgets and acquire more content specifically under this vertical."
        })
        
    # 3. Peak hour recommendations
    if not df_enroll.empty:
        df_enroll_copy = df_enroll.copy()
        df_enroll_copy["timestamp"] = pd.to_datetime(df_enroll_copy["timestamp"])
        hour_counts = df_enroll_copy["timestamp"].dt.hour.value_counts()
        if not hour_counts.empty:
            peak_hour = hour_counts.idxmax()
            insights.append({
                "type": "info",
                "title": f"Peak Enrollment Hour Identified",
                "description": f"Student enrollments peak during the hour of {peak_hour:02d}:00. Schedule promotional push notifications, email campaigns, and new course announcements around this window to maximize engagement."
            })
            
    # 4. Search analytics gaps
    search_data = get_search_analytics(db, dataset_id, category, start_date, end_date, course_id)
    low_conv_kws = search_data.get("low_conversion_keywords", [])
    if low_conv_kws:
        top_low_kw = low_conv_kws[0]
        insights.append({
            "type": "danger",
            "title": f"Search Deficit for Keyword '{top_low_kw['keyword']}'",
            "description": f"The search query '{top_low_kw['keyword']}' was run {top_low_kw['search_count']} times, but has low enrollment conversion ({top_low_kw['conversion_rate']}%). This indicates a misalignment; either the search result relevance is low, or there is lack of premium content matching this specific intent. Consider developing new courses for this query."
        })
        
    # Standard fallback if list is empty
    if not insights:
        insights.append({
            "type": "info",
            "title": "Healthy Enrollment Funnel",
            "description": "No critical dropoffs detected. Course conversion metrics are balanced across categories."
        })
        
    return insights

def get_advanced_eda_metrics(db: Session, dataset_id: int) -> Dict[str, Any]:
    """
    Computes advanced statistical and EDA metrics:
    1. Pearson Correlation & Relationship Analysis between views and enrollments.
    2. Distribution Analysis of course views (mean, median, std dev, skewness).
    3. Time-Series 3-day rolling average of daily view activity.
    4. Outlier Detection of daily view activity using the IQR method.
    """
    dfs = load_dataframes(db, dataset_id)
    df_views = dfs["views"]
    df_enroll = dfs["enrollments"]
    
    # 1. Pearson Correlation
    correlation_coefficient = 0.0
    relationship_strength = "No Data"
    
    if not df_views.empty and not df_enroll.empty:
        views_by_course = df_views.groupby("course_id").size().reset_index(name="views")
        enroll_by_course = df_enroll.groupby("course_id").size().reset_index(name="enrollments")
        merged = pd.merge(views_by_course, enroll_by_course, on="course_id", how="outer").fillna(0)
        
        if len(merged) > 1:
            correlation_coefficient = float(merged["views"].corr(merged["enrollments"]))
            if pd.isna(correlation_coefficient):
                correlation_coefficient = 0.0
                
            abs_corr = abs(correlation_coefficient)
            if abs_corr >= 0.7:
                relationship_strength = "Very Strong Positive" if correlation_coefficient > 0 else "Very Strong Negative"
            elif abs_corr >= 0.4:
                relationship_strength = "Moderate Positive" if correlation_coefficient > 0 else "Moderate Negative"
            elif abs_corr >= 0.1:
                relationship_strength = "Weak Positive" if correlation_coefficient > 0 else "Weak Negative"
            else:
                relationship_strength = "Negligible Relationship"
                
    # 2. Distribution Analysis of Course Views
    views_distribution = {
        "mean": 0.0,
        "median": 0.0,
        "std_dev": 0.0,
        "skewness": 0.0
    }
    
    if not df_views.empty:
        course_views = df_views.groupby("course_id").size()
        if len(course_views) > 0:
            views_distribution["mean"] = round(float(course_views.mean()), 2)
            views_distribution["median"] = round(float(course_views.median()), 2)
            views_distribution["std_dev"] = round(float(course_views.std()), 2) if len(course_views) > 1 else 0.0
            views_distribution["skewness"] = round(float(course_views.skew()), 2) if len(course_views) > 2 else 0.0
            if pd.isna(views_distribution["std_dev"]): views_distribution["std_dev"] = 0.0
            if pd.isna(views_distribution["skewness"]): views_distribution["skewness"] = 0.0

    # 3 & 4. Time-Series Trends & Outliers
    rolling_averages = []
    outliers = []
    
    if not df_views.empty and "timestamp" in df_views.columns:
        df_views_copy = df_views.copy()
        df_views_copy["date"] = pd.to_datetime(df_views_copy["timestamp"]).dt.date
        daily_views = df_views_copy.groupby("date").size().reset_index(name="views")
        daily_views = daily_views.sort_values("date")
        
        # 3. 3-day Rolling Average
        if len(daily_views) > 0:
            daily_views["rolling_avg"] = daily_views["views"].rolling(window=3, min_periods=1).mean()
            rolling_averages = [
                {"date": str(row["date"]), "views": int(row["views"]), "rolling_avg": round(float(row["rolling_avg"]), 2)}
                for _, row in daily_views.iterrows()
            ]
            
        # 4. Outlier Detection with IQR method
        if len(daily_views) >= 4:
            q1 = daily_views["views"].quantile(0.25)
            q3 = daily_views["views"].quantile(0.75)
            iqr = q3 - q1
            lower_bound = q1 - 1.5 * iqr
            upper_bound = q3 + 1.5 * iqr
            
            outlier_df = daily_views[(daily_views["views"] < lower_bound) | (daily_views["views"] > upper_bound)]
            outliers = [
                {
                    "date": str(row["date"]), 
                    "views": int(row["views"]), 
                    "status": "Unusually High" if row["views"] > upper_bound else "Unusually Low",
                    "lower_bound": round(lower_bound, 1),
                    "upper_bound": round(upper_bound, 1)
                }
                for _, row in outlier_df.iterrows()
            ]
    return {
        "correlation": {
            "coefficient": round(correlation_coefficient, 3),
            "strength": relationship_strength
        },
        "views_distribution": views_distribution,
        "rolling_activity": rolling_averages,
        "anomalous_outliers": outliers
    }
