import streamlit as st


def sidebar_menu():
    role = (st.session_state.get("user_role") or "viewer").strip().lower()

    st.sidebar.markdown("## PPC")
    st.sidebar.caption("Surveyor Database")
    st.sidebar.divider()

    st.sidebar.page_link("app.py", label="Home", icon="🏠")
    st.sidebar.page_link("pages/01_dashboard.py", label="Dashboard", icon="📊")
    st.sidebar.page_link("pages/08_public_search.py", label="Public Search", icon="🔎")

    if role in ("manager", "admin", "super_admin"):
        st.sidebar.divider()
        st.sidebar.page_link("pages/02_add_surveyor.py", label="Add Surveyor", icon="➕")
        st.sidebar.page_link("pages/05_projects.py", label="Projects", icon="📁")
        st.sidebar.page_link("pages/07_hiring.py", label="Hiring", icon="🧩")
        st.sidebar.page_link("pages/06_surveyor_payments.py", label="Payments", icon="💳")

    if role in ("admin", "super_admin"):
        st.sidebar.page_link("pages/04_banks.py", label="Banks", icon="🏦")
        st.sidebar.page_link("pages/03_admin.py", label="Admin", icon="🔐")


def navbar(brand: str, right_text: str = "") -> None:
    st.markdown(
        f"""
        <div class="ppc-navbar">
          <div class="ppc-brand">{brand}</div>
          <div class="ppc-navlinks">
            <div class="ppc-pill">{right_text}</div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
