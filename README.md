# Student Performance Analytics System (SPAS)

A centralised data warehouse and interactive analytics dashboard built for UTS 41091 Data Systems — Assignment 2.

**Live dashboard:** https://student-analytics-group12.streamlit.app/

---

## System Overview

| Component | Technology |
|---|---|
| Data source | Kaggle student performance CSV (6607 rows) |
| ETL pipeline | Python + pandas + pyodbc |
| Cloud data warehouse | Azure SQL Database (Australia East) |
| Dashboard | Streamlit + Plotly Express |

---

## (a) Provisioning the Azure SQL Database

The database is already provisioned and live:

- **Server:** `studentanalytics2025.database.windows.net`
- **Database:** `StudentAnalytics`
- **Region:** Australia East

If you need to connect from a new machine, add your client IP to the Azure SQL firewall:

1. Go to [https://portal.azure.com](https://portal.azure.com)
2. Search for `studentanalytics2025` → open the **SQL server**
3. Left sidebar → **Networking** → **Add a firewall rule**
4. Enter your IP address → click **Save**

---

## (b) Installing Python Dependencies

Requires Python 3.10 or later.

```bash
pip install -r requirements.txt
```

This installs: `pandas`, `streamlit`, `plotly`, `pymssql`

> **Note:** The ETL script (`etl.py`) additionally requires **ODBC Driver 18 for SQL Server** installed at the OS level.
> Download: https://learn.microsoft.com/en-us/sql/connect/odbc/download-odbc-driver-for-sql-server

---

## (c) Running the ETL Pipeline

Populates the Azure SQL warehouse from the source CSV.

```bash
python etl.py
```

**What it does:**
1. Connects to Azure SQL Database
2. Creates the star schema tables if they do not exist (5 dimensions + 1 fact table)
3. Reads `data/student_performance.csv`
4. Cleans and transforms the data (null imputation, type conversion, date assignment)
5. Loads all records into the warehouse

> If `data/student_performance.csv` is missing, the script automatically generates a 2,000-row synthetic dataset via `generate_data.py`.

> **This only needs to be run once.** Re-running is safe — it clears and reloads the data (idempotent).

---

## (d) Launching the Dashboard

```bash
streamlit run app.py
```

Opens at `http://localhost:8501` in your browser.

The dashboard has 8 pages accessible from the sidebar:

| Page | Description |
|---|---|
| Home Dashboard | KPI summary and score distribution |
| At-Risk Students | 6-factor risk scoring across all students |
| FR 2.2.01 — Student Records | Search and browse student records |
| FR 2.2.02 — Assessment Results | Scores broken down by demographics |
| FR 2.2.03 — Track Student Changes | Exam score improvement vs previous score |
| FR 2.2.04 — Research Query Tool | Filter students by any combination of criteria |
| FR 2.2.05 — Performance Over Time | Trends across NSW school terms |
| FR 2.2.06 — Segmented Results | Average scores by segment (school type, income, etc.) |

---

## Project Structure

```
student_analytics/
├── app.py               # Streamlit dashboard (8 pages)
├── etl.py               # ETL pipeline
├── config.py            # Azure SQL connection settings
├── generate_data.py     # Synthetic data generator (fallback)
├── requirements.txt     # Python dependencies
├── data/
│   └── student_performance.csv
└── .streamlit/
    └── secrets.toml     # Local credentials (not committed to GitHub)
```

---

## Group Members

- Sanjan Neupane
- Shervin Sabu
- Rudra Labh
- Christopher Valenzuela
