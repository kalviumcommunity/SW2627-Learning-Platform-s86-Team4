import pandas as pd
import numpy as np
import os
import random
from datetime import datetime, timedelta

# Create datasets directory if not exists
os.makedirs(os.path.dirname(os.path.abspath(__file__)), exist_ok=True)

# Seed for reproducibility
np.random.seed(42)
random.seed(42)

# Course definition with category and base popularity/characteristics
courses = [
    {"id": "C_101", "name": "Introduction to Python", "category": "Data Science", "search_keywords": ["python", "learn python", "coding python", "programming"], "view_prob": 0.85, "enroll_prob": 0.55},
    {"id": "C_102", "name": "Python for Data Science", "category": "Data Science", "search_keywords": ["python", "data science", "pandas", "numpy"], "view_prob": 0.80, "enroll_prob": 0.40},
    {"id": "C_103", "name": "Machine Learning Bootcamp", "category": "Data Science", "search_keywords": ["machine learning", "ml", "data science", "ai"], "view_prob": 0.90, "enroll_prob": 0.12}, # High views, low enrollment!
    {"id": "C_104", "name": "Deep Learning Specialization", "category": "Data Science", "search_keywords": ["deep learning", "neural networks", "ai", "tensorflow"], "view_prob": 0.45, "enroll_prob": 0.18},
    {"id": "C_201", "name": "Mastering React", "category": "Web Development", "search_keywords": ["react", "javascript", "frontend", "web development"], "view_prob": 0.75, "enroll_prob": 0.45},
    {"id": "C_202", "name": "Next.js Complete Guide", "category": "Web Development", "search_keywords": ["nextjs", "react", "frontend", "web development"], "view_prob": 0.65, "enroll_prob": 0.35},
    {"id": "C_203", "name": "Django Web Dev from Scratch", "category": "Web Development", "search_keywords": ["django", "python", "backend", "web development"], "view_prob": 0.50, "enroll_prob": 0.20},
    {"id": "C_301", "name": "Excel for Beginners to Pro", "category": "Business", "search_keywords": ["excel", "spreadsheet", "data analysis", "business"], "view_prob": 0.92, "enroll_prob": 0.65},
    {"id": "C_302", "name": "SQL Essentials for Business", "category": "Business", "search_keywords": ["sql", "database", "data analysis", "business"], "view_prob": 0.80, "enroll_prob": 0.50},
    {"id": "C_401", "name": "Advanced CSS & Sass", "category": "Design", "search_keywords": ["css", "sass", "styling", "frontend", "design"], "view_prob": 0.60, "enroll_prob": 0.40},
    {"id": "C_402", "name": "UI/UX Design Fundamentals", "category": "Design", "search_keywords": ["ui/ux", "figma", "design", "wireframe"], "view_prob": 0.88, "enroll_prob": 0.15}, # High views, low enrollment!
    {"id": "C_501", "name": "Digital Marketing Masterclass", "category": "Marketing", "search_keywords": ["marketing", "seo", "ads", "social media"], "view_prob": 0.35, "enroll_prob": 0.22}
]

# All possible search keywords
all_keywords = []
for c in courses:
    all_keywords.extend(c["search_keywords"])
all_keywords = list(set(all_keywords))
all_keywords.extend(["coding", "web dev", "developer", "analytics", "tutorial", "course", "learn code", "free course"])

# Base timeline
start_date = datetime(2026, 7, 1)
end_date = datetime(2026, 7, 31)
total_days = (end_date - start_date).days + 1

# Generate event log
events = []
user_counter = 1000

