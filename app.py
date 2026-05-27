import streamlit as st
import pymssql
import pandas as pd
import plotly.express as px

from config import SERVER, DATABASE, USERNAME, PASSWORD

st.set_page_config(page_title="Student Performance Analytics", layout="wide")


def run_query(query, params=None):
    """Run a SQL query and return results as a pandas DataFrame."""
    conn = pymssql.connect(server=SERVER, user=USERNAME, password=PASSWORD, database=DATABASE)
    cursor = conn.cursor()
    if params:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    columns = [desc[0] for desc in cursor.description]
    rows    = cursor.fetchall()
    conn.close()
    return pd.DataFrame.from_records(rows, columns=columns)


st.sidebar.title("Student Analytics")
st.sidebar.markdown("---")

page = st.sidebar.radio("Navigate to", [
    "Home Dashboard",
    "At-Risk Students",
    "FR 2.2.01 — Student Records",
    "FR 2.2.02 — Assessment Results",
    "FR 2.2.03 — Track Student Changes",
    "FR 2.2.04 — Research Query Tool",
    "FR 2.2.05 — Performance Over Time",
    "FR 2.2.06 — Segmented Results",
])


if page == "Home Dashboard":
    st.title("Student Performance Analytics")
    st.markdown("Use the sidebar to navigate between views.")
    st.markdown("---")

    col1, col2, col3, col4 = st.columns(4)

    total_df     = run_query("SELECT COUNT(*) AS n FROM dim_Student")
    avg_score_df = run_query("SELECT AVG(Exam_Score) AS avg FROM fact_Performance")
    avg_att_df   = run_query("SELECT AVG(Attendance_Rate) AS avg FROM fact_Performance")
    at_risk_df   = run_query("""
        SELECT COUNT(*) AS n FROM fact_Performance f
        JOIN dim_Lifestyle l  ON f.Lifestyle_Key  = l.Lifestyle_Key
        JOIN dim_Support   sp ON f.Support_Key    = sp.Support_Key
        WHERE (CASE WHEN f.Exam_Score < 65           THEN 1 ELSE 0 END +
               CASE WHEN f.Attendance_Rate < 75      THEN 1 ELSE 0 END +
               CASE WHEN l.Weekly_Hours_Studied < 10 THEN 1 ELSE 0 END +
               CASE WHEN f.Motivation_Level = 'Low'  THEN 1 ELSE 0 END +
               CASE WHEN sp.Access_to_Resources = 'Low' THEN 1 ELSE 0 END +
               CASE WHEN sp.Tutoring_Sessions = 0    THEN 1 ELSE 0 END) >= 4
    """)

    col1.metric("Total Students",     int(total_df["n"][0]))
    col2.metric("Avg Exam Score",     f"{float(avg_score_df['avg'][0]):.1f}")
    col3.metric("Avg Attendance (%)", f"{float(avg_att_df['avg'][0]):.1f}")
    col4.metric("High Risk Students", int(at_risk_df["n"][0]), delta="need support", delta_color="inverse")

    st.markdown("---")
    st.subheader("Exam Score Distribution")
    scores_df = run_query("SELECT Exam_Score FROM fact_Performance")
    fig = px.histogram(scores_df, x="Exam_Score", nbins=30,
                       color_discrete_sequence=["#4C78A8"],
                       labels={"Exam_Score": "Exam Score"})
    st.plotly_chart(fig, use_container_width=True)


