"""
generate_data.py
Run this file if you don't have the Kaggle CSV.
It creates 2000 realistic fake student records.

Usage:  python generate_data.py
"""

import pandas as pd
import numpy as np
import os


def generate_sample_data(n_students=2000, output_file="data/student_performance.csv"):
    np.random.seed(42)

    hours_studied   = np.random.randint(1, 44, n_students)
    attendance      = np.random.uniform(60, 100, n_students).round(1)
    previous_scores = np.random.uniform(50, 100, n_students).round(1)

    # Exam score is influenced by study hours, attendance, and previous performance
    exam_score = (
        0.30 * hours_studied +
        0.30 * (attendance / 100) * 100 +
        0.30 * previous_scores +
        np.random.normal(0, 5, n_students)
    )
    exam_score = np.clip(exam_score, 0, 100).round(1)

    data = {
        "Hours_Studied":              hours_studied,
        "Attendance":                 attendance,
        "Parental_Involvement":       np.random.choice(["Low", "Medium", "High"], n_students),
        "Access_to_Resources":        np.random.choice(["Low", "Medium", "High"], n_students),
        "Extracurricular_Activities": np.random.choice(["Yes", "No"], n_students),
        "Sleep_Hours":                np.random.uniform(4, 10, n_students).round(1),
        "Previous_Scores":            previous_scores,
        "Motivation_Level":           np.random.choice(["Low", "Medium", "High"], n_students),
        "Internet_Access":            np.random.choice(["Yes", "No"], n_students, p=[0.85, 0.15]),
        "Tutoring_Sessions":          np.random.randint(0, 9, n_students),
        "Family_Income":              np.random.choice(["Low", "Medium", "High"], n_students),
        "Teacher_Quality":            np.random.choice(["Low", "Medium", "High"], n_students),
        "School_Type":                np.random.choice(["Public", "Private"], n_students, p=[0.7, 0.3]),
        "Physical_Activity":          np.random.randint(0, 7, n_students),
        "Learning_Disabilities":      np.random.choice(["Yes", "No"], n_students, p=[0.1, 0.9]),
        "Parental_Education_Level":   np.random.choice(["High School", "College", "Postgraduate"], n_students),
        "Distance_from_Home":         np.random.choice(["Near", "Moderate", "Far"], n_students),
        "Gender":                     np.random.choice(["Male", "Female"], n_students),
        "Sports":                     np.random.choice(["Yes", "No"], n_students),
        "Music":                      np.random.choice(["Yes", "No"], n_students),
        "Volunteering":               np.random.choice(["Yes", "No"], n_students),
        "Exam_Score":                 exam_score,
    }

    df = pd.DataFrame(data)
    os.makedirs(os.path.dirname(output_file), exist_ok=True)
    df.to_csv(output_file, index=False)
    print(f"Generated {n_students} student records and saved to {output_file}")
    return df


if __name__ == "__main__":
    generate_sample_data()
