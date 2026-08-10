# 📊 CourseInsight – Course Enrollment Analytics Platform

## 📌 Problem Statement

Online learning platforms collect valuable data such as search queries, course preview clicks, and enrollment records. However, despite some courses receiving a large number of views, many fail to convert those views into actual enrollments. Without proper analysis, administrators cannot identify where users drop off in the enrollment process or make data-driven decisions to improve course performance.

**CourseInsight** is a Data Science-based Streamlit web application that analyzes course engagement data, calculates key performance indicators (KPIs), and presents meaningful business insights through interactive Plotly visualizations.

---

## 🎯 Project Objectives

* Analyze user engagement data from an online learning platform.
* Identify courses with high views but low enrollments.
* Calculate important business KPIs and conversion metrics.
* Perform Exploratory Data Analysis (EDA) — correlation, outliers, rolling trends.
* Visualize insights using 6 interactive Plotly charts.
* Allow users to upload and analyze their own datasets (CSV / Excel).
* Auto-clean datasets and rebuild the analytics database.
* Generate rule-based actionable business insights — no Machine Learning required.

---

## 🚀 Tech Stack

| Layer | Technologies |
|---|---|
| **UI / Frontend** | Streamlit, HTML/CSS (inline for custom cards) |
| **Backend / Data Layer** | Python, SQLAlchemy ORM, PostgreSQL |
| **Analytics** | Pandas, NumPy, Plotly |
| **Auth** | Bcrypt (password hashing), python-jose (JWT) |
| **Config** | python-dotenv (`.env`) |

---

## 📂 Project Structure

```text
CourseInsight/
│
├── app.py                      # Main Streamlit application (sole entrypoint)
│
├── backend/
│   ├── database/
│   │   └── db.py               # SQLAlchemy engine, session, get_db() helper
│   ├── models/
│   │   └── models.py           # ORM models: User, Dataset, DatasetMetadata,
│   │                           #   Category, SearchData, CourseView, Enrollment
│   └── services/
│       └── auth_service.py     # get_password_hash(), verify_password(), JWT helpers
│
├── analytics/
│   ├── analysis.py             # get_kpis(), get_course_performance(),
│   │                           #   get_search_analytics(), get_category_analysis(),
│   │                           #   get_time_trends(), get_business_insights(),
│   │                           #   get_advanced_eda_metrics()
│   ├── charts.py               # get_funnel_chart(), get_category_bar_chart(),
│   │                           #   get_time_line_chart(), get_views_vs_enrollments_scatter(),
│   │                           #   get_category_pie_chart(), get_hourly_heatmap()
│   └── utils.py                # parse_file_to_df(), generate_dataset_metadata(),
│                               #   clean_dataframe(), populate_db_tables_from_df()
│
├── datasets/
│   ├── sample_dataset.csv      # Pre-loaded sample interaction log dataset
│   ├── generate_sample.py      # Script to regenerate sample_dataset.csv
│   └── uploads/                # Uploaded user dataset files (auto-created)
│
├── .streamlit/
│   └── config.toml             # Enforces light theme (primaryColor, backgroundColor)
│
├── .env                        # DATABASE_URL, JWT_SECRET (gitignored)
├── .env.example                # Template showing required env vars
├── verify_app.py               # Checks all imports and DB table compilation
├── reset_db.py                 # Drops and recreates all database tables
├── courseinsight.db            # SQLite database file (auto-created on first run)
└── README.md
```

---

## 📑 Pages & UI Flow

### 🏠 Page 1 — Landing Home Page (`auth_view = "home"`)
Shown to all unauthenticated users.

**Content:**
* Large branded header with a one-line value proposition.
* Two call-to-action buttons:
  * **🔑 Sign In to Dashboard** → navigates to the Login form page.
  * **📝 Create an Account** → navigates to the Register form page.
* Two-column informational grid:
  * **Left**: What is CourseInsight? + Key benefits & use cases.
  * **Right**: How It Works — 4-step numbered guide.

---

### 🔑 Page 2 — Login Page (`auth_view = "login"`)
* Back to Home button.
* Styled form with Username and Password fields.
* On success: seeds sample dataset for the user if missing, sets active dataset, redirects to dashboard.
* On failure: displays error message.

---

### 📝 Page 3 — Register Page (`auth_view = "register"`)
* Back to Home button.
* Styled form with Username, Email, and Password fields.
* Full **password strength validation**:
  * Minimum 8 characters
  * At least one uppercase letter
  * At least one lowercase letter
  * At least one digit
  * At least one special character (`!@#$%^&*` etc.)
