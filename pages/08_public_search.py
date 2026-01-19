import re
import pandas as pd
import streamlit as st

from ui.theme import init_page, apply_theme, theme_switcher
from ui.layout import navbar, sidebar_menu
from ui.components import card_start, card_end
from core.db import query_df


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
    # keep last 3-4 digits
    keep = 4 if len(digits) >= 8 else 3
    return ("*" * (len(digits) - keep)) + digits[-keep:]


def _mask_tazkira(v: str) -> str:
    if v is None:
        return ""
    s = str(v).strip()
    if not s:
        return ""
    # keep last 3 chars visible
    if len(s) <= 3:
        return "*" * len(s)
    return ("*" * (len(s) - 3)) + s[-3:]


def _safe_str(x):
    return "" if x is None else str(x)


def _highlight_matches(df: pd.DataFrame, q: str):
    """
    Highlight any cell containing q (case-insensitive).
    """
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
            SELECT Province_Code, Province_Name
            FROM provinces
            ORDER BY Province_Name
            """
        )
        if p.empty:
            return []
        return list(zip(p["Province_Code"].tolist(), p["Province_Name"].tolist()))
    except Exception:
        return []


def _get_org_options_if_any():
    """
    Optional: works only if you have organization fields/tables.
    If not available, it will quietly return empty.
    Adjust query to your real schema if needed.
    """
    candidates = [
        # Option A: organizations table
        """
        SELECT Organization_Code AS Org_Code, Organization_Name AS Org_Name
        FROM organizations
        ORDER BY Organization_Name
        """,
        # Option B: field on surveyors table
        """
        SELECT DISTINCT Organization AS Org_Name
        FROM surveyors
        WHERE Organization IS NOT NULL AND Organization <> ''
        ORDER BY Organization
        """,
    ]

    for sql in candidates:
        try:
            o = query_df(sql)
            if o is None or o.empty:
                continue

            # normalize into list of tuples (code_or_name, name)
            if "Org_Code" in o.columns and "Org_Name" in o.columns:
                return list(zip(o["Org_Code"].tolist(), o["Org_Name"].tolist()))
            if "Org_Name" in o.columns:
                return [(name, name) for name in o["Org_Name"].tolist()]
        except Exception:
            continue

    return []


def _render_header_stats(total_found: int, page: int, page_size: int):
    left, mid, right = st.columns([1, 1, 1])
    left.metric("Found", total_found)
    mid.metric("Page", page + 1)
    right.metric("Page size", page_size)


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
    if "ps_org" not in st.session_state:
        st.session_state.ps_org = "ALL"
    if "ps_page_size" not in st.session_state:
        st.session_state.ps_page_size = 20

    # Card container
    card_start(
        "Public Search",
        "Search by Surveyor Code, Tazkira, Name, Phone or WhatsApp. "
        "Use filters to narrow down. Results are limited and masked for privacy."
    )

    # Top filters (mobile-friendly: columns collapse naturally)
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

    org_options = _get_org_options_if_any()
    org_map = {"ALL": "All Organizations"}
    for code, name in org_options:
        org_map[str(code)] = name

    with col3:
        if len(org_options) > 0:
            org_choice = st.selectbox(
                "Organization",
                options=list(org_map.keys()),
                format_func=lambda k: org_map.get(k, k),
                key="ps_org"
            )
        else:
            st.caption("Organization filter not available")
            st.session_state.ps_org = "ALL"

    # Secondary controls
    c4, c5, c6 = st.columns([1, 1, 1])
    with c4:
        page_size = st.selectbox(
            "Results per page",
            options=[10, 20, 30, 50],
            key="ps_page_size"
        )
    with c5:
        mask_mode = st.toggle("Privacy mask", value=True, help="Mask phone/tazkira for public view.")
    with c6:
        compact = st.toggle("Compact table", value=False)

    # Reset pagination when query/filters change
    # (simple approach: compare against stored snapshot)
    snapshot = (st.session_state.ps_q.strip(), st.session_state.ps_prov, st.session_state.ps_org, st.session_state.ps_page_size)
    if "ps_snapshot" not in st.session_state:
        st.session_state.ps_snapshot = snapshot
    if st.session_state.ps_snapshot != snapshot:
        st.session_state.ps_page = 0
        st.session_state.ps_snapshot = snapshot

    q_clean = (st.session_state.ps_q or "").strip()

    if not q_clean and st.session_state.ps_prov == "ALL" and st.session_state.ps_org == "ALL":
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
                s.Surveyor_Code LIKE %(like)s
                OR s.Tazkira_No LIKE %(like)s
                OR s.Surveyor_Name LIKE %(like)s
                OR s.Phone_Number LIKE %(like)s
                OR s.Whatsapp_Number LIKE %(like)s
            )
            """
        )

    if st.session_state.ps_prov != "ALL":
        params["prov"] = st.session_state.ps_prov
        where_parts.append(
            """
            (
                s.Permanent_Province_Code = %(prov)s
                OR s.Current_Province_Code = %(prov)s
            )
            """
        )

    # Organization filter (optional)
    # Adjust this to your actual schema if you have it
    org_filter_sql = ""
    if len(org_options) > 0 and st.session_state.ps_org != "ALL":
        params["org"] = st.session_state.ps_org
        # Option A: organizations join with code
        # Option B: surveyors.Organization field equals selected value
        org_filter_sql = """
            AND (
                s.Organization = %(org)s
                OR s.Organization_Code = %(org)s
            )
        """

    where_sql = " AND ".join([p.strip() for p in where_parts if p.strip()])
    if not where_sql:
        where_sql = "1=1"

    # Pagination
    page = int(st.session_state.ps_page)
    page_size = int(st.session_state.ps_page_size)
    offset = page * page_size

    # Total count for pagination
    try:
        total_df = query_df(
            f"""
            SELECT COUNT(*) AS total
            FROM surveyors s
            WHERE {where_sql}
            {org_filter_sql}
            """,
            params
        )
        total_found = int(total_df.iloc[0]["total"]) if not total_df.empty else 0
    except Exception:
        total_found = 0

    # Query data (Public-safe columns)
    df = query_df(
        f"""
        SELECT
          s.Surveyor_Code,
          s.Surveyor_Name,
          s.Gender,
          s.Father_Name,
          s.Tazkira_No,
          s.Whatsapp_Number,
          s.Phone_Number,
          pp.Province_Name AS Permanent_Province,
          cp.Province_Name AS Current_Province,
          DATE(s.Created_At) AS Created_Date
        FROM surveyors s
        LEFT JOIN provinces pp ON pp.Province_Code = s.Permanent_Province_Code
        LEFT JOIN provinces cp ON cp.Province_Code = s.Current_Province_Code
        WHERE {where_sql}
        {org_filter_sql}
        ORDER BY s.Surveyor_ID DESC
        LIMIT {page_size} OFFSET {offset}
        """,
        params
    )

    st.divider()

    # Header stats + pager controls
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
        # Next is disabled if we're at/after last page
        next_disabled = True
        if total_found > 0:
            total_pages = max(1, (total_found + page_size - 1) // page_size)
            next_disabled = (page + 1) >= total_pages

        if st.button("Next ➡️", use_container_width=True, disabled=next_disabled):
            st.session_state.ps_page = page + 1
            st.rerun()

    # Render results
    if df is None or df.empty:
        st.warning("No results found.")
        card_end()
        return

    # Public masking
    if mask_mode:
        if "Phone_Number" in df.columns:
            df["Phone_Number"] = df["Phone_Number"].apply(_mask_phone)
        if "Whatsapp_Number" in df.columns:
            df["Whatsapp_Number"] = df["Whatsapp_Number"].apply(_mask_phone)
        if "Tazkira_No" in df.columns:
            df["Tazkira_No"] = df["Tazkira_No"].apply(_mask_tazkira)

    # Optional: reorder columns for best UX
    preferred_order = [
        "Surveyor_Code",
        "Surveyor_Name",
        "Gender",
        "Father_Name",
        "Phone_Number",
        "Whatsapp_Number",
        "Permanent_Province",
        "Current_Province",
        "Tazkira_No",
        "Created_Date",
    ]
    existing = [c for c in preferred_order if c in df.columns]
    df = df[existing]

    # Highlight
    styled = _highlight_matches(df, q_clean)

    # Table options
    if compact:
        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True,
            height=420
        )
    else:
        st.dataframe(
            styled,
            use_container_width=True,
            hide_index=True
        )

    # Public note
    with st.expander("Public Mode & Privacy"):
        st.write(
            "This is a read-only public page. Sensitive fields are masked and results are limited per page. "
            "For full access, use the internal dashboard."
        )

    card_end()


if __name__ == "__main__":
    main()
