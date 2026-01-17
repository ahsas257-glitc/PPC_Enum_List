import streamlit as st
from core.settings import APP_TITLE


def ensure_auth_state():
    st.session_state.setdefault("is_authenticated", False)
    st.session_state.setdefault("user_role", "viewer")
    st.session_state.setdefault("user_name", None)
    st.session_state.setdefault("username", None)


def _get_users_from_secrets():
    """
    Reads users from .streamlit/secrets.toml

    Expected structure:

    [users.admin]
    password = "admin123"
    full_name = "Admin"
    role = "admin"
    """
    try:
        users = st.secrets.get("users", {})
        if not isinstance(users, dict):
            return {}
        return users
    except Exception:
        return {}


def login_box():
    ensure_auth_state()

    st.subheader("User Login")

    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", key="login_username")
        password = st.text_input("Password", type="password", key="login_password")
        ok = st.form_submit_button("Login")

        if not ok:
            return

        username = (username or "").strip()
        password = (password or "").strip()

        if not username or not password:
            st.error("Username and password are required.")
            return

        users = _get_users_from_secrets()
        if not users:
            st.error("No users found in secrets.toml. Please configure [users.*] section.")
            return

        user = users.get(username)
        if not isinstance(user, dict):
            st.error("Invalid username or password.")
            return

        expected_password = str(user.get("password", "")).strip()
        if password != expected_password:
            st.error("Invalid username or password.")
            return

        st.session_state.is_authenticated = True
        st.session_state.user_role = str(user.get("role", "viewer")).strip() or "viewer"
        st.session_state.user_name = str(user.get("full_name", username)).strip() or username
        st.session_state.username = username

        st.success(f"Welcome, {st.session_state.user_name}.")
        st.rerun()


def require_login():
    ensure_auth_state()
    if not st.session_state.is_authenticated:
        st.title(APP_TITLE)
        login_box()
        st.stop()


def require_role(*roles):
    """
    Example: require_role("admin") or require_role("admin", "editor")
    """
    ensure_auth_state()
    if not st.session_state.is_authenticated:
        require_login()

    allowed = {r.strip() for r in roles if isinstance(r, str)}
    if allowed and st.session_state.user_role not in allowed:
        st.error("You do not have permission to access this page.")
        st.stop()


def logout_button():
    ensure_auth_state()

    if st.sidebar.button("Logout"):
        st.session_state.is_authenticated = False
        st.session_state.user_role = "viewer"
        st.session_state.user_name = None
        st.session_state.username = None

        # optional: clear form inputs
        st.session_state.pop("login_username", None)
        st.session_state.pop("login_password", None)

        st.rerun()
