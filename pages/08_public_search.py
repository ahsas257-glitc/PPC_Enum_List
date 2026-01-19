import streamlit as st
import pandas as pd
from core.db import query_df
from ui.theme import init_page, apply_theme, theme_switcher
from ui.layout import navbar, sidebar_menu
from ui.components import card_start, card_end

# -----------------------------
# Helpers (UI + Public Safety)
# -----------------------------

def _mask_phone(v: str) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if not s:
        return ""
    digits = re.sub(r"\D+", "", s)
    if len(digits) <= 4:
        return "*" * len(digits)
    keep = 4 if len(digits) >= 8 else 3
    return ("*" * (len(digits) - keep)) + digits[-keep:]

def _mask_tazkira(v: str) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if not s:
        return ""
    if len(s) <= 3:
        return "*" * len(s)
    return ("*" * (len(s) - 3)) + s[-3:]

def _safe_str(x):
    return "" if x is None else str(x)

def _highlight_matches(df: pd.DataFrame, q: str):
    query = q.strip()
    if not query:
        return df.style
    pat = re.compile(re.escape(query), re.IGNORECASE)

    def style_cell(val):
        s = _safe_str(val)
        if pat.search(s):
            return "background-color: rgba(255, 230, 150, 0.75); font-weight: 600;"
        return ""
    return df.style.applymap(style_cell)

def _get_province_options():
    try:
        p = query_df(
            """
            SELECT province_code, province_name
            FROM provinces
            ORDER BY province_name
            """
        )
        if p.empty:
            return []
        return list(zip(p["province_code"].tolist(), p["province_name"].tolist()))
    except Exception:
        return []

def _get_project_options():
    try:
        p = query_df(
            """
            SELECT project_id, project_name
            FROM projects
            ORDER BY project_name
            """
        )
        if p.empty:
            return []
        return list(zip(p["project_id"].tolist(), p["project_name"].tolist()))
    except Exception:
        return []

