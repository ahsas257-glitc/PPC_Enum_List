import streamlit as st
import re
from ui.theme import init_page, apply_theme, theme_switcher
from ui.layout import navbar, sidebar_menu
from ui.components import card_start, card_end, field_error
from core.db import load_provinces, get_connection
from core.validators import COUNTRY_CODES, validate_email, validate_tazkira, normalize_phone

# Handle exception for SURVEYOR_CODE_PREFIX import
try:
    from core.settings import SURVEYOR_CODE_PREFIX
except Exception:
    SURVEYOR_CODE_PREFIX = "PPC"

def init_form_state():
    """ Initialize the form state with default values. """
    defaults = {
        "surveyor_name": "",
        "gender": "Male",
        "father_name": "",
        "tazkira": "",
        "email": "",
        "perm_prov": None,
        "curr_prov": None,
        "w_code_label": "Afghanistan (+93)",
        "w_custom": "+93",
        "whatsapp_raw": "",
        "p_code_label": "Afghanistan (+93)",
        "p_custom": "+93",
        "phone_raw": "",
        "cv_link": "",
        "tazkira_image": None,
        "errors": {},
        "success_msg": "",
    }
    for k, v in defaults.items():
        st.session_state.setdefault(k, v)

def validate_all(name_to_code: dict):
    """ Validate all fields and return any errors. """
    e = {}

    if not st.session_state.surveyor_name.strip():
        e["surveyor_name"] = "Surveyor name is required."
    if not st.session_state.father_name.strip():
        e["father_name"] = "Father name is required."

    # Tazkira validation
    t_err = validate_tazkira(st.session_state.tazkira)
    if t_err:
        e["tazkira"] = t_err if isinstance(t_err, str) else "Invalid Tazkira number."

    # Email validation
    mail_err = validate_email(st.session_state.email)
    if mail_err:
        e["email"] = mail_err if isinstance(mail_err, str) else "Invalid email address."

    # Normalize WhatsApp and Phone numbers
    w_code = dict(COUNTRY_CODES).get(st.session_state.w_code_label, "+93")
    if st.session_state.w_code_label == "Other":
        w_code = st.session_state.w_custom.strip() or "+93"

    p_code = dict(COUNTRY_CODES).get(st.session_state.p_code_label, "+93")
    if st.session_state.p_code_label == "Other":
        p_code = st.session_state.p_custom.strip() or "+93"

    w_norm, w_err = normalize_phone(st.session_state.whatsapp_raw, w_code)
    if w_err:
        e["whatsapp_raw"] = w_err if isinstance(w_err, str) else "Invalid WhatsApp number."

    p_norm, p_err = normalize_phone(st.session_state.phone_raw, p_code)
    if p_err:
        e["phone_raw"] = p_err if isinstance(p_err, str) else "Invalid phone number."

    # Validate provinces
    perm_code = name_to_code.get(st.session_state.perm_prov)
    curr_code = name_to_code.get(st.session_state.curr_prov)

    if not perm_code:
        e["perm_prov"] = "Select a permanent province."
    if not curr_code:
        e["curr_prov"] = "Select a current province."

    return e, w_norm, p_norm, perm_code, curr_code

def get_next_surveyor_code_tx(conn, perm_prov_code: str) -> str:
    """ Generate next surveyor code based on province sequence. """
    cur = conn.cursor()

    cur.execute(
        "INSERT IGNORE INTO province_sequences (Province_Code, Last_Number) VALUES (%s, 0)",
        (perm_prov_code,)
    )

    cur.execute(
        "SELECT Last_Number FROM province_sequences WHERE Province_Code=%s FOR UPDATE",
        (perm_prov_code,)
    )
    row = cur.fetchone()
    last = int(row[0]) if row else 0
    nxt = last + 1

    cur.execute(
        "UPDATE province_sequences SET Last_Number=%s WHERE Province_Code=%s",
        (nxt, perm_prov_code),
    )

    cur.close()
    return f"{SURVEYOR_CODE_PREFIX}-{perm_prov_code}-{nxt:03d}"

