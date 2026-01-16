import streamlit as st
from core.db import query_df
from core.settings import APP_TITLE

def ensure_auth_state():
    st.session_state.setdefault("is_authenticated", False)
    st.session_state.setdefault("user_role", "viewer")
    st.session_state.setdefault("user_name", None)


def login_box():
    ensure_auth_state()

    st.subheader("User Login")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        ok = st.form_submit_button("Login")

        if ok:
            if not username.strip() or not password.strip():
                st.error("Username and password are required.")
                return

            df = query_df(
                """
                SELECT Username, Full_Name, Role
                FROM users
                WHERE Username=%s
                  AND Password_Hash=SHA2(%s,256)
                  AND Is_Active=1
                LIMIT 1
                """,
                (username.strip(), password.strip()),
            )

            if df.empty:
                st.error("Invalid username or password.")
                return

            row = df.iloc[0]
            st.session_state.is_authenticated = True
            st.session_state.user_role = row["Role"]
            st.session_state.user_name = row["Full_Name"] or row["Username"]

            st.success(f"Welcome, {st.session_state.user_name}.")
            st.rerun()


def require_login():
    ensure_auth_state()
    if not st.session_state.is_authenticated:
        login_box()
        st.stop()


def require_role(*roles):
    ensure_auth_state()
    if st.session_state.user_role not in roles:
        st.error("You do not have permission to access this page.")
        st.stop()


def logout_button():
    if st.sidebar.button("Logout"):
        st.session_state.is_authenticated = False
        st.session_state.user_role = "viewer"
        st.session_state.user_name = None
        st.rerun()
