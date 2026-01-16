import streamlit as st
from datetime import date
from ui.theme import init_page, apply_theme, theme_switcher
from ui.layout import navbar, sidebar_menu
from ui.components import card_start, card_end
from core.db import query_df, execute, load_provinces, search_projects

STATUSES = ["ACTIVE", "INACTIVE"]

def main():
    init_page(title="PPC Surveyor Database", layout="wide")
    sidebar_menu()
    theme = theme_switcher(default="light")
    apply_theme(theme)
    navbar("PPC Surveyor Database", right_text="Hiring")

    st.title("Project Surveyor Hiring")

    card_start("Assign Surveyor to Project", "Select a project and a surveyor, then assign one or more work provinces.")

    q = st.text_input("Search Project", placeholder="Type project code, name, client, or implementing partner")
    proj_df = search_projects(q)

    if proj_df.empty:
        st.warning("No projects found.")
        card_end()
        return

    proj = st.selectbox(
        "Select Project",
        proj_df.to_dict("records"),
        format_func=lambda r: f'{r.get("Project_Code","")} - {r.get("Project_Name","")}',
    )

    surv_df = query_df(
        "SELECT Surveyor_ID, Surveyor_Code, Surveyor_Name FROM surveyors ORDER BY Surveyor_Name LIMIT 500"
    )
    if surv_df.empty:
        st.warning("No surveyors found.")
        card_end()
        return

    surv = st.selectbox(
        "Select Surveyor",
        surv_df.to_dict("records"),
        format_func=lambda r: f'{r.get("Surveyor_Code","")} - {r.get("Surveyor_Name","")}',
    )

    prov_df = load_provinces()
    if prov_df.empty:
        st.warning("No provinces found.")
        card_end()
        return

    provs = st.multiselect(
        "Work Provinces *",
        prov_df.to_dict("records"),
        format_func=lambda r: f'{r.get("Province_Name","")} ({r.get("Province_Code","")})',
    )

    role = st.text_input("Role *", placeholder="Example: Field Surveyor, TPM Monitor, WASH Engineer")
    start_date = st.date_input("Start Date *", value=date.today())
    end_date = st.date_input("End Date", value=None)
    status = st.selectbox("Status", STATUSES, index=0)

    c1, c2 = st.columns([1, 3])
    with c1:
        save = st.button("Save Hiring", type="primary")
    with c2:
        st.caption("One record will be created per selected province.")

    if save:
        if not role.strip():
            st.error("Role is required.")
            card_end()
            return
        if not provs:
            st.error("At least one work province is required.")
            card_end()
            return
        if end_date is not None and start_date is not None and start_date > end_date:
            st.error("Start date cannot be after end date.")
            card_end()
            return

        try:
            for p in provs:
                execute(
                    """
                    INSERT INTO project_surveyors
                      (Project_ID, Surveyor_ID, Role, Work_Province_Code, Start_Date, End_Date, Status)
                    VALUES
                      (%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        int(proj["Project_ID"]),
                        int(surv["Surveyor_ID"]),
                        role.strip(),
                        p["Province_Code"],
                        start_date,
                        end_date,
                        status,
                    ),
                )
            st.success("Saved successfully.")
        except Exception as ex:
            st.error(f"Save failed: {ex}")

    card_end()

if __name__ == "__main__":
    main()