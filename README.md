# 📊 Edu Analysis

A production-ready data engineering project that analyzes user engagement on an online learning platform to understand why highly viewed courses fail to convert into active enrollments.

---

## 📖 Problem Statement

An online learning platform tracks search queries, course preview clicks, and enrollment behaviour, but no analysis explains why highly viewed courses still fail to convert into active enrollments.

The objective of this project is to build a modular data processing pipeline that cleans raw engagement data, generates processed datasets, and prepares the foundation for business insights and reporting.

---

## 🎯 Project Objectives

- Read raw course engagement data
- Clean and preprocess the dataset
- Remove duplicate and invalid records
- Handle missing values
- Generate processed datasets
- Produce reports for further analysis
- Follow production-ready Python scripting practices
- Maintain modular, reusable, and well-documented code

---

## 📂 Project Structure

```
Edu-Analysis/
│
├── data/
│   ├── raw/
│   │   └── course_engagement.csv
│   │
│   └── processed/
│       └── clean_course_engagement.csv
│
├── logs/
│   └── workflow.log
│
├── reports/
│   └── analysis_report.txt
│
├── scripts/
│   ├── ingest.py
│   ├── process.py
│   ├── output.py
│   └── main.py
│
├── requirements.txt
├── README.md
└── .gitignore
```

---

## 🚀 Features

- Modular Python scripts
- Data ingestion
- Data cleaning and preprocessing
- Reusable string cleaning pipeline for whitespace, casing, regex cleanup, and label standardization
- Datetime parsing with temporal feature extraction and weekly time-series aggregation
- Statistical outlier detection (IQR and Z-score) with cap/remove/flag strategies and audit logs
- Duplicate removal
- Missing value handling
- Logging support
- Error handling
- Processed CSV generation
- Report generation

---

## 🛠️ Technologies Used

- Python
- Pandas
- Logging Module

---

## ⚙️ Installation

### 1. Clone the repository

```bash
git clone <repository-url>
```

### 2. Navigate to the project

```bash
cd Edu-Analysis
```

### 3. Create a virtual environment

```bash
python -m venv venv
```

### 4. Activate the virtual environment

**Windows**

```bash
venv\Scripts\activate
```

**Linux / macOS**

```bash
source venv/bin/activate
```

### 5. Install dependencies

```bash
pip install -r requirements.txt
```

---

## ▶️ Run the Project

```bash
python scripts/main.py
```

---

## 📁 Output

Running the project generates:

- Cleaned dataset
- Workflow log
- Analysis report

Generated files:

```
data/processed/clean_course_engagement.csv

logs/workflow.log

reports/analysis_report.txt
```

---

## 📈 Current Workflow

```
Raw CSV
    │
    ▼
Ingest Data
    │
    ▼
Process Data
    │
    ▼
Generate Output
    │
    ▼
Save Cleaned Data & Report
```

The processing step now includes reusable text normalization so that messy values such as extra spaces, mixed casing, and spelling variants are cleaned consistently before aggregation.

---

## 📌 future tasks

- Business analytics dashboard
- Data visualization
- SQL database integration
- Interactive reporting
- API integration
- Machine learning based enrollment prediction

