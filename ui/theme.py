from __future__ import annotations
from pathlib import Path
import streamlit as st

CSS_DIR = Path(__file__).parent / "assets" / "css"

def _inject_css(path: Path) -> None:
    st.markdown(f"<style>{path.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

def init_page(title: str = "PPC Surveyor Database", layout: str = "wide") -> None:
    st.set_page_config(page_title=title, layout=layout)

def apply_theme(theme: str) -> None:
    theme = (theme or "light").lower().strip()
    _inject_css(CSS_DIR / "base.css")
    if theme == "dark":
        _inject_css(CSS_DIR / "dark.css")
    else:
        _inject_css(CSS_DIR / "light.css")

def theme_switcher(default: str = "light") -> str:
    if "ppc_theme" not in st.session_state:
        st.session_state.ppc_theme = default
    chosen = st.sidebar.radio("Theme", ["light", "dark"], index=0 if st.session_state.ppc_theme=="light" else 1)
    st.session_state.ppc_theme = chosen
    return chosen