def main():
    """ Main function for adding a surveyor. """
    init_page(title="PPC Surveyor Database", layout="wide")
    sidebar_menu()
    theme = theme_switcher(default="light")
    apply_theme(theme)
    navbar("PPC Surveyor Database", right_text="Surveyors")

    init_form_state()

    st.title("Add Surveyor")

    try:
        prov_df = load_provinces()
        if prov_df.empty:
            st.error("The provinces table is empty. Please load provinces first.")
            st.stop()
    except Exception as ex:
        st.error(f"Database error: {ex}")
        st.stop()

    prov_names = prov_df["Province_Name"].tolist()
    name_to_code = dict(zip(prov_df["Province_Name"], prov_df["Province_Code"]))

    card_start(
        "Register a New Surveyor",
        "If there is an error, it will be shown under the related field and your inputs will be kept."
    )

    if st.session_state.success_msg:
        st.success(st.session_state.success_msg)

    with st.form("add_surveyor_form", clear_on_submit=False):
        c1, c2 = st.columns(2)

        with c1:
            st.text_input("Surveyor Name *", key="surveyor_name")
            field_error(st.session_state.errors.get("surveyor_name"))

            st.selectbox("Gender *", ["Male", "Female"], key="gender")

            st.text_input("Father Name *", key="father_name")
            field_error(st.session_state.errors.get("father_name"))

            st.text_input("Tazkira No *", placeholder="1234-5678-91011", key="tazkira")
            field_error(st.session_state.errors.get("tazkira"))

            st.text_input("Email *", placeholder="name@example.com", key="email")
            field_error(st.session_state.errors.get("email"))

        with c2:
            st.selectbox("Permanent Province *", prov_names, key="perm_prov")
            field_error(st.session_state.errors.get("perm_prov"))

            st.selectbox("Current Province *", prov_names, key="curr_prov")
            field_error(st.session_state.errors.get("curr_prov"))

            st.caption("Tip: If the number starts with 0, the system will remove it automatically.")

        st.divider()

        st.markdown("### WhatsApp Number *")
        wc1, wc2 = st.columns([1, 2])
        with wc1:
            st.selectbox("Country code", [x[0] for x in COUNTRY_CODES], key="w_code_label")
            if st.session_state.w_code_label == "Other":
                st.text_input("Custom code (e.g., +93)", key="w_custom")
        with wc2:
            st.text_input("WhatsApp number", placeholder="0731212123 or 731212123", key="whatsapp_raw")
            field_error(st.session_state.errors.get("whatsapp_raw"))

        st.markdown("### Phone Number *")
        pc1, pc2 = st.columns([1, 2])
        with pc1:
            st.selectbox("Country code", [x[0] for x in COUNTRY_CODES], key="p_code_label")
            if st.session_state.p_code_label == "Other":
                st.text_input("Custom code (e.g., +93)", key="p_custom")
        with pc2:
            st.text_input("Phone number", placeholder="0731212123 or 731212123", key="phone_raw")
            field_error(st.session_state.errors.get("phone_raw"))

        st.divider()

        st.markdown("### Tazkira Image *")
        tazkira_files = st.file_uploader("Upload Tazkira Image, PDF or Word", type=["jpg", "jpeg", "png", "pdf", "docx"], accept_multiple_files=True)

        # Initialize file processing variables
        tazkira_image_blob = None
        tazkira_pdf_blob = None
        tazkira_word_blob = None

        tazkira_image_name = None
        tazkira_pdf_name = None
        tazkira_word_name = None
        tazkira_image_mime = None
        tazkira_pdf_mime = None
        tazkira_word_mime = None

        if tazkira_files:
            for uploaded_file in tazkira_files:
                file_name = uploaded_file.name
                file_type = uploaded_file.type

                # Process file and store in appropriate variable
                file_blob = uploaded_file.getvalue()
                
                if "image" in file_type:
                    tazkira_image_blob = file_blob
                    tazkira_image_name = file_name
                    tazkira_image_mime = file_type
                elif "pdf" in file_type:
                    tazkira_pdf_blob = file_blob
                    tazkira_pdf_name = file_name
                    tazkira_pdf_mime = file_type
                elif "word" in file_type:
                    tazkira_word_blob = file_blob
                    tazkira_word_name = file_name
                    tazkira_word_mime = file_type

        st.divider()

        st.markdown("### CV (Optional)")
        st.text_input("CV Link", key="cv_link")
        cv_file = st.file_uploader("Upload CV file (optional)", type=None)

        submit = st.form_submit_button("Add to Database", type="primary")

        if submit:
            st.session_state.success_msg = ""
            errors, w_norm, p_norm, perm_code, curr_code = validate_all(name_to_code)
            st.session_state.errors = errors

            if errors:
                st.warning("Some fields have issues. Please fix the errors shown under the fields.")
                st.stop()

            conn = get_connection()
            try:
                if getattr(conn, "in_transaction", False):
                    conn.rollback()

                conn.start_transaction()

                surveyor_code = get_next_surveyor_code_tx(conn, perm_code)

                # Optionally, handle the CV upload
                cv_blob = cv_file.getvalue() if cv_file else None
                cv_name = cv_file.name if cv_file else None
                cv_mime = cv_file.type if cv_file else None

                # Insert Surveyor data into the database
                cur = conn.cursor()
                cur.execute(
                    """
                    INSERT INTO surveyors
                      (Surveyor_Code, Surveyor_Name, Gender, Father_Name, Tazkira_No,
                       Email_Address, Whatsapp_Number, Phone_Number,
                       Permanent_Province_Code, Current_Province_Code,
                       CV_Link, CV_File, CV_File_Name, CV_Mime,
                       Tazkira_Image, Tazkira_Image_Name, Tazkira_Image_Mime,
                       Tazkira_PDF, Tazkira_PDF_Name, Tazkira_PDF_Mime,
                       Tazkira_Word, Tazkira_Word_Name, Tazkira_Word_Mime)
                    VALUES
                      (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
                    """,
                    (
                        surveyor_code,
                        st.session_state.surveyor_name.strip(),
                        st.session_state.gender,
                        st.session_state.father_name.strip(),
                        st.session_state.tazkira.strip(),
                        st.session_state.email.strip(),
                        w_norm,
                        p_norm,
                        perm_code,
                        curr_code,
                        (st.session_state.cv_link.strip() or None),
                        cv_blob,
                        cv_name,
                        cv_mime,
                        tazkira_image_blob,
                        tazkira_image_name,
                        tazkira_image_mime,
                        tazkira_pdf_blob,
                        tazkira_pdf_name,
                        tazkira_pdf_mime,
                        tazkira_word_blob,
                        tazkira_word_name,
                        tazkira_word_mime,
                    ),
                )
                cur.close()

                conn.commit()

                st.session_state.success_msg = f"Saved successfully. Surveyor Code: {surveyor_code}"
                st.session_state.errors = {}

            except Exception as ex:
                try:
                    conn.rollback()
                except Exception:
                    pass
                st.error(f"Save failed: {ex}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    card_end()

if __name__ == "__main__":
    main()