elif page == "At-Risk Students":
    st.title("At-Risk Student Identifier")
    st.markdown("Students are flagged as at-risk based on a combination of performance and lifestyle factors. Each risk factor adds 1 point — the higher the score, the more support they need.")

    st.markdown("""
    **Risk factors scored:**
    | Factor | At-Risk Threshold |
    |---|---|
    | Exam Score | Below 65 |
    | Attendance Rate | Below 75% |
    | Weekly Study Hours | Below 10 hrs |
    | Motivation Level | Low |
    | Access to Resources | Low |
    | Tutoring Sessions | None (0) |
    """)

    df = run_query("""
        SELECT
            s.Student_ID,
            s.Gender,
            s.Family_Income,
            s.Parental_Education_Level,
            s.Distance_from_Home,
            f.Exam_Score,
            f.Attendance_Rate,
            f.Previous_Score,
            f.Motivation_Level,
            f.Stress_Level,
            l.Weekly_Hours_Studied,
            l.Sleep_Hours,
            sp.Access_to_Resources,
            sp.Tutoring_Sessions,
            sp.Teacher_Quality,
            sp.Parental_Involvement,
            sc.School_Type
        FROM fact_Performance f
        JOIN dim_Student   s  ON f.Student_Key   = s.Student_Key
        JOIN dim_Lifestyle l  ON f.Lifestyle_Key  = l.Lifestyle_Key
        JOIN dim_Support   sp ON f.Support_Key    = sp.Support_Key
        JOIN dim_School    sc ON f.School_Key     = sc.School_Key
    """)

    # Calculate a risk score out of 6
    df["Risk_Score"] = (
        (df["Exam_Score"]          < 65).astype(int) +
        (df["Attendance_Rate"]     < 75).astype(int) +
        (df["Weekly_Hours_Studied"] < 10).astype(int) +
        (df["Motivation_Level"]   == "Low").astype(int) +
        (df["Access_to_Resources"] == "Low").astype(int) +
        (df["Tutoring_Sessions"]   == 0).astype(int)
    )

    df["Risk_Level"] = df["Risk_Score"].apply(
        lambda x: "High Risk" if x >= 4 else ("Medium Risk" if x >= 2 else "Low Risk")
    )

    high   = df[df["Risk_Level"] == "High Risk"]
    medium = df[df["Risk_Level"] == "Medium Risk"]
    low    = df[df["Risk_Level"] == "Low Risk"]

    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Total Students",  len(df))
    col2.metric("High Risk",   len(high),   delta=f"{len(high)/len(df)*100:.1f}%",   delta_color="inverse")
    col3.metric("Medium Risk", len(medium), delta=f"{len(medium)/len(df)*100:.1f}%", delta_color="off")
    col4.metric("Low Risk",    len(low),    delta=f"{len(low)/len(df)*100:.1f}%",    delta_color="normal")

    st.markdown("---")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Risk Level Breakdown")
        risk_counts = df["Risk_Level"].value_counts().reset_index()
        risk_counts.columns = ["Risk_Level", "Count"]
        fig = px.pie(risk_counts, names="Risk_Level", values="Count",
                     color="Risk_Level",
                     color_discrete_map={
                         "High Risk":   "#e74c3c",
                         "Medium Risk": "#f39c12",
                         "Low Risk":    "#2ecc71"
                     })
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Risk Score Distribution")
        fig2 = px.histogram(df, x="Risk_Score", nbins=7,
                            color_discrete_sequence=["#e67e22"],
                            labels={"Risk_Score": "Risk Score (out of 6)"})
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Exam Score vs Attendance — coloured by Risk")
    fig3 = px.scatter(df, x="Attendance_Rate", y="Exam_Score",
                      color="Risk_Level",
                      color_discrete_map={
                          "High Risk":   "#e74c3c",
                          "Medium Risk": "#f39c12",
                          "Low Risk":    "#2ecc71"
                      },
                      hover_data=["Student_ID", "Weekly_Hours_Studied", "Motivation_Level"],
                      opacity=0.7,
                      labels={"Attendance_Rate": "Attendance (%)", "Exam_Score": "Exam Score"})
    st.plotly_chart(fig3, use_container_width=True)

    st.subheader("Risk by Family Income")
    risk_income = df.groupby(["Family_Income", "Risk_Level"]).size().reset_index(name="Count")
    fig4 = px.bar(risk_income, x="Family_Income", y="Count", color="Risk_Level",
                  barmode="stack",
                  category_orders={"Family_Income": ["Low", "Medium", "High"],
                                   "Risk_Level": ["High Risk", "Medium Risk", "Low Risk"]},
                  color_discrete_map={
                      "High Risk":   "#e74c3c",
                      "Medium Risk": "#f39c12",
                      "Low Risk":    "#2ecc71"
                  })
    st.plotly_chart(fig4, use_container_width=True)

    st.markdown("---")
    st.subheader("High Risk Students — Full List")
    st.markdown(f"These **{len(high)}** students need immediate support.")

    risk_filter = st.selectbox("Show risk level", ["High Risk", "Medium Risk", "Low Risk", "All"])
    if risk_filter == "All":
        display_df = df
    else:
        display_df = df[df["Risk_Level"] == risk_filter]

    st.dataframe(
        display_df[[
            "Student_ID", "Risk_Level", "Risk_Score", "Exam_Score",
            "Attendance_Rate", "Weekly_Hours_Studied", "Motivation_Level",
            "Access_to_Resources", "Tutoring_Sessions", "Family_Income"
        ]].sort_values("Risk_Score", ascending=False),
        use_container_width=True
    )

