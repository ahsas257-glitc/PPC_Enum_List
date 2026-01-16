import streamlit as st
from ui.theme import init_page, apply_theme, theme_switcher
from ui.layout import navbar, sidebar_menu
from ui.components import card_start, card_end
from core.db import query_df

def main():
    init_page(title="PPC Surveyor Database", layout="wide")
    sidebar_menu()
    theme = theme_switcher(default="light")
    apply_theme(theme)
    navbar("PPC Surveyor Database", right_text="Public Search")

    st.title("Search Surveyor (Public)")

    card_start("Public Search", "Search by Surveyor Code, Tazkira, name, phone, or WhatsApp.")

    q = st.text_input("Search", placeholder="Example: PPC-KAB-001 or 1234-5678-91011 or a name")

    if not q.strip():
        st.info("Enter a value to search.")
        card_end()
        return

    like = f"%{q.strip()}%"

    df = query_df(
        """
        SELECT
          s.Surveyor_Code,
          s.Surveyor_Name,
          s.Gender,
          s.Father_Name,
          s.Tazkira_No,
          s.Email_Address,
          s.Whatsapp_Number,
          s.Phone_Number,
          pp.Province_Name AS Permanent_Province,
          cp.Province_Name AS Current_Province,
          s.Created_At
        FROM surveyors s
        LEFT JOIN provinces pp ON pp.Province_Code = s.Permanent_Province_Code
        LEFT JOIN provinces cp ON cp.Province_Code = s.Current_Province_Code
        WHERE s.Surveyor_Code LIKE %s
           OR s.Tazkira_No LIKE %s
           OR s.Surveyor_Name LIKE %s
           OR s.Phone_Number LIKE %s
           OR s.Whatsapp_Number LIKE %s
        ORDER BY s.Surveyor_ID DESC
        LIMIT 50
        """,
        (like, like, like, like, like),
    )

    if df.empty:
        st.warning("No results found.")
    else:
        st.dataframe(df, use_container_width=True)

    card_end()

if __name__ == "__main__":
    main()
