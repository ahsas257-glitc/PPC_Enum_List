import streamlit as st
from ui.theme import init_page, apply_theme, theme_switcher
from ui.layout import navbar, sidebar_menu
from ui.components import card_start, card_end, field_error
from core.auth import login_box
from core.db import (
    get_connection,
    get_surveyor_by_code,
    load_banks,
    list_surveyor_accounts,
    add_surveyor_account_tx,
    set_default_account_tx,
)
from core.validators import E164_RE

PAYMENT_TYPES = ["BANK_ACCOUNT", "MOBILE_CREDIT"]

def validate_dynamic(payment_type: str, account_number: str | None, mobile_number: str | None) -> dict:
    errs = {}
    if payment_type == "BANK_ACCOUNT":
        if not (account_number or "").strip():
            errs["account_number"] = "Account number is required for this payment type."
    elif payment_type == "MOBILE_CREDIT":
        if not (mobile_number or "").strip():
            errs["mobile_number"] = "Mobile number is required for this payment type."
        elif not E164_RE.match(mobile_number.strip()):
            errs["mobile_number"] = "Invalid mobile format. Example: +937XXXXXXXX"
    return errs

def main():
    init_page(title="PPC Surveyor Database", layout="wide")
    sidebar_menu()
    theme = theme_switcher(default="light")
    apply_theme(theme)
    navbar("PPC Surveyor Database", right_text="Payments")

    st.title("Surveyor Payments (Admin)")

    if not st.session_state.get("is_admin", False):
        login_box()
        return

    st.session_state.setdefault("pay_errors", {})
    st.session_state.setdefault("selected_surveyor_id", None)

    card_start("Find Surveyor", "Enter the Surveyor Code to load accounts.")

    code = st.text_input("Surveyor Code", placeholder="Example: PPC-KAB-001", key="pay_surveyor_code")
    if st.button("Load Surveyor", key="btn_load_surveyor"):
        df = get_surveyor_by_code(code)
        if df.empty:
            st.error("Surveyor not found.")
            st.session_state.selected_surveyor_id = None
        else:
            st.session_state.selected_surveyor_id = int(df.iloc[0]["Surveyor_ID"])
            st.success(f"{df.iloc[0]['Surveyor_Name']} ({df.iloc[0]['Surveyor_Code']})")

    sid = st.session_state.selected_surveyor_id
    if not sid:
        card_end()
        return

    st.divider()

    st.subheader("Existing Accounts")
    acc = list_surveyor_accounts(sid)
    if acc.empty:
        st.info("No accounts found for this surveyor.")
    else:
        st.dataframe(acc, use_container_width=True)

    st.divider()

    banks = load_banks(active_only=True)
    if banks.empty:
        st.error("No active banks found. Add/activate a bank first.")
        card_end()
        return

    if "Payment_Method" not in banks.columns:
        st.error("Payment_Method is missing from the banks query or table.")
        card_end()
        return

    bank_map = {
        r.Bank_Name: {"id": int(r.Bank_ID), "method": str(r.Payment_Method)}
        for r in banks.itertuples()
    }

    st.subheader("Add New Account")
    with st.form("add_payment_form", clear_on_submit=False):
        c1, c2 = st.columns(2)

        with c1:
            bank_name = st.selectbox("Bank *", list(bank_map.keys()), key="pay_bank_name")
            bank_id = bank_map[bank_name]["id"]
            bank_method = bank_map[bank_name]["method"]

            show_account = bank_method in ("BANK_TRANSFER", "BOTH")
            show_mobile = bank_method in ("MOBILE_WALLET", "BOTH")

            if bank_method == "BANK_TRANSFER":
                payment_type = "BANK_ACCOUNT"
                st.info("Bank transfer: account number is required.")
            elif bank_method == "MOBILE_WALLET":
                payment_type = "MOBILE_CREDIT"
                st.info("Mobile wallet: mobile number is required.")
            else:
                payment_type = st.selectbox("Payment Type *", PAYMENT_TYPES, key="pay_type_both")
                st.info("This bank supports both methods. Select one.")

            account_number = None
            mobile_number = None

            if show_account and payment_type == "BANK_ACCOUNT":
                account_number = st.text_input("Account Number *", key="pay_account_number")
                field_error(st.session_state.pay_errors.get("account_number"))

            if show_mobile and payment_type == "MOBILE_CREDIT":
                mobile_number = st.text_input(
                    "Mobile Number (E.164) *",
                    placeholder="+937XXXXXXXX",
                    key="pay_mobile_number",
                )
                field_error(st.session_state.pay_errors.get("mobile_number"))

        with c2:
            title = st.text_input("Account Title (optional)", key="pay_title")
            make_default = st.selectbox("Make Default?", [1, 0], format_func=lambda x: "Yes" if x == 1 else "No", key="pay_default")
            is_active = st.selectbox("Active?", [1, 0], format_func=lambda x: "Active" if x == 1 else "Inactive", key="pay_active")

        ok = st.form_submit_button("Add Account", type="primary")

        if ok:
            errs = validate_dynamic(payment_type, account_number, mobile_number)
            st.session_state.pay_errors = errs

            if errs:
                st.warning("Please fix the highlighted fields.")
                st.stop()

            conn = get_connection()
            try:
                if getattr(conn, "in_transaction", False):
                    conn.rollback()
                conn.start_transaction()

                new_id = add_surveyor_account_tx(
                    conn=conn,
                    surveyor_id=sid,
                    bank_id=bank_id,
                    payment_type=payment_type,
                    account_number=account_number,
                    mobile_number=mobile_number,
                    account_title=title,
                    make_default=make_default,
                    is_active=is_active,
                )
                conn.commit()
                st.session_state.pay_errors = {}
                st.success(f"Account added. ID={new_id}")
                st.rerun()

            except Exception as ex:
                try:
                    conn.rollback()
                except Exception:
                    pass
                st.error(f"Add failed: {ex}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    st.divider()

    st.subheader("Set Default Account")
    if not acc.empty:
        options = {
            f"ID:{r.Bank_Account_ID} | {r.Bank_Name} | {r.Payment_Type} | Default:{r.Is_Default}": int(r.Bank_Account_ID)
            for r in acc.itertuples()
        }
        sel = st.selectbox("Select account", list(options.keys()), key="pay_default_select")

        if st.button("Set as Default", key="btn_set_default"):
            conn = get_connection()
            try:
                if getattr(conn, "in_transaction", False):
                    conn.rollback()
                conn.start_transaction()

                rc = set_default_account_tx(conn, sid, options[sel])
                conn.commit()

                if rc == 0:
                    st.warning("No changes were made.")
                else:
                    st.success("Default account updated.")
                st.rerun()

            except Exception as ex:
                try:
                    conn.rollback()
                except Exception:
                    pass
                st.error(f"Update failed: {ex}")
            finally:
                try:
                    conn.close()
                except Exception:
                    pass

    card_end()

if __name__ == "__main__":
    main()