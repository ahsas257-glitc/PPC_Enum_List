import streamlit as st
import pandas as pd
from io import BytesIO

from ui.theme import init_page, apply_theme, theme_switcher
from ui.layout import navbar, sidebar_menu
from ui.components import card_start, card_end
from core.auth import login_box
from core.db import query_df, execute
from core.validators import validate_email, validate_tazkira, normalize_phone, COUNTRY_CODES

def admin_panel():
    st.success("Admin mode enabled")

    c1, c2 = st.columns([1, 5])
    with c1:
        if st.button("Logout"):
            st.session_state.is_admin = False
            st.rerun()

    st.divider()

    card_start("Search Surveyor (Admin)", "Search by code, Tazkira, name, phone, or WhatsApp (up to 200 rows).")

    q = st.text_input("Search", placeholder="Example: PPC-KAB-001 or 1234-5678-91011")
    like = f"%{q.strip()}%" if q else "%"

    df = query_df(
        """
        SELECT
          s.Surveyor_ID,
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
          s.CV_Link,
          s.CV_File_Name,
          s.CV_Mime,
          s.Created_At,
          s.Updated_At
        FROM surveyors s
        LEFT JOIN provinces pp ON pp.Province_Code = s.Permanent_Province_Code
        LEFT JOIN provinces cp ON cp.Province_Code = s.Current_Province_Code
        WHERE s.Surveyor_Code LIKE %s
           OR s.Tazkira_No LIKE %s
           OR s.Surveyor_Name LIKE %s
           OR s.Phone_Number LIKE %s
           OR s.Whatsapp_Number LIKE %s
        ORDER BY s.Surveyor_ID DESC
        LIMIT 200
        """,
        (like, like, like, like, like),
    )

    if df.empty:
        st.warning("No results found.")
        card_end()
    else:
        st.dataframe(df, use_container_width=True)

        d1, d2 = st.columns(2)
        with d1:
            csv_bytes = df.to_csv(index=False).encode("utf-8-sig")
            st.download_button("Download CSV", data=csv_bytes, file_name="surveyors.csv", mime="text/csv")
        with d2:
            xbuf = BytesIO()
            with pd.ExcelWriter(xbuf, engine="openpyxl") as writer:
                df.to_excel(writer, index=False, sheet_name="surveyors")
            st.download_button(
                "Download Excel",
                data=xbuf.getvalue(),
                file_name="surveyors.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        card_end()

    st.divider()

    card_start("Delete Surveyor", "Delete by Surveyor Code only.")

    del_code = st.text_input("Surveyor Code to delete", placeholder="PPC-KAB-001", key="del_code")
    if st.button("Delete", type="primary"):
        if not del_code.strip():
            st.error("Enter a Surveyor Code.")
        else:
            try:
                rc = execute("DELETE FROM surveyors WHERE Surveyor_Code=%s", (del_code.strip(),))
                if rc == 0:
                    st.warning("No matching record found.")
                else:
                    st.success("Record deleted.")
            except Exception as ex:
                st.error(f"Delete failed: {ex}")
    card_end()

    st.divider()

    st.session_state.setdefault("edit_errors", {})
    st.session_state.setdefault("edit_record", None)

    card_start("Edit Surveyor", "Surveyor Code is fixed; other fields can be updated.")

    edit_code = st.text_input("Surveyor Code", placeholder="PPC-KAB-001", key="edit_code")
    if st.button("Load Record"):
        if not edit_code.strip():
            st.error("Enter a Surveyor Code.")
        else:
            one = query_df("SELECT * FROM surveyors WHERE Surveyor_Code=%s", (edit_code.strip(),))
            if one.empty:
                st.warning("Record not found.")
                st.session_state.edit_record = None
            else:
                st.session_state.edit_record = one.iloc[0].to_dict()
                st.session_state.edit_errors = {}

    rec = st.session_state.edit_record
    if rec:
        with st.form("edit_form", clear_on_submit=False):
            st.write(f"Surveyor Code: **{rec.get('Surveyor_Code','')}**")

            c1, c2 = st.columns(2)

            with c1:
                name = st.text_input("Surveyor Name *", value=rec.get("Surveyor_Name", "") or "")
                gender = st.selectbox("Gender *", ["Male", "Female"], index=0 if rec.get("Gender") == "Male" else 1)
                father = st.text_input("Father Name *", value=rec.get("Father_Name", "") or "")
                tazkira = st.text_input("Tazkira No *", value=rec.get("Tazkira_No", "") or "")
                email = st.text_input("Email *", value=rec.get("Email_Address", "") or "")

            with c2:
                st.markdown("**WhatsApp**")
                w_code_label = st.selectbox("Country code (WhatsApp)", [x[0] for x in COUNTRY_CODES], index=0, key="w_code_label_edit")
                w_code = dict(COUNTRY_CODES).get(w_code_label, "+93")
                whatsapp_raw = st.text_input("WhatsApp number", value=rec.get("Whatsapp_Number", "") or "", key="whatsapp_raw_edit")

                st.markdown("**Phone**")
                p_code_label = st.selectbox("Country code (Phone)", [x[0] for x in COUNTRY_CODES], index=0, key="p_code_label_edit")
                p_code = dict(COUNTRY_CODES).get(p_code_label, "+93")
                phone_raw = st.text_input("Phone number", value=rec.get("Phone_Number", "") or "", key="phone_raw_edit")

                cv_link = st.text_input("CV Link", value=(rec.get("CV_Link") or ""), key="cv_link_edit")

            save = st.form_submit_button("Save changes", type="primary")

            if save:
                errs = {}

                if not name.strip():
                    errs["name"] = "Surveyor name is required."
                if not father.strip():
                    errs["father"] = "Father name is required."

                t_err = validate_tazkira(tazkira)
                if t_err:
                    errs["tazkira"] = t_err if isinstance(t_err, str) else "Invalid Tazkira number."

                e_err = validate_email(email)
                if e_err:
                    errs["email"] = e_err if isinstance(e_err, str) else "Invalid email address."

                w_norm, w_err = normalize_phone(whatsapp_raw, w_code)
                if w_err:
                    errs["whatsapp"] = w_err if isinstance(w_err, str) else "Invalid WhatsApp number."

                p_norm, p_err = normalize_phone(phone_raw, p_code)
                if p_err:
                    errs["phone"] = p_err if isinstance(p_err, str) else "Invalid phone number."

                st.session_state.edit_errors = errs
                if errs:
                    st.warning("Please fix the errors and try again.")
                    st.json(errs)
                    st.stop()

                try:
                    execute(
                        """
                        UPDATE surveyors
                        SET Surveyor_Name=%s,
                            Gender=%s,
                            Father_Name=%s,
                            Tazkira_No=%s,
                            Email_Address=%s,
                            Whatsapp_Number=%s,
                            Phone_Number=%s,
                            CV_Link=%s
                        WHERE Surveyor_Code=%s
                        """,
                        (
                            name.strip(),
                            gender,
                            father.strip(),
                            tazkira.strip(),
                            email.strip(),
                            w_norm,
                            p_norm,
                            (cv_link.strip() or None),
                            rec["Surveyor_Code"],
                        ),
                    )
                    st.success("Saved successfully.")
                    st.session_state.edit_record = None
                except Exception as ex:
                    st.error(f"Save failed: {ex}")

    card_end()

    st.divider()

    card_start("Download CV File", "Download the stored CV file for a surveyor (if available).")

    code = st.text_input("Surveyor Code (for CV download)", placeholder="PPC-KAB-001", key="cv_dl_code")
    if st.button("Fetch CV"):
        if not code.strip():
            st.error("Enter a Surveyor Code.")
        else:
            df_cv = query_df(
                "SELECT CV_File, CV_File_Name, CV_Mime FROM surveyors WHERE Surveyor_Code=%s",
                (code.strip(),),
            )
            if df_cv.empty:
                st.warning("Record not found.")
            else:
                row = df_cv.iloc[0]
                if row["CV_File"] is None:
                    st.info("No CV file is stored for this surveyor.")
                else:
                    st.download_button(
                        "Download CV File",
                        data=row["CV_File"],
                        file_name=row["CV_File_Name"] or "cv.bin",
                        mime=row["CV_Mime"] or "application/octet-stream",
                    )

    card_end()

def main():
    init_page(title="PPC Surveyor Database", layout="wide")
    sidebar_menu()
    theme = theme_switcher(default="light")
    apply_theme(theme)
    navbar("PPC Surveyor Database", right_text="Admin")

    st.title("Admin")

    if not st.session_state.get("is_admin", False):
        login_box()
        return

    admin_panel()

if __name__ == "__main__":
    main()