#  FR 2.2.01  —  Student records

elif page == "FR 2.2.01 — Student Records":
    st.title("FR 2.2.01 — Student Records")
    st.markdown("Browse all student records or search for a specific student by ID.")

    search = st.text_input("Search by Student ID (e.g. STU0010001)", "")

    if search.strip():
        df = run_query("""
            SELECT s.Student_ID, s.Gender, s.Family_Income, s.Parental_Education_Level,
                   s.Distance_from_Home, f.Exam_Score, f.Attendance_Rate, f.Motivation_Level
            FROM dim_Student s
            JOIN fact_Performance f ON s.Student_Key = f.Student_Key
            WHERE s.Student_ID = %s
        """, (search.strip(),))
        if df.empty:
            st.warning("No student found with that ID.")
        else:
            st.success(f"Found student: {search.strip()}")
            st.dataframe(df, use_container_width=True)
    else:
        df = run_query("""
            SELECT TOP 200 s.Student_ID, s.Gender, s.Family_Income,
                   s.Parental_Education_Level, s.Distance_from_Home,
                   f.Exam_Score, f.Attendance_Rate, f.Motivation_Level
            FROM dim_Student s
            JOIN fact_Performance f ON s.Student_Key = f.Student_Key
            ORDER BY s.Student_ID
        """)
        st.dataframe(df, use_container_width=True)
        st.caption(f"Showing first 200 of all students")


#  FR 2.2.02  —  Assesment results

elif page == "FR 2.2.02 — Assessment Results":
    st.title("FR 2.2.02 — Assessment Results")
    st.markdown("View exam scores, attendance rates, and how they relate to student demographics.")

    df = run_query("""
        SELECT f.Exam_Score, f.Previous_Score, f.Attendance_Rate,
               s.Gender, s.Family_Income, s.Parental_Education_Level
        FROM fact_Performance f
        JOIN dim_Student s ON f.Student_Key = s.Student_Key
    """)

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Exam Score vs Previous Score")
        fig = px.scatter(df, x="Previous_Score", y="Exam_Score", color="Gender",
                         opacity=0.5, labels={"Previous_Score": "Previous Score",
                                               "Exam_Score": "Exam Score"})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Exam Score by Family Income")
        fig2 = px.box(df, x="Family_Income", y="Exam_Score",
                      color="Family_Income",
                      category_orders={"Family_Income": ["Low", "Medium", "High"]})
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Score by Parental Education Level")
    avg_df = df.groupby("Parental_Education_Level")["Exam_Score"].mean().reset_index()
    fig3 = px.bar(avg_df, x="Parental_Education_Level", y="Exam_Score", color="Parental_Education_Level")
    st.plotly_chart(fig3, use_container_width=True)


#  FR 2.2.03  —  Track student changes

