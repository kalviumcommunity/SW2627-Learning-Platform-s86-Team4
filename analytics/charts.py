import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import numpy as np
from sqlalchemy.orm import Session
from analytics.analysis import (
    load_filtered_dataframes, 
    get_course_performance, 
    get_category_analysis,
    get_search_analytics,
    get_time_trends
)

def apply_premium_theme(fig):
    """Applies a premium light theme to a Plotly figure."""
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(
            family="Inter, system-ui, sans-serif",
            color="#0f172a", # slate-900 (dark text)
            size=11
        ),
        margin=dict(l=40, r=20, t=40, b=40),
        xaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.12)", # slate-400 with opacity
            linecolor="rgba(148, 163, 184, 0.15)",
            tickfont=dict(color="#475569") # slate-600
        ),
        yaxis=dict(
            gridcolor="rgba(148, 163, 184, 0.12)",
            linecolor="rgba(148, 163, 184, 0.15)",
            tickfont=dict(color="#475569")
        )
    )
    try:
        fig.update_traces(marker=dict(line=dict(color="rgba(15,23,42,0.05)", width=1)))
    except Exception:
        pass
    return fig

def get_funnel_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates a Funnel Chart: Searches -> Views -> Enrollments."""
    dfs = load_filtered_dataframes(db, dataset_id, category, start_date, end_date, course_id)
    s_count = len(dfs["searches"])
    v_count = len(dfs["views"])
    e_count = len(dfs["enrollments"])
    
    stages = ["Searches", "Course Views", "Enrollments"]
    counts = [s_count, v_count, e_count]
    
    fig = go.Figure(go.Funnel(
        y=stages,
        x=counts,
        textposition="inside",
        textinfo="value+percent initial",
        opacity=0.85,
        marker=dict(
            color=["#6366f1", "#8b5cf6", "#ec4899"], # Indigo, Violet, Pink
            line=dict(width=1, color="rgba(255,255,255,0.2)")
        )
    ))
    
    fig.update_layout(title="Enrollment Conversion Funnel")
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_category_bar_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates a grouped Bar Chart comparing Views & Enrollments by Category."""
    cat_data = get_category_analysis(db, dataset_id, category, start_date, end_date, course_id)
    if not cat_data:
        return go.Figure().to_dict()
        
    df = pd.DataFrame(cat_data)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(
        x=df["category"],
        y=df["views"],
        name="Views",
        marker_color="rgba(99, 102, 241, 0.8)", # indigo-500
    ))
    fig.add_trace(go.Bar(
        x=df["category"],
        y=df["enrollments"],
        name="Enrollments",
        marker_color="rgba(236, 72, 153, 0.8)", # pink-500
    ))
    
    fig.update_layout(
        barmode='group',
        title="Views & Enrollments by Category",
        xaxis_title="Category",
        yaxis_title="Count"
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_time_line_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates a Line Chart showing daily views and enrollments trends."""
    dfs = load_filtered_dataframes(db, dataset_id, category, start_date, end_date, course_id)
    df_views = dfs["views"]
    df_enroll = dfs["enrollments"]
    
    if df_views.empty:
        return go.Figure().to_dict()
        
    df_views_copy = df_views.copy()
    df_enroll_copy = df_enroll.copy()
    df_views_copy["date"] = pd.to_datetime(df_views_copy["timestamp"]).dt.date
    df_enroll_copy["date"] = pd.to_datetime(df_enroll_copy["timestamp"]).dt.date
    
    v_daily = df_views_copy.groupby("date").size().reset_index(name="Views")
    e_daily = df_enroll_copy.groupby("date").size().reset_index(name="Enrollments")
    
    merged = pd.merge(v_daily, e_daily, on="date", how="outer").fillna(0)
    merged = merged.sort_values("date")
    merged["date"] = merged["date"].astype(str)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=merged["date"], y=merged["Views"],
        mode='lines+markers',
        name='Views',
        line=dict(color='#6366f1', width=3),
        marker=dict(size=6)
    ))
    fig.add_trace(go.Scatter(
        x=merged["date"], y=merged["Enrollments"],
        mode='lines+markers',
        name='Enrollments',
        line=dict(color='#ec4899', width=3),
        marker=dict(size=6)
    ))
    
    fig.update_layout(
        title="Daily Activity Trends",
        xaxis_title="Date",
        yaxis_title="Count",
        hovermode="x unified"
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_views_vs_enrollments_scatter(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates a Scatter Plot of views vs. enrollments for courses."""
    perf_data = get_course_performance(db, dataset_id, category, start_date, end_date, course_id)
    if not perf_data:
        return go.Figure().to_dict()
        
    df = pd.DataFrame(perf_data)
    
    fig = px.scatter(
        df,
        x="views",
        y="enrollments",
        text="course_name",
        size="views",
        color="category",
        hover_name="course_name",
        title="Course Views vs. Enrollments Scatter Plot",
        labels={"views": "Course Views", "enrollments": "Enrollments"},
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    
    fig.update_traces(textposition='top center')
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_category_pie_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates a Pie Chart representing enrollment distribution across categories."""
    cat_data = get_category_analysis(db, dataset_id, category, start_date, end_date, course_id)
    if not cat_data:
        return go.Figure().to_dict()
        
    df = pd.DataFrame(cat_data)
    
    fig = px.pie(
        df,
        values="enrollments",
        names="category",
        title="Enrollment Distribution by Category",
        hole=0.4,
        color_discrete_sequence=px.colors.qualitative.Safe
    )
    
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_hourly_heatmap(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates a Heatmap of activity density by Day of Week vs. Hour of Day."""
    dfs = load_filtered_dataframes(db, dataset_id, category, start_date, end_date, course_id)
    df_views = dfs["views"].copy()
    df_enroll = dfs["enrollments"].copy()
    
    if df_views.empty:
        return go.Figure().to_dict()
        
    df_views["timestamp"] = pd.to_datetime(df_views["timestamp"])
    df_enroll["timestamp"] = pd.to_datetime(df_enroll["timestamp"])
    
    df_comb = pd.concat([df_views[["timestamp"]], df_enroll[["timestamp"]]], ignore_index=True)
    
    df_comb["day_of_week"] = df_comb["timestamp"].dt.day_name()
    df_comb["hour"] = df_comb["timestamp"].dt.hour
    
    grid = df_comb.groupby(["day_of_week", "hour"]).size().unstack(fill_value=0)
    
    days_ordered = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    grid = grid.reindex(days_ordered, fill_value=0)
    
    for h in range(24):
        if h not in grid.columns:
            grid[h] = 0
    grid = grid.sort_index(axis=1)
    
    fig = go.Figure(data=go.Heatmap(
        z=grid.values,
        x=[f"{h:02d}:00" for h in grid.columns],
        y=grid.index,
        colorscale="Viridis",
        colorbar=dict(title="Activity"),
        hoverongaps=False
    ))
    
    fig.update_layout(
        title="Activity Density (Day vs. Hour)",
        xaxis_title="Hour of Day",
        yaxis_title="Day of Week"
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_course_treemap(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates a Treemap visualizing course hierarchies and views."""
    perf_data = get_course_performance(db, dataset_id, category, start_date, end_date, course_id)
    if not perf_data:
        return go.Figure().to_dict()
        
    df = pd.DataFrame(perf_data)
    
    fig = px.treemap(
        df,
        path=["category", "course_name"],
        values="views",
        color="conversion_rate",
        color_continuous_scale="RdPu",
        title="Category & Course Treemap (Sized by Views, Colored by Conversion %)"
    )
    
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_enrollment_area_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates an Area Chart for cumulative enrollments over time."""
    dfs = load_filtered_dataframes(db, dataset_id, category, start_date, end_date, course_id)
    df_enroll = dfs["enrollments"]
    
    if df_enroll.empty:
        return go.Figure().to_dict()
        
    df_enroll_copy = df_enroll.copy()
    df_enroll_copy["date"] = pd.to_datetime(df_enroll_copy["timestamp"]).dt.date
    daily_enrolls = df_enroll_copy.groupby("date").size().reset_index(name="Enrollments")
    daily_enrolls = daily_enrolls.sort_values("date")
    
    daily_enrolls["Cumulative Enrollments"] = daily_enrolls["Enrollments"].cumsum()
    daily_enrolls["date"] = daily_enrolls["date"].astype(str)
    
    fig = px.area(
        daily_enrolls,
        x="date",
        y="Cumulative Enrollments",
        title="Cumulative Enrollments Over Time",
        labels={"date": "Date", "Cumulative Enrollments": "Cumulative Enrollments"}
    )
    
    fig.update_traces(
        line=dict(color='#8b5cf6', width=2),
        fillcolor='rgba(139, 92, 246, 0.2)'
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_monthly_trend_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Monthly Enrollment Line Trend."""
    dfs = load_filtered_dataframes(db, dataset_id, category, start_date, end_date, course_id)
    df_enroll = dfs["enrollments"]
    if df_enroll.empty:
        return go.Figure().to_dict()
        
    df_enroll_copy = df_enroll.copy()
    df_enroll_copy["month"] = pd.to_datetime(df_enroll_copy["timestamp"]).dt.to_period("M").astype(str)
    monthly_counts = df_enroll_copy.groupby("month").size().reset_index(name="Enrollments")
    
    fig = px.line(
        monthly_counts, 
        x="month", 
        y="Enrollments", 
        title="Monthly Enrollment Trend", 
        markers=True, 
        color_discrete_sequence=["#8b5cf6"]
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_top_5_viewed_courses_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Top 5 Viewed Courses bar chart."""
    perf = get_course_performance(db, dataset_id, category, start_date, end_date, course_id)
    if not perf:
        return go.Figure().to_dict()
    df = pd.DataFrame(perf).head(5)
    
    fig = px.bar(
        df, 
        x="course_name", 
        y="views", 
        title="Top 5 Viewed Courses", 
        color="views", 
        color_continuous_scale="Viridis"
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_top_viewed_courses_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Top 10 Viewed Courses horizontal bar chart."""
    perf = get_course_performance(db, dataset_id, category, start_date, end_date, course_id)
    if not perf:
        return go.Figure().to_dict()
    df = pd.DataFrame(perf).head(10)
    
    fig = px.bar(
        df, 
        y="course_name", 
        x="views", 
        orientation="h", 
        title="Top 10 Viewed Courses", 
        color="views", 
        color_continuous_scale="Purples"
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_top_enrolled_courses_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Top 10 Enrolled Courses bar chart."""
    perf = get_course_performance(db, dataset_id, category, start_date, end_date, course_id)
    if not perf:
        return go.Figure().to_dict()
    df = pd.DataFrame(perf).sort_values("enrollments", ascending=False).head(10)
    
    fig = px.bar(
        df, 
        x="course_name", 
        y="enrollments", 
        title="Top 10 Enrolled Courses", 
        color="enrollments", 
        color_continuous_scale="RdPu"
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_course_conversion_rate_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Top 10 Courses by Conversion Rate horizontal bar chart."""
    perf = get_course_performance(db, dataset_id, category, start_date, end_date, course_id)
    if not perf:
        return go.Figure().to_dict()
    df = pd.DataFrame(perf).sort_values("conversion_rate", ascending=False).head(10)
    
    fig = px.bar(
        df, 
        y="course_name", 
        x="conversion_rate", 
        orientation="h", 
        title="Top 10 Courses by Conversion Rate (%)", 
        color="conversion_rate", 
        color_continuous_scale="Reds"
    )
    fig.update_layout(yaxis={'categoryorder':'total ascending'})
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_daily_search_trend_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Daily Search Trend line chart."""
    dfs = load_filtered_dataframes(db, dataset_id, category, start_date, end_date, course_id)
    df_search = dfs["searches"]
    if df_search.empty:
        return go.Figure().to_dict()
        
    df_search_copy = df_search.copy()
    df_search_copy["date"] = pd.to_datetime(df_search_copy["timestamp"]).dt.date
    daily_counts = df_search_copy.groupby("date").size().reset_index(name="Searches")
    daily_counts["date"] = daily_counts["date"].astype(str)
    
    fig = px.line(
        daily_counts, 
        x="date", 
        y="Searches", 
        title="Daily Search Trend", 
        markers=True, 
        color_discrete_sequence=["#4f46e5"]
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_most_searched_keywords_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Top 10 Searched Keywords bar chart."""
    search_data = get_search_analytics(db, dataset_id, category, start_date, end_date, course_id)
    kws = search_data.get("keywords", [])
    if not kws:
        return go.Figure().to_dict()
    df = pd.DataFrame(kws).head(10)
    
    fig = px.bar(
        df, 
        x="keyword", 
        y="search_count", 
        title="Top 10 Searched Keywords", 
        color="search_count", 
        color_continuous_scale="Blues"
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_searches_by_category_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Searches by Category bar chart."""
    cats = get_category_analysis(db, dataset_id, category, start_date, end_date, course_id)
    if not cats:
        return go.Figure().to_dict()
    df = pd.DataFrame(cats)
    
    fig = px.bar(
        df, 
        x="category", 
        y="average_searches", 
        title="Searches by Category", 
        color="average_searches", 
        color_continuous_scale="Purples"
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_search_distribution_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Search Distribution donut chart."""
    cats = get_category_analysis(db, dataset_id, category, start_date, end_date, course_id)
    if not cats:
        return go.Figure().to_dict()
    df = pd.DataFrame(cats)
    
    fig = px.pie(
        df, 
        values="average_searches", 
        names="category", 
        title="Search Volume Distribution", 
        hole=0.4, 
        color_discrete_sequence=px.colors.qualitative.Pastel
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_views_by_category_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Views by Category bar chart."""
    cats = get_category_analysis(db, dataset_id, category, start_date, end_date, course_id)
    if not cats:
        return go.Figure().to_dict()
    df = pd.DataFrame(cats)
    
    fig = px.bar(
        df, 
        x="category", 
        y="views", 
        title="Views by Category", 
        color="views", 
        color_continuous_scale="Viridis"
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_enrollments_by_category_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Enrollments by Category bar chart."""
    cats = get_category_analysis(db, dataset_id, category, start_date, end_date, course_id)
    if not cats:
        return go.Figure().to_dict()
    df = pd.DataFrame(cats)
    
    fig = px.bar(
        df, 
        x="category", 
        y="enrollments", 
        title="Enrollments by Category", 
        color="enrollments", 
        color_continuous_scale="RdPu"
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_conversion_by_category_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Conversion by Category bar chart."""
    cats = get_category_analysis(db, dataset_id, category, start_date, end_date, course_id)
    if not cats:
        return go.Figure().to_dict()
    df = pd.DataFrame(cats)
    
    fig = px.bar(
        df, 
        x="category", 
        y="conversion_rate", 
        title="Conversion Rate by Category (%)", 
        color="conversion_rate", 
        color_continuous_scale="Tealgrn"
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_conversion_percentage_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Conversion Rate percentage bar chart for top courses."""
    perf = get_course_performance(db, dataset_id, category, start_date, end_date, course_id)
    if not perf:
        return go.Figure().to_dict()
    df = pd.DataFrame(perf).sort_values("enrollments", ascending=False).head(10)
    
    fig = px.bar(
        df, 
        x="course_name", 
        y="conversion_rate", 
        title="Conversion Rate (%) for Top Enrolled Courses", 
        color="conversion_rate", 
        color_continuous_scale="Plasma"
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_daily_activity_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Daily Activity Trend line chart."""
    trends = get_time_trends(db, dataset_id, category, start_date, end_date, course_id)
    daily = trends.get("daily", [])
    if not daily:
        return go.Figure().to_dict()
    df = pd.DataFrame(daily)
    
    fig = go.Figure()
    fig.add_trace(go.Scatter(x=df["date"], y=df["views"], mode="lines+markers", name="Views", line=dict(color="#6366f1", width=2)))
    fig.add_trace(go.Scatter(x=df["date"], y=df["enrollments"], mode="lines+markers", name="Enrollments", line=dict(color="#ec4899", width=2)))
    fig.update_layout(title="Daily Traffic & Enrollments", xaxis_title="Date", yaxis_title="Count")
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_weekly_activity_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Weekly Activity Trend bar chart."""
    trends = get_time_trends(db, dataset_id, category, start_date, end_date, course_id)
    weekly = trends.get("weekly", [])
    if not weekly:
        return go.Figure().to_dict()
    df = pd.DataFrame(weekly)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["weekday"], y=df["views"], name="Views", marker_color="rgba(99, 102, 241, 0.8)"))
    fig.add_trace(go.Bar(x=df["weekday"], y=df["enrollments"], name="Enrollments", marker_color="rgba(236, 72, 153, 0.8)"))
    fig.update_layout(barmode="group", title="Weekly Activity Distribution", xaxis_title="Day of Week", yaxis_title="Count")
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_monthly_activity_chart(db: Session, dataset_id: int, category: str = None, start_date: str = None, end_date: str = None, course_id: str = None) -> dict:
    """Generates Monthly Activity Trend bar chart."""
    trends = get_time_trends(db, dataset_id, category, start_date, end_date, course_id)
    monthly = trends.get("monthly", [])
    if not monthly:
        return go.Figure().to_dict()
    df = pd.DataFrame(monthly)
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=df["month"], y=df["views"], name="Views", marker_color="rgba(99, 102, 241, 0.8)"))
    fig.add_trace(go.Bar(x=df["month"], y=df["enrollments"], name="Enrollments", marker_color="rgba(236, 72, 153, 0.8)"))
    fig.update_layout(barmode="group", title="Monthly Activity Trends", xaxis_title="Month", yaxis_title="Count")
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_compare_grouped_bar_chart(db: Session, dataset_id: int, course_id_1: str, course_id_2: str) -> dict:
    """Generates grouped bar comparison chart for two courses."""
    perf = get_course_performance(db, dataset_id)
    c1 = next((c for c in perf if c["course_id"] == course_id_1), None)
    c2 = next((c for c in perf if c["course_id"] == course_id_2), None)
    if not c1 or not c2:
        return go.Figure().to_dict()
        
    metrics = ["Views", "Searches", "Enrollments"]
    vals1 = [c1["views"], c1["search_count"], c1["enrollments"]]
    vals2 = [c2["views"], c2["search_count"], c2["enrollments"]]
    
    fig = go.Figure()
    fig.add_trace(go.Bar(x=metrics, y=vals1, name=c1["course_name"], marker_color="#6366f1"))
    fig.add_trace(go.Bar(x=metrics, y=vals2, name=c2["course_name"], marker_color="#ec4899"))
    fig.update_layout(barmode="group", title="Side-by-Side Volume Comparison", yaxis_title="Count")
    fig = apply_premium_theme(fig)
    return fig.to_dict()

def get_compare_radar_chart(db: Session, dataset_id: int, course_id_1: str, course_id_2: str) -> dict:
    """Generates radar chart comparison vector for two courses."""
    perf = get_course_performance(db, dataset_id)
    c1 = next((c for c in perf if c["course_id"] == course_id_1), None)
    c2 = next((c for c in perf if c["course_id"] == course_id_2), None)
    if not c1 or not c2:
        return go.Figure().to_dict()
        
    categories = ["Conversion Rate (%)", "Average Time (min)", "Popularity Index"]
    max_views = max([c["views"] for c in perf]) if perf else 1
    pop1 = (c1["views"] / max_views * 100)
    pop2 = (c2["views"] / max_views * 100)
    
    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=[c1["conversion_rate"], c1["average_time_spent"], pop1],
        theta=categories,
        fill="toself",
        name=c1["course_name"],
        line_color="#6366f1"
    ))
    fig.add_trace(go.Scatterpolar(
        r=[c2["conversion_rate"], c2["average_time_spent"], pop2],
        theta=categories,
        fill="toself",
        name=c2["course_name"],
        line_color="#ec4899"
    ))
    fig.update_layout(
        polar=dict(
            radialaxis=dict(visible=True, range=[0, 100])
        ),
        showlegend=True,
        title="Performance Vector Comparison (Radar)"
    )
    fig = apply_premium_theme(fig)
    return fig.to_dict()