* On success: creates user, seeds `sample_dataset.csv`, auto-redirects to Login page.
* On failure: shows specific validation error message.

---

### 📊 Page 4 — Main Dashboard (Logged-in state)

Shown after login. Contains a **Sidebar** and **4 main tabs**.

#### Sidebar (persistent across all tabs)
* Welcome message with the logged-in username.
* **📂 Active Dataset dropdown** — switch between all uploaded datasets on the fly. Switching rebuilds the analytics SQL tables automatically.
* **🚪 Logout button** — clears session state and returns to landing page.

#### Header
* "📊 CourseInsight Platform" title.
* Active dataset filename shown as a subtitle.

---

#### Tab 1 — 📈 Analytics Dashboard

**Filters (applied to all KPIs and charts):**
* Category filter (dropdown of all unique categories in the dataset)
* Course filter (dropdown of all unique course names)
* Date range filter (date picker, auto-bounds to dataset's min/max timestamps)

**KPI Cards (Row 1 — 4 columns):**
| Card | What it shows |
|---|---|
| Total Searches | Count of all search action rows |
| Course Views | Count of all view action rows |
| Enrollments | Count of all enrollment action rows |
| Overall Conversion | `enrollments / views * 100` (%) |

**KPI Cards (Row 2 — 3 columns):**
| Card | What it shows |
|---|---|
| Avg Views / Course | Mean views across all unique courses |
| Highest Viewed Course | Course name with the most views |
| Lowest Conversion Course | Course name with the lowest view-to-enroll rate |

**Plotly Charts (3 rows × 2 columns):**
| Chart | Type | Description |
|---|---|---|
| Enrollment Conversion Funnel | Funnel | Searches → Views → Enrollments pipeline |
| Views & Enrollments by Category | Grouped Bar | Side-by-side comparison per category |
| Daily Activity Trends | Line | Views and enrollments plotted over time |
| Views vs Enrollments per Course | Scatter | Each dot = one course |
| Category Share | Pie | Slice breakdown of enrollment share per category |
| Hourly Activity Heatmap | Heatmap | Day-of-week × Hour-of-day activity grid |

---

#### Tab 2 — 🧹 Data Cleaning & Preview

**Dataset Overview (4 metric cards):**
* Total Rows, Total Columns, Duplicate Row Count, Total Missing Cell Count.

**Column Inspector (Table):**
* Column Name, Data Type, Missing Value Count, Unique Value Count — for every column.

**Row Preview:**
* First 10 rows of the active dataset displayed as a dataframe.

**Data Cleaning Form:**
* Missing Values Strategy (dropdown):
  * *Drop rows with missing values* — removes rows where vital columns are empty.
  * *Fill with default placeholders* — fills missing cells with sensible defaults.
  * *Fill NaN only* — simple fillna with empty string.
* Remove duplicate rows (checkbox, default on).
* Standardize column values — applies Title Case to course names and categories (checkbox, default on).
* **🧹 Run Dataset Cleaning** button — cleans data, overwrites the file on disk, updates DB metadata, and rebuilds all analytics SQL log tables automatically.

---

#### Tab 3 — 🔬 Advanced Stats & Insights

**EDA Section (2 columns):**

*Left — Correlation Analysis:*
* Pearson Correlation Coefficient between views and enrollments (per course).
* Relationship strength label (Very Strong / Moderate / Weak / Negligible).
* Interpretation guide for correlation values.

*Right — Time-Series Outlier Detection:*
* IQR-based anomalous day detection — flags dates with unusually high or low view counts.
* Table showing: Date, Views Count, Anomaly Status, Lower Bound (IQR), Upper Bound (IQR).
* If no outliers found, shows info message.

**Business Insights Section:**
* Automatically generated rule-based insight cards:
  * Courses with high views but low enrollments (high impression, low conversion).
  * Categories with the highest conversion rates.
  * Frequently searched keywords with poor enrollment outcomes.
  * Peak enrollment hour identification.
  * Other dataset-specific patterns.
* Each insight card shows a title and a descriptive explanation.

**Share Report (Mock):**
* Email input field.
* On submit: shows `"Dummy Email sent successfully to {email}!"` success message.

---

#### Tab 4 — 📤 Dataset Manager

**Upload New Dataset:**
* File uploader accepting `.csv`, `.xlsx`, `.xls`.
* Warning shown if a file with the same name already exists.
* **🚀 Upload & Analyze Dataset** button:
  * Saves file to `datasets/uploads/` with a unique timestamped filename.
  * Parses file, generates metadata, creates DB records.
  * Automatically sets uploaded file as the active dataset.
  * Rebuilds analytics SQL log tables for the new dataset.

**Your Uploaded Datasets (List):**
Each dataset row shows:
* Filename + upload timestamp.
* Row count + Column count.
* 🟢 Active / ⚪ Inactive status badge.
* Action buttons:
  * **🔌 Activate** — sets the dataset as active, rebuilds analytics tables.
  * **🗑️ Delete** — removes file from disk and all DB records.
  * **📥 Export** — download the current version of the dataset as CSV.

---

## 🗄 Database Schema

| Table | Columns (key ones) | Purpose |
|---|---|---|
| `users` | id, username, email, hashed_password | Registered user accounts |
| `datasets` | id, filename, filepath, uploaded_by_user_id, row_count, col_count, is_active | Dataset file registry |
| `dataset_metadata` | dataset_id, columns_json, duplicate_count, missing_count | Per-dataset column info |
| `categories` | dataset_id, name | Unique categories per dataset |
| `search_data` | dataset_id, timestamp, user_id, search_keyword, course_id | Search action log rows |
| `course_views` | dataset_id, timestamp, user_id, course_id, course_name, category | View action log rows |
| `enrollments` | dataset_id, timestamp, user_id, course_id, course_name, category | Enrollment action log rows |

---

## 🔄 Application Workflow

```text
Open App
   │
   ▼
🏠 Landing Home Page
   │
   ├──► 🔑 Login Page ──► Authenticate ──► Seed sample dataset (if new)
   │                                                │
   └──► 📝 Register Page ──► Create Account ──►────┘
                                                    │
                                                    ▼
                                          📊 Dashboard (4 Tabs)
                                          │
                                          ├── 📈 Analytics Dashboard
                                          │       Filters → KPI Cards → 6 Plotly Charts
                                          │
                                          ├── 🧹 Data Cleaning & Preview
                                          │       Overview → Column Info → Row Preview → Clean
                                          │
                                          ├── 🔬 Advanced Stats & Insights
                                          │       Correlation → Outliers → Business Insights → Share
                                          │
                                          └── 📤 Dataset Manager
                                                  Upload → List → Activate / Delete / Export
```

---

## ⚙️ Setup & How to Run

### 1. Prerequisites
Python **3.8+** installed on your system.

### 2. Install Dependencies
```bash
pip install pandas numpy plotly sqlalchemy python-dotenv streamlit bcrypt "python-jose[cryptography]" openpyxl
```

### 3. Configure Environment Variables
Copy `.env.example` to `.env`:
```bash
copy .env.example .env
```

Edit `.env`:
```env
# Use SQLite (no setup required — recommended for local development)
DATABASE_URL=sqlite:///./courseinsight.db

# JWT secret key — replace with any secure random string
JWT_SECRET=your_random_secret_key_here
```

> For PostgreSQL: `DATABASE_URL=postgresql://username:password@localhost:5432/courseinsight`

### 4. Verify Setup
```bash
python verify_app.py
```
Expected output: `All checks PASSED successfully!`

### 5. Run the Application
```bash
streamlit run app.py
```

### 6. Open in Browser
**[http://localhost:8501](http://localhost:8501)**

Register a new account — the platform automatically loads `sample_dataset.csv` for you, ready to explore!

---

## 🛠 Utility Scripts

| Script | Command | Purpose |
|---|---|---|
| `verify_app.py` | `python verify_app.py` | Verify all imports and DB table compilation |
| `reset_db.py` | `python reset_db.py` | Drop and recreate all database tables (use after schema changes) |
| `datasets/generate_sample.py` | `python datasets/generate_sample.py` | Regenerate `sample_dataset.csv` |

---

## 🌐 Deployment (Optional)

| Service | Purpose |
|---|---|
| **Render** | Host the Streamlit application |
| **Supabase PostgreSQL** | Cloud PostgreSQL database |

---

## 👨‍💻 Author

**CourseInsight** is a Data Science Analytics project built with **Python, Streamlit, SQLAlchemy, Pandas, NumPy, and Plotly**. The platform analyzes course engagement data, visualizes conversion trends, and provides rule-based business insights to help improve course enrollment performance.