elif page == "FR 2.2.03 — Track Student Changes":
    st.title("FR 2.2.03 — Track Student Performance Changes")
    st.markdown("Compare each student's current exam score against their previous score.")

    df = run_query("""
        SELECT s.Student_ID, f.Previous_Score, f.Exam_Score,
               (f.Exam_Score - f.Previous_Score) AS Score_Change,
               f.Attendance_Rate, l.Weekly_Hours_Studied, f.Motivation_Level
        FROM fact_Performance f
        JOIN dim_Student   s ON f.Student_Key   = s.Student_Key
        JOIN dim_Lifestyle l ON f.Lifestyle_Key = l.Lifestyle_Key
        ORDER BY Score_Change DESC
    """)

    df["Status"] = df["Score_Change"].apply(
        lambda x: "Improved" if x > 0 else ("Declined" if x < 0 else "Same")
    )

    col1, col2, col3 = st.columns(3)
    col1.metric("Improved", len(df[df["Status"] == "Improved"]), delta="↑")
    col2.metric("Declined", len(df[df["Status"] == "Declined"]), delta="↓")
    col3.metric("No Change", len(df[df["Status"] == "Same"]))

    st.subheader("Score Change Distribution")
    fig = px.histogram(df, x="Score_Change", color="Status",
                       color_discrete_map={"Improved": "#2ecc71",
                                           "Declined": "#e74c3c",
                                           "Same":     "#95a5a6"})
    st.plotly_chart(fig, use_container_width=True)

    st.subheader("Top 20 Most Improved Students")
    st.dataframe(df.head(20)[["Student_ID", "Previous_Score", "Exam_Score", "Score_Change", "Status"]],
                 use_container_width=True)

#  FR 2.2.04  —  Research Query Tool

elif page == "FR 2.2.04 — Research Query Tool":
    st.title("FR 2.2.04 — Research Query Tool")
    st.markdown("Filter students by any combination of criteria and explore the results.")

    col1, col2 = st.columns(2)

    with col1:
        income_filter  = st.multiselect("Family Income",
                                        ["Low", "Medium", "High"],
                                        default=["Low", "Medium", "High"])
        gender_filter  = st.multiselect("Gender",
                                        ["Male", "Female"],
                                        default=["Male", "Female"])
        school_filter  = st.multiselect("School Type",
                                        ["Public", "Private"],
                                        default=["Public", "Private"])
    with col2:
        score_range    = st.slider("Exam Score Range",    0, 100, (0, 100))
        attend_range   = st.slider("Attendance Range (%)", 0, 100, (0, 100))
        hours_range    = st.slider("Weekly Study Hours",  0, 44,  (0, 44))

    if income_filter and gender_filter and school_filter:
        # Build WHERE clauses using the selected filters
        income_sql = ", ".join([f"'{x}'" for x in income_filter])
        gender_sql = ", ".join([f"'{x}'" for x in gender_filter])
        school_sql = ", ".join([f"'{x}'" for x in school_filter])

        query = f"""
            SELECT s.Student_ID, s.Gender, s.Family_Income, s.Parental_Education_Level,
                   sc.School_Type, f.Exam_Score, f.Attendance_Rate,
                   l.Weekly_Hours_Studied, f.Motivation_Level, f.Stress_Level
            FROM fact_Performance f
            JOIN dim_Student   s  ON f.Student_Key   = s.Student_Key
            JOIN dim_Lifestyle l  ON f.Lifestyle_Key  = l.Lifestyle_Key
            JOIN dim_School    sc ON f.School_Key     = sc.School_Key
            WHERE s.Family_Income        IN ({income_sql})
              AND s.Gender               IN ({gender_sql})
              AND sc.School_Type         IN ({school_sql})
              AND f.Exam_Score           BETWEEN {score_range[0]}  AND {score_range[1]}
              AND f.Attendance_Rate      BETWEEN {attend_range[0]} AND {attend_range[1]}
              AND l.Weekly_Hours_Studied BETWEEN {hours_range[0]}  AND {hours_range[1]}
        """

        result_df = run_query(query)
        st.markdown(f"**{len(result_df)} students** match your filters.")
        st.dataframe(result_df, use_container_width=True)

        if len(result_df) > 0:
            st.subheader("Study Hours vs Exam Score")
            fig = px.scatter(result_df, x="Weekly_Hours_Studied", y="Exam_Score",
                             color="Family_Income", size="Attendance_Rate",
                             hover_data=["Student_ID"],
                             opacity=0.7)
            st.plotly_chart(fig, use_container_width=True)
    else:
        st.info("Please select at least one option in each filter.")


