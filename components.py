from __future__ import annotations
import streamlit as st

def card_start(title: str, subtitle: str | None = None):
    st.markdown("<div class='ppc-card'>", unsafe_allow_html=True)
    st.subheader(title)
    if subtitle:
        st.markdown(f"<div class='ppc-muted'>{subtitle}</div>", unsafe_allow_html=True)
    st.write("")

def card_end():
    st.markdown("</div>", unsafe_allow_html=True)

def field_error(msg: str | None):
    if msg:
        st.markdown(f"<div class='ppc-hint'>⚠️ {msg}</div>", unsafe_allow_html=True)

def toast_ok(msg: str):
    st.success(msg)

def toast_err(msg: str):
    st.error(msg)
