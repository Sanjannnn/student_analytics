# ─────────────────────────────────────────────────────────────────────────────
#  Azure SQL connection details.
#  When running on Streamlit Cloud, values come from st.secrets.
#  When running locally, values come from .streamlit/secrets.toml (if present)
#  or the hardcoded fallbacks below.
# ─────────────────────────────────────────────────────────────────────────────

try:
    import streamlit as st
    SERVER   = st.secrets["azure"]["SERVER"]
    DATABASE = st.secrets["azure"]["DATABASE"]
    USERNAME = st.secrets["azure"]["USERNAME"]
    PASSWORD = st.secrets["azure"]["PASSWORD"]
except Exception:
    SERVER   = "studentanalytics2025.database.windows.net"
    DATABASE = "StudentAnalytics"
    USERNAME = "sqladmin"
    PASSWORD = "Analytics2025!"

CONNECTION_STRING = (
    f"Driver={{ODBC Driver 18 for SQL Server}};"
    f"Server=tcp:{SERVER},1433;"
    f"Database={DATABASE};"
    f"Uid={USERNAME};"
    f"Pwd={PASSWORD};"
    f"Encrypt=yes;"
    f"TrustServerCertificate=no;"
    f"Connection Timeout=30;"
)