for day_offset in range(total_days):
    current_day = start_date + timedelta(days=day_offset)
    
    # Let's say there are more interactions on weekdays than weekends
    is_weekend = current_day.weekday() >= 5
    num_sessions = random.randint(30, 60) if not is_weekend else random.randint(15, 30)
    
    for _ in range(num_sessions):
        user_counter += 1
        user_id = f"U_{user_counter}"
        
        # Decide starting action
        # 70% start with a search, 30% start with a direct view of a random course
        start_with_search = random.random() < 0.70
        
        # Generate session timestamp
        # Peak hours: 10:00 - 13:00 and 18:00 - 22:00
        hour_prob = [0.01, 0.01, 0.01, 0.01, 0.01, 0.02, 0.03, 0.04, 0.06, 0.08, 
                     0.10, 0.09, 0.07, 0.05, 0.04, 0.04, 0.05, 0.07, 0.09, 0.10, 
                     0.06, 0.03, 0.02, 0.01]
        hour_prob = np.array(hour_prob) / sum(hour_prob)
        hour = np.random.choice(range(24), p=hour_prob)
        minute = random.randint(0, 59)
        second = random.randint(0, 59)
        session_time = current_day.replace(hour=hour, minute=minute, second=second)
        
        selected_keyword = ""
        matched_course = None
        
        if start_with_search:
            # Pick a keyword
            # 80% search for keywords associated with courses, 20% general
            if random.random() < 0.80:
                matched_course = random.choice(courses)
                selected_keyword = random.choice(matched_course["search_keywords"])
            else:
                selected_keyword = random.choice(all_keywords)
                
            events.append({
                "timestamp": session_time.strftime("%Y-%m-%d %H:%M:%S"),
                "user_id": user_id,
                "action": "search",
                "search_keyword": selected_keyword,
                "course_id": "",
                "course_name": "",
                "category": ""
            })
            
            # Search duration gap
            session_time += timedelta(seconds=random.randint(15, 90))
            
            # Will user click a course after search?
            if matched_course and random.random() < matched_course["view_prob"]:
                # Click and view
                events.append({
                    "timestamp": session_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "user_id": user_id,
                    "action": "view",
                    "search_keyword": selected_keyword,
                    "course_id": matched_course["id"],
                    "course_name": matched_course["name"],
                    "category": matched_course["category"]
                })
                
                # View duration gap
                session_time += timedelta(seconds=random.randint(45, 300))
                
                # Will user enroll?
                if random.random() < matched_course["enroll_prob"]:
                    events.append({
                        "timestamp": session_time.strftime("%Y-%m-%d %H:%M:%S"),
                        "user_id": user_id,
                        "action": "enroll",
                        "search_keyword": selected_keyword,
                        "course_id": matched_course["id"],
                        "course_name": matched_course["name"],
                        "category": matched_course["category"]
                    })
        else:
            # Direct view
            matched_course = random.choice(courses)
            events.append({
                "timestamp": session_time.strftime("%Y-%m-%d %H:%M:%S"),
                "user_id": user_id,
                "action": "view",
                "search_keyword": "",
                "course_id": matched_course["id"],
                "course_name": matched_course["name"],
                "category": matched_course["category"]
            })
            
            # View duration gap
            session_time += timedelta(seconds=random.randint(45, 300))
            
            # Will user enroll?
            if random.random() < matched_course["enroll_prob"]:
                events.append({
                    "timestamp": session_time.strftime("%Y-%m-%d %H:%M:%S"),
                    "user_id": user_id,
                    "action": "enroll",
                    "search_keyword": "",
                    "course_id": matched_course["id"],
                    "course_name": matched_course["name"],
                    "category": matched_course["category"]
                })

# Create dataframe
df = pd.DataFrame(events)

# Let's inject some anomalies for cleaning verification
# 1. A few duplicate rows
duplicates = df.sample(n=25, random_state=42)
df = pd.concat([df, duplicates], ignore_index=True)

# 2. Some missing values in course_name and category for view/enroll action (e.g. 10 rows)
missing_indices = df[(df["action"].isin(["view", "enroll"])) & (df["course_name"].notna()) & (df["course_name"] != "")].sample(n=10, random_state=42).index
for idx in missing_indices:
    # 50% blank out course_name, 50% blank out category
    if random.random() < 0.5:
        df.at[idx, "course_name"] = ""
    else:
        df.at[idx, "category"] = ""

# Sort by timestamp to keep chronological order
df["timestamp_dt"] = pd.to_datetime(df["timestamp"])
df = df.sort_values("timestamp_dt").drop(columns=["timestamp_dt"])

# Save to datasets/sample_dataset.csv
output_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "sample_dataset.csv")
df.to_csv(output_path, index=False)
print(f"Sample dataset generated successfully at: {output_path}")
print(f"Total rows: {len(df)}")
print(f"Action counts:\n{df['action'].value_counts()}")
