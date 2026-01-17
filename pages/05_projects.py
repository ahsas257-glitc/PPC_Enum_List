import streamlit as st
from ui.theme import init_page, apply_theme, theme_switcher
from ui.layout import navbar, sidebar_menu
from ui.components import card_start, card_end
from core.auth import login_box
from core.db import search_projects, add_project_auto, update_project, get_project_by_id

PROJECT_TYPES = ["CBE", "PB", "WASH", "OTHER"]
STATUSES = ["PLANNED", "ACTIVE", "ON_HOLD", "CLOSED"]

def _must(cond: bool, msg: str):
    if cond:
        st.error(msg)
        st.stop()

def _safe_index(options: list[str], value: str, default: str) -> int:
    v = value if value in options else default
    return options.index(v)

def main():
    init_page(title="PPC Surveyor Database", layout="wide")
    sidebar_menu()
    theme = theme_switcher(default="light")
    apply_theme(theme)
    navbar("PPC Surveyor Database", right_text="Projects")

    st.title("Projects (Admin)")

    if not st.session_state.get("is_admin", False):
        login_box()
        return

    card_start("Project Search & List", "Search by code, name, client, or implementing partner.")

    q = st.text_input(
        "Search",
        placeholder="Project Code, Name, Client, or Implementing Partner",
        key="proj_search",
    )
    df = search_projects(q)
    st.dataframe(df, use_container_width=True)

    st.divider()

    st.subheader("Add Project (Auto Code + Phase)")
    with st.form("add_project_form", clear_on_submit=False):
        c1, c2 = st.columns(2)

        with c1:
            name = st.text_input("Project Name *", key="proj_add_name")
            client = st.text_input("Client Name *", key="proj_add_client")
            ptype = st.selectbox(
                "Project Type",
                PROJECT_TYPES,
                index=_safe_index(PROJECT_TYPES, "OTHER", "OTHER"),
                key="proj_add_type",
            )
            ip = st.text_input("Implementing Partner", key="proj_add_ip")

        with c2:
            start = st.date_input("Start Date *", value=None, key="proj_add_start")
            end = st.date_input("End Date", value=None, key="proj_add_end")
            status = st.selectbox(
                "Status",
                STATUSES,
                index=_safe_index(STATUSES, "PLANNED", "PLANNED"),
                key="proj_add_status",
            )
            doc = st.text_input("Project Document Link", key="proj_add_doc")

        notes = st.text_area("Notes", key="proj_add_notes")
        ok = st.form_submit_button("Add Project", type="primary")

        if ok:
            _must(not name.strip(), "Project name is required.")
            _must(not client.strip(), "Client name is required.")
            _must(not start, "Start date is required.")
            _must(end is not None and start is not None and start > end, "Start date cannot be after end date.")

            try:
                new_id = add_project_auto(
                    {
                        "Project_Name": name,
                        "Client_Name": client,
                        "Project_Type": ptype,
                        "Implementing_Partner": ip,
                        "Start_Date": start,
                        "End_Date": end,
                        "Status": status,
                        "Notes": notes,
                        "Project_Document_Link": doc,
                    }
                )
                st.success(f"Saved. Project_ID={new_id}")
                st.rerun()
            except Exception as ex:
                st.error(f"Save failed: {ex}")

    st.divider()

    st.subheader("Edit Project (Load by Project_ID)")
    pid = st.text_input("Project_ID", placeholder="e.g., 12", key="proj_edit_id")
    if not pid.strip():
        card_end()
        return

    try:
        pid_int = int(pid)
    except Exception:
        st.error("Project_ID must be a number.")
        card_end()
        return

    df_one = get_project_by_id(pid_int)
    if df_one.empty:
        st.error("Project not found.")
        card_end()
        return

    row = df_one.iloc[0].to_dict()

    with st.form("edit_project_form", clear_on_submit=False):
        st.caption("Project code and phase number are system-generated and cannot be edited.")

        c1, c2 = st.columns(2)
        with c1:
            st.text_input("Project Code", value=row.get("Project_Code", ""), disabled=True, key="proj_edit_code")
            st.text_input("Phase Number", value=str(row.get("Phase_Number", "")), disabled=True, key="proj_edit_phase")

            name2 = st.text_input("Project Name *", value=row.get("Project_Name", ""), key="proj_edit_name")
            client2 = st.text_input("Client Name *", value=row.get("Client_Name") or "", key="proj_edit_client")
            ptype2 = st.selectbox(
                "Project Type",
                PROJECT_TYPES,
                index=_safe_index(PROJECT_TYPES, row.get("Project_Type", "OTHER"), "OTHER"),
                key="proj_edit_type",
            )
            ip2 = st.text_input("Implementing Partner", value=row.get("Implementing_Partner") or "", key="proj_edit_ip")

        with c2:
            start2 = st.date_input("Start Date *", value=row.get("Start_Date"), key="proj_edit_start")
            end2 = st.date_input("End Date", value=row.get("End_Date"), key="proj_edit_end")
            status2 = st.selectbox(
                "Status",
                STATUSES,
                index=_safe_index(STATUSES, row.get("Status", "PLANNED"), "PLANNED"),
                key="proj_edit_status",
            )
            doc2 = st.text_input(
                "Project Document Link",
                value=row.get("Project_Document_Link") or "",
                key="proj_edit_doc",
            )

        notes2 = st.text_area("Notes", value=row.get("Notes") or "", key="proj_edit_notes")

        save = st.form_submit_button("Save Changes", type="primary")
        if save:
            _must(not name2.strip(), "Project name is required.")
            _must(not client2.strip(), "Client name is required.")
            _must(not start2, "Start date is required.")
            _must(end2 is not None and start2 is not None and start2 > end2, "Start date cannot be after end date.")

            try:
                update_project(
                    pid_int,
                    {
                        "Project_Code": row.get("Project_Code", ""),
                        "Project_Name": name2,
                        "Project_Type": ptype2,
                        "Client_Name": client2,
                        "Implementing_Partner": ip2,
                        "Start_Date": start2,
                        "End_Date": end2,
                        "Status": status2,
                        "Notes": notes2,
                        "Project_Document_Link": doc2,
                    },
                )
                st.success("Updated.")
                st.rerun()
            except Exception as ex:
                st.error(f"Update failed: {ex}")

    card_end()

if __name__ == "__main__":
    main()