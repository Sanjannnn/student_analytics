"""
etl.py  —  Student Analytics ETL Pipeline
Connects to Azure SQL Database, creates the star schema tables,
then Extracts, Transforms, and Loads student performance data.

Usage:  python etl.py
"""

import pyodbc
import pandas as pd
import os
import random
from datetime import datetime

from config import CONNECTION_STRING

DATA_FILE = "data/student_performance.csv"


# Connecting to Azure

def connect_db():
    print("Connecting to Azure SQL Database...")
    conn = pyodbc.connect(CONNECTION_STRING)
    print("Connected successfully!")
    return conn


# Creating Tables

def create_tables(conn):
    cursor = conn.cursor()

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='dim_Student' AND xtype='U')
        CREATE TABLE dim_Student (
            Student_Key              INT          IDENTITY(1,1) PRIMARY KEY,
            Student_ID               NVARCHAR(15) NOT NULL UNIQUE,
            Family_Income            NVARCHAR(10) CHECK (Family_Income IN ('Low','Medium','High')),
            Parental_Education_Level NVARCHAR(25) CHECK (Parental_Education_Level IN ('High School','College','Postgraduate')),
            Gender                   NVARCHAR(15) CHECK (Gender IN ('Male','Female','Non-binary','Other')),
            Distance_from_Home       NVARCHAR(10) CHECK (Distance_from_Home IN ('Near','Moderate','Far'))
        )
    """)

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='dim_Lifestyle' AND xtype='U')
        CREATE TABLE dim_Lifestyle (
            Lifestyle_Key              INT   IDENTITY(1,1) PRIMARY KEY,
            Weekly_Hours_Studied       INT   CHECK (Weekly_Hours_Studied BETWEEN 0 AND 168),
            Extracurricular_Activities BIT,
            Sports                     BIT,
            Music                      BIT,
            Volunteering               BIT,
            Sleep_Hours                FLOAT CHECK (Sleep_Hours BETWEEN 0 AND 24)
        )
    """)

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='dim_Support' AND xtype='U')
        CREATE TABLE dim_Support (
            Support_Key           INT          IDENTITY(1,1) PRIMARY KEY,
            Access_to_Resources   NVARCHAR(10) CHECK (Access_to_Resources IN ('Low','Medium','High')),
            Tutoring_Sessions     INT          CHECK (Tutoring_Sessions >= 0),
            Teacher_Quality       NVARCHAR(10) CHECK (Teacher_Quality IN ('Low','Medium','High')),
            Parental_Involvement  NVARCHAR(10) CHECK (Parental_Involvement IN ('Low','Medium','High')),
            Internet_Access       BIT,
            Learning_Disabilities BIT
        )
    """)

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='dim_School' AND xtype='U')
        CREATE TABLE dim_School (
            School_Key  INT          IDENTITY(1,1) PRIMARY KEY,
            School_Type NVARCHAR(10) CHECK (School_Type IN ('Public','Private'))
        )
    """)

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='dim_Date' AND xtype='U')
        CREATE TABLE dim_Date (
            Date_Key  INT          IDENTITY(1,1) PRIMARY KEY,
            Full_Date DATE,
            Year      INT,
            Month     INT,
            Day       INT,
            Term      NVARCHAR(10)
        )
    """)

    cursor.execute("""
        IF NOT EXISTS (SELECT * FROM sysobjects WHERE name='fact_Performance' AND xtype='U')
        CREATE TABLE fact_Performance (
            Performance_Key   INT          IDENTITY(1,1) PRIMARY KEY,
            Student_Key       INT          FOREIGN KEY REFERENCES dim_Student(Student_Key),
            Lifestyle_Key     INT          FOREIGN KEY REFERENCES dim_Lifestyle(Lifestyle_Key),
            Support_Key       INT          FOREIGN KEY REFERENCES dim_Support(Support_Key),
            School_Key        INT          FOREIGN KEY REFERENCES dim_School(School_Key),
            Date_Key          INT          FOREIGN KEY REFERENCES dim_Date(Date_Key),
            Attendance_Rate   FLOAT        CHECK (Attendance_Rate BETWEEN 0 AND 100),
            Previous_Score    FLOAT        CHECK (Previous_Score BETWEEN 0 AND 100),
            Exam_Score        FLOAT        CHECK (Exam_Score BETWEEN 0 AND 100),
            Motivation_Level  NVARCHAR(10) CHECK (Motivation_Level IN ('Low','Medium','High')),
            Stress_Level      NVARCHAR(10) CHECK (Stress_Level IN ('Low','Medium','High')),
            Physical_Activity INT          CHECK (Physical_Activity >= 0)
        )
    """)

    conn.commit()
    print("All tables created (or already existed).")


# Read the CSV

def extract_data(csv_file=DATA_FILE):
    if not os.path.exists(csv_file):
        print(f"No CSV found at '{csv_file}'. Generating sample data...")
        import generate_data
        generate_data.generate_sample_data()

    df = pd.read_csv(csv_file)
    print(f"Extracted {len(df)} rows from '{csv_file}'")
    return df


# Transform Data

def transform_data(df):
    print("Transforming data...")

    # Rename Kaggle column names to match our Part 1 schema
    rename_map = {
        "Hours_Studied":   "Weekly_Hours_Studied",
        "Attendance":      "Attendance_Rate",
        "Previous_Scores": "Previous_Score",
    }
    df = df.rename(columns=rename_map)

    # Fill missing numbers with the median
    numeric_cols = [
        "Weekly_Hours_Studied", "Attendance_Rate", "Previous_Score",
        "Sleep_Hours", "Physical_Activity", "Exam_Score", "Tutoring_Sessions"
    ]
    for col in numeric_cols:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].median())

    # Clamp scores and rates to valid ranges
    for col in ["Exam_Score", "Previous_Score", "Attendance_Rate"]:
        if col in df.columns:
            df[col] = df[col].clip(0, 100)

    # Fill missing text columns with the most common value
    cat_cols = [
        "Gender", "Family_Income", "Parental_Education_Level", "Distance_from_Home",
        "Access_to_Resources", "Teacher_Quality", "Parental_Involvement",
        "School_Type", "Motivation_Level", "Stress_Level"
    ]
    for col in cat_cols:
        if col in df.columns:
            df[col] = df[col].fillna(df[col].mode()[0])

    # Add a Stress_Level column if the Kaggle dataset doesn't have it
    if "Stress_Level" not in df.columns:
        df["Stress_Level"] = "Medium"

    # Convert Yes/No columns to 1/0 (SQL BIT type needs integers)
    yes_no_cols = [
        "Extracurricular_Activities", "Sports", "Music",
        "Volunteering", "Internet_Access", "Learning_Disabilities"
    ]
    for col in yes_no_cols:
        if col in df.columns:
            df[col] = df[col].map({"Yes": 1, "No": 0}).fillna(0).astype(int)

    # Add any missing boolean columns as 0
    for col in ["Sports", "Music", "Volunteering"]:
        if col not in df.columns:
            df[col] = 0
    if "Internet_Access" not in df.columns:
        df["Internet_Access"] = 1
    if "Learning_Disabilities" not in df.columns:
        df["Learning_Disabilities"] = 0

    # Generate unique Student IDs (STU0010001, STU0010002, ...)
    df["Student_ID"] = ["STU" + str(i + 10001).zfill(7) for i in range(len(df))]

    # Assign random dates in the 2024 NSW school year
    term_dates = {
        "Term 1": ("2024-01-29", "2024-04-12"),
        "Term 2": ("2024-04-29", "2024-07-05"),
        "Term 3": ("2024-07-22", "2024-09-27"),
        "Term 4": ("2024-10-14", "2024-12-20"),
    }
    random.seed(42)
    dates, terms = [], []
    for _ in range(len(df)):
        term = random.choice(list(term_dates.keys()))
        start = datetime.strptime(term_dates[term][0], "%Y-%m-%d")
        end   = datetime.strptime(term_dates[term][1], "%Y-%m-%d")
        rand_date = start + pd.Timedelta(days=random.randint(0, (end - start).days))
        dates.append(rand_date.date())
        terms.append(term)

    df["Full_Date"] = dates
    df["Term"]      = terms
    df["Year"]      = 2024
    df["Month"]     = [d.month for d in dates]
    df["Day"]       = [d.day   for d in dates]

    print(f"Transformation done. {len(df)} rows ready to load.")
    return df


# Dimension Helper

def get_or_create_lifestyle(cursor, row):
    cursor.execute("""
        SELECT Lifestyle_Key FROM dim_Lifestyle
        WHERE Weekly_Hours_Studied = ? AND Extracurricular_Activities = ?
          AND Sports = ? AND Music = ? AND Volunteering = ? AND Sleep_Hours = ?
    """, (int(row["Weekly_Hours_Studied"]), int(row["Extracurricular_Activities"]),
          int(row["Sports"]), int(row["Music"]), int(row["Volunteering"]),
          float(row["Sleep_Hours"])))

    result = cursor.fetchone()
    if result:
        return result[0]

    cursor.execute("""
        INSERT INTO dim_Lifestyle
            (Weekly_Hours_Studied, Extracurricular_Activities, Sports, Music, Volunteering, Sleep_Hours)
        OUTPUT INSERTED.Lifestyle_Key
        VALUES (?, ?, ?, ?, ?, ?)
    """, (int(row["Weekly_Hours_Studied"]), int(row["Extracurricular_Activities"]),
          int(row["Sports"]), int(row["Music"]), int(row["Volunteering"]),
          float(row["Sleep_Hours"])))
    return cursor.fetchone()[0]


def get_or_create_support(cursor, row):
    cursor.execute("""
        SELECT Support_Key FROM dim_Support
        WHERE Access_to_Resources = ? AND Tutoring_Sessions = ?
          AND Teacher_Quality = ? AND Parental_Involvement = ?
          AND Internet_Access = ? AND Learning_Disabilities = ?
    """, (str(row["Access_to_Resources"]), int(row["Tutoring_Sessions"]),
          str(row["Teacher_Quality"]), str(row["Parental_Involvement"]),
          int(row["Internet_Access"]), int(row["Learning_Disabilities"])))

    result = cursor.fetchone()
    if result:
        return result[0]

    cursor.execute("""
        INSERT INTO dim_Support
            (Access_to_Resources, Tutoring_Sessions, Teacher_Quality,
             Parental_Involvement, Internet_Access, Learning_Disabilities)
        OUTPUT INSERTED.Support_Key
        VALUES (?, ?, ?, ?, ?, ?)
    """, (str(row["Access_to_Resources"]), int(row["Tutoring_Sessions"]),
          str(row["Teacher_Quality"]), str(row["Parental_Involvement"]),
          int(row["Internet_Access"]), int(row["Learning_Disabilities"])))
    return cursor.fetchone()[0]


def get_or_create_school(cursor, school_type):
    cursor.execute("SELECT School_Key FROM dim_School WHERE School_Type = ?", (school_type,))
    result = cursor.fetchone()
    if result:
        return result[0]

    cursor.execute("""
        INSERT INTO dim_School (School_Type)
        OUTPUT INSERTED.School_Key
        VALUES (?)
    """, (school_type,))
    return cursor.fetchone()[0]


def get_or_create_date(cursor, row):
    cursor.execute("SELECT Date_Key FROM dim_Date WHERE Full_Date = ?", (str(row["Full_Date"]),))
    result = cursor.fetchone()
    if result:
        return result[0]

    cursor.execute("""
        INSERT INTO dim_Date (Full_Date, Year, Month, Day, Term)
        OUTPUT INSERTED.Date_Key
        VALUES (?, ?, ?, ?, ?)
    """, (str(row["Full_Date"]), int(row["Year"]), int(row["Month"]),
          int(row["Day"]), str(row["Term"])))
    return cursor.fetchone()[0]


# Loading the Data

def load_data(conn, df):
    print("Loading data into Azure SQL Database...")
    cursor = conn.cursor()

    # Delete existing data first so re-running this script never creates duplicates (NFR 2.3.03)
    print("Clearing old data...")
    cursor.execute("DELETE FROM fact_Performance")
    cursor.execute("DELETE FROM dim_Student")
    cursor.execute("DELETE FROM dim_Lifestyle")
    cursor.execute("DELETE FROM dim_Support")
    cursor.execute("DELETE FROM dim_School")
    cursor.execute("DELETE FROM dim_Date")
    conn.commit()

    print(f"Inserting {len(df)} rows...")

    for i, row in df.iterrows():
        # Insert the student into dim_Student and get back their key
        cursor.execute("""
            INSERT INTO dim_Student
                (Student_ID, Family_Income, Parental_Education_Level, Gender, Distance_from_Home)
            OUTPUT INSERTED.Student_Key
            VALUES (?, ?, ?, ?, ?)
        """, (str(row["Student_ID"]), str(row["Family_Income"]),
              str(row["Parental_Education_Level"]), str(row["Gender"]),
              str(row["Distance_from_Home"])))
        student_key = cursor.fetchone()[0]

        # Get (or create) keys for each dimension table
        lifestyle_key = get_or_create_lifestyle(cursor, row)
        support_key   = get_or_create_support(cursor, row)
        school_key    = get_or_create_school(cursor, str(row["School_Type"]))
        date_key      = get_or_create_date(cursor, row)

        # Insert the fact record linking all dimension keys
        cursor.execute("""
            INSERT INTO fact_Performance
                (Student_Key, Lifestyle_Key, Support_Key, School_Key, Date_Key,
                 Attendance_Rate, Previous_Score, Exam_Score,
                 Motivation_Level, Stress_Level, Physical_Activity)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (student_key, lifestyle_key, support_key, school_key, date_key,
              float(row["Attendance_Rate"]), float(row["Previous_Score"]),
              float(row["Exam_Score"]),      str(row["Motivation_Level"]),
              str(row["Stress_Level"]),      int(row["Physical_Activity"])))

        # Save to the database every 100 rows
        if (i + 1) % 100 == 0:
            conn.commit()
            print(f"  {i + 1} / {len(df)} rows loaded...")

    conn.commit()
    print(f"Load complete! {len(df)} student records are now in Azure SQL Database.")


# Run ETL pipeline

def run_etl():
    print("=" * 55)
    print("  STUDENT ANALYTICS — ETL PIPELINE")
    print("=" * 55)

    conn = connect_db()
    create_tables(conn)

    df = extract_data()
    df = transform_data(df)
    load_data(conn, df)

    conn.close()
    print("=" * 55)
    print("  ETL complete! Open app.py to view the dashboard.")
    print("=" * 55)


if __name__ == "__main__":
    run_etl()
