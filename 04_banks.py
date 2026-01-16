import streamlit as st
from ui.theme import init_page, apply_theme, theme_switcher
from ui.layout import navbar, sidebar_menu
from ui.components import card_start, card_end
from core.auth import login_box
from core.db import load_banks, add_bank, set_bank_active

def main():
    init_page(title="PPC Surveyor Database", layout="wide")
    sidebar_menu()
    theme = theme_switcher(default="light")
    apply_theme(theme)
    navbar("PPC Surveyor Database", right_text="Banks")

    st.title("Banks (Admin)")

    if not st.session_state.get("is_admin", False):
        login_box()
        return

    card_start("Bank List", "Add a new bank and manage active/inactive status.")

    banks = load_banks(active_only=False)
    if banks.empty:
        st.warning("No banks found.")
    else:
        st.dataframe(banks, use_container_width=True)

    st.divider()

    st.subheader("Add New Bank")
    st.session_state.setdefault("bank_name", "")
    st.session_state.setdefault("bank_err", "")

    with st.form("add_bank_form", clear_on_submit=False):
        st.text_input("Bank Name *", key="bank_name")
        if st.session_state.bank_err:
            st.error(st.session_state.bank_err)

        ok = st.form_submit_button("Add Bank", type="primary")
        if ok:
            name = st.session_state.bank_name.strip()
            if not name:
                st.session_state.bank_err = "Bank name is required."
                st.stop()

            try:
                add_bank(name, "BANK_TRANSFER", 1)
                st.session_state.bank_err = ""
                st.success("Bank added successfully.")
                st.rerun()
            except Exception as ex:
                st.session_state.bank_err = str(ex)
                st.error(f"Add failed: {ex}")

    st.divider()

    st.subheader("Set Bank Status")
    if not banks.empty:
        options = {f"{r.Bank_Name} (ID:{r.Bank_ID})": int(r.Bank_ID) for r in banks.itertuples()}
        selected = st.selectbox("Select Bank", list(options.keys()))
        bank_id = options[selected]
        is_active = st.selectbox("Status", [1, 0], format_func=lambda x: "Active" if x == 1 else "Inactive")

        if st.button("Save Status"):
            try:
                set_bank_active(bank_id, is_active)
                st.success("Status saved.")
                st.rerun()
            except Exception as ex:
                st.error(f"Save failed: {ex}")

    card_end()

if __name__ == "__main__":
    main()