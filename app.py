import streamlit as st
from ui.theme import init_page, apply_theme, theme_switcher
from ui.layout import navbar, sidebar_menu
from core.auth import ensure_auth_state
from core.settings import APP_TITLE
from path_bootstrap import ROOT  # فقط برای اطمینان از sys.path


def main():
    init_page(title=APP_TITLE, layout="wide")
    ensure_auth_state()

    sidebar_menu()
    theme = theme_switcher(default="light")
    apply_theme(theme)

    navbar(APP_TITLE, right_text="Home")

    st.title(APP_TITLE)
    st.caption("Surveyor database management system with strict validation and standardized design.")
    st.info("Use the left menu to navigate to the desired section.")


if __name__ == "__main__":
    main()