#  FR 2.2.05  —  Performance over Time

elif page == "FR 2.2.05 — Performance Over Time":
    st.title("FR 2.2.05 — Performance Over Time")
    st.markdown("Analyse how exam scores and attendance trend across the 2024 school year.")

    term_df = run_query("""
        SELECT d.Term, d.Month,
               AVG(f.Exam_Score)      AS Avg_Score,
               AVG(f.Attendance_Rate) AS Avg_Attendance,
               COUNT(*)               AS Student_Count
        FROM fact_Performance f
        JOIN dim_Date d ON f.Date_Key = d.Date_Key
        GROUP BY d.Term, d.Month
        ORDER BY d.Month
    """)

    term_order = ["Term 1", "Term 2", "Term 3", "Term 4"]

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Average Exam Score by Term")
        grouped = term_df.groupby("Term")["Avg_Score"].mean().reset_index()
        fig = px.bar(grouped, x="Term", y="Avg_Score", color="Term",
                     category_orders={"Term": term_order},
                     labels={"Avg_Score": "Average Score"})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader("Average Attendance by Term")
        grouped2 = term_df.groupby("Term")["Avg_Attendance"].mean().reset_index()
        fig2 = px.line(grouped2, x="Term", y="Avg_Attendance", markers=True,
                       category_orders={"Term": term_order},
                       labels={"Avg_Attendance": "Avg Attendance (%)"})
        st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Student Count per Term")
    count_df = term_df.groupby("Term")["Student_Count"].sum().reset_index()
    fig3 = px.bar(count_df, x="Term", y="Student_Count",
                  category_orders={"Term": term_order},
                  color_discrete_sequence=["#9467bd"])
    st.plotly_chart(fig3, use_container_width=True)


#  FR 2.2.06  —  Segmented Results

elif page == "FR 2.2.06 — Segmented Results":
    st.title("FR 2.2.06 — Segmented Results")
    st.markdown("Compare student performance across different segments.")

    segment = st.selectbox("Segment by", [
        "School Type",
        "Parental Education",
        "Teacher Quality",
        "Motivation Level",
        "Stress Level",
    ])

    query_map = {
        "School Type": """
            SELECT sc.School_Type AS Segment, AVG(f.Exam_Score) AS Avg_Score, COUNT(*) AS Count
            FROM fact_Performance f
            JOIN dim_School sc ON f.School_Key = sc.School_Key
            GROUP BY sc.School_Type
        """,
        "Parental Education": """
            SELECT s.Parental_Education_Level AS Segment, AVG(f.Exam_Score) AS Avg_Score, COUNT(*) AS Count
            FROM fact_Performance f
            JOIN dim_Student s ON f.Student_Key = s.Student_Key
            GROUP BY s.Parental_Education_Level
        """,
        "Teacher Quality": """
            SELECT sp.Teacher_Quality AS Segment, AVG(f.Exam_Score) AS Avg_Score, COUNT(*) AS Count
            FROM fact_Performance f
            JOIN dim_Support sp ON f.Support_Key = sp.Support_Key
            GROUP BY sp.Teacher_Quality
        """,
        "Motivation Level": """
            SELECT f.Motivation_Level AS Segment, AVG(f.Exam_Score) AS Avg_Score, COUNT(*) AS Count
            FROM fact_Performance f
            GROUP BY f.Motivation_Level
        """,
        "Stress Level": """
            SELECT f.Stress_Level AS Segment, AVG(f.Exam_Score) AS Avg_Score, COUNT(*) AS Count
            FROM fact_Performance f
            GROUP BY f.Stress_Level
        """,
    }

    df = run_query(query_map[segment])

    col1, col2 = st.columns(2)

    with col1:
        st.subheader(f"Average Score by {segment}")
        fig = px.bar(df, x="Segment", y="Avg_Score", color="Segment",
                     labels={"Avg_Score": "Average Exam Score"})
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.subheader(f"Student Count by {segment}")
        fig2 = px.pie(df, names="Segment", values="Count")
        st.plotly_chart(fig2, use_container_width=True)

    st.dataframe(df, use_container_width=True)
