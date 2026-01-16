import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from ui.theme import init_page, apply_theme, theme_switcher
from ui.layout import navbar, sidebar_menu
from core.db import query_df
from core.auth import ensure_auth_state
from core.settings import APP_TITLE

def main():
    init_page(title=APP_TITLE, layout="wide")
    ensure_auth_state()

    sidebar_menu()
    theme = theme_switcher(default="light")
    apply_theme(theme)
    navbar(APP_TITLE, right_text="Dashboard")

    st.title("Dashboard")

    k1 = query_df("SELECT COUNT(*) AS n FROM surveyors")
    k2 = query_df("SELECT COUNT(*) AS n FROM projects")
    k3 = query_df("SELECT COUNT(*) AS n FROM project_surveyors WHERE Status='ACTIVE'")

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Surveyors", int(k1.iloc[0]["n"]))
    c2.metric("Total Projects", int(k2.iloc[0]["n"]))
    c3.metric("Active Assignments", int(k3.iloc[0]["n"]))

    st.divider()

    df = query_df("""
      SELECT p.Province_Name, COUNT(*) AS cnt
      FROM surveyors s
      LEFT JOIN provinces p ON p.Province_Code = s.Permanent_Province_Code
      GROUP BY p.Province_Name
      ORDER BY cnt DESC
      LIMIT 12
    """)

    if not df.empty:
        fig = plt.figure()
        plt.bar(df["Province_Name"], df["cnt"])
        plt.xticks(rotation=45, ha="right")
        st.pyplot(fig, use_container_width=True)

if __name__ == "__main__":
    main()