# -----------------------------
# Main Page
# -----------------------------
def main():
    init_page(title="PPC Surveyor Database", layout="wide")
    sidebar_menu()
    theme = theme_switcher(default="light")
    apply_theme(theme)
    navbar("PPC Surveyor Database", right_text="Public Search")

    st.title("🔎 Public Surveyor Search")
    st.caption("Read-only public search portal (limited fields).")

    # UI state
    if "ps_page" not in st.session_state:
        st.session_state.ps_page = 0
    if "ps_q" not in st.session_state:
        st.session_state.ps_q = ""
    if "ps_prov" not in st.session_state:
        st.session_state.ps_prov = "ALL"
    if "ps_proj" not in st.session_state:
        st.session_state.ps_proj = "ALL"
    if "ps_page_size" not in st.session_state:
        st.session_state.ps_page_size = 20

    # Card container
    card_start(
        "Public Search",
        "Search by Surveyor Code, Tazkira, Name, Phone or WhatsApp. "
        "Use filters to narrow down. Results are limited and masked for privacy."
    )

    # Filters Section
    col1, col2, col3 = st.columns([2, 1.2, 1.2])

    with col1:
        q = st.text_input(
            "Search",
            key="ps_q",
            placeholder="Example: PPC-KAB-001 | 1234-5678-91011 | Name | Phone",
            help="Auto search runs when you type. Use filters for better results."
        )

    province_options = _get_province_options()
    prov_map = {"ALL": "All Provinces"}
    for code, name in province_options:
        prov_map[str(code)] = name

    with col2:
        prov_choice = st.selectbox(
            "Province",
            options=list(prov_map.keys()),
            format_func=lambda k: prov_map.get(k, k),
            key="ps_prov"
        )

    project_options = _get_project_options()
    proj_map = {"ALL": "All Projects"}
    for code, name in project_options:
        proj_map[str(code)] = name

    with col3:
        proj_choice = st.selectbox(
            "Project",
            options=list(proj_map.keys()),
            format_func=lambda k: proj_map.get(k, k),
            key="ps_proj"
        )

    # Results per page
    c4, c5 = st.columns([1, 1])
    with c4:
        page_size = st.selectbox(
            "Results per page",
            options=[10, 20, 30, 50],
            key="ps_page_size"
        )

    # Reset pagination when query/filters change
    snapshot = (st.session_state.ps_q.strip(), st.session_state.ps_prov, st.session_state.ps_proj, st.session_state.ps_page_size)
    if "ps_snapshot" not in st.session_state:
        st.session_state.ps_snapshot = snapshot
    if st.session_state.ps_snapshot != snapshot:
        st.session_state.ps_page = 0
        st.session_state.ps_snapshot = snapshot

    q_clean = (st.session_state.ps_q or "").strip()

    if not q_clean and st.session_state.ps_prov == "ALL" and st.session_state.ps_proj == "ALL":
        st.info("Type a search value or use filters to see results.")
        card_end()
        return

    # Build SQL filters
    where_parts = []
    params = {}

    if q_clean:
        params["like"] = f"%{q_clean}%"
        where_parts.append(
            """
            (
                s.surveyor_code LIKE %(like)s
                OR s.surveyor_name LIKE %(like)s
                OR s.tazkira_no LIKE %(like)s
                OR s.phone_number LIKE %(like)s
                OR s.whatsapp_number LIKE %(like)s
            )
            """
        )

    if st.session_state.ps_prov != "ALL":
        params["prov"] = st.session_state.ps_prov
        where_parts.append(
            """
            (
                s.permanent_province_code = %(prov)s
                OR s.current_province_code = %(prov)s
            )
            """
        )

    if st.session_state.ps_proj != "ALL":
        params["proj"] = st.session_state.ps_proj
        where_parts.append(
            """
            s.project_id = %(proj)s
            """
        )

    where_sql = " AND ".join([p.strip() for p in where_parts if p.strip()])
    if not where_sql:
        where_sql = "1=1"

    # Pagination
    page = int(st.session_state.ps_page)
    page_size = int(st.session_state.ps_page_size)
    offset = page * page_size

    # Query data (Public-safe columns)
    df = query_df(
        f"""
        SELECT
          s.surveyor_code,
          s.surveyor_name,
          s.gender,
          s.father_name,
          s.tazkira_no,
          s.whatsapp_number,
          s.phone_number,
          pp.province_name AS permanent_province,
          cp.province_name AS current_province,
          p.project_name AS project_name,
          DATE(s.created_at) AS created_date
        FROM surveyors s
        LEFT JOIN provinces pp ON pp.province_code = s.permanent_province_code
        LEFT JOIN provinces cp ON cp.province_code = s.current_province_code
        LEFT JOIN projects p ON p.project_id = s.project_id
        WHERE {where_sql}
        ORDER BY s.surveyor_id DESC
        LIMIT {page_size} OFFSET {offset}
        """,
        params
    )

    st.divider()

    # Header stats + pager controls
    total_found = len(df)
    _render_header_stats(total_found=total_found, page=page, page_size=page_size)

    pager_left, pager_mid, pager_right = st.columns([1, 2, 1])

    with pager_left:
        prev_disabled = page <= 0
        if st.button("⬅️ Prev", use_container_width=True, disabled=prev_disabled):
            st.session_state.ps_page = max(0, page - 1)
            st.rerun()

    with pager_mid:
        if total_found > 0:
            total_pages = max(1, (total_found + page_size - 1) // page_size)
            st.caption(f"Showing page {page + 1} of {total_pages} | Total records: {total_found}")
        else:
            st.caption("No records count available or no results.")

    with pager_right:
        next_disabled = True
        if total_found > 0:
            total_pages = max(1, (total_found + page_size - 1) // page_size)
            next_disabled = (page + 1) >= total_pages

        if st.button("Next ➡️", use_container_width=True, disabled=next_disabled):
            st.session_state.ps_page = page + 1
            st.rerun()

    # Render results as Cards
    if df is None or df.empty:
        st.warning("No results found.")
        card_end()
        return

    # Masking
    df["phone_number"] = df["phone_number"].apply(_mask_phone)
    df["whatsapp_number"] = df["whatsapp_number"].apply(_mask_phone)
    df["tazkira_no"] = df["tazkira_no"].apply(_mask_tazkira)

    # Styling and final rendering
    styled = _highlight_matches(df, q_clean)

    st.dataframe(styled, use_container_width=True, hide_index=True)

    # Public note
    with st.expander("Public Mode & Privacy"):
        st.write(
            "This is a read-only public page. Sensitive fields are masked and results are limited per page. "
            "For full access, use the internal dashboard."
        )

    card_end()

def _render_header_stats(total_found: int, page: int, page_size: int):
    left, mid, right = st.columns([1, 1, 1])
    left.metric("Found", total_found)
    mid.metric("Page", page + 1)
    right.metric("Page size", page_size)

if __name__ == "__main__":
    main()
