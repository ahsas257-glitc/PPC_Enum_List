import streamlit as st


def set_global_style():
    st.set_page_config(page_title="PPC Surveyor Database", layout="wide")
    st.markdown(
        """
        <style>
          .block-container { padding-top: 1.2rem; padding-bottom: 2rem; }
          .ppc-card {
            border: 1px solid rgba(49, 51, 63, 0.2);
            border-radius: 16px;
            padding: 18px 18px 8px 18px;
            background: rgba(255,255,255,0.02);
          }
          .ppc-hint {
            color: #d33;
            font-size: 0.86rem;
            margin-top: -6px;
            margin-bottom: 8px;
          }
          .ppc-muted { opacity: 0.75; font-size: 0.9rem; }
        </style>
        """,
        unsafe_allow_html=True
    )


def field_error(msg: str | None):
    """نمایش خطا دقیقاً زیر همان فیلد (بدون پاک شدن دیتا)."""
    if msg:
        st.markdown(f"<div class='ppc-hint'>⚠️ {msg}</div>", unsafe_allow_html=True)


def card_start(title: str, subtitle: str | None = None):
    st.markdown("<div class='ppc-card'>", unsafe_allow_html=True)
    st.subheader(title)
    if subtitle:
        st.markdown(f"<div class='ppc-muted'>{subtitle}</div>", unsafe_allow_html=True)
    st.write("")


def card_end():
    st.markdown("</div>", unsafe_allow_html=True)
