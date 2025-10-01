# pages/dashboard.py
from __future__ import annotations
import streamlit as st
import plotly.express as px
from core.state import require_auth, go
from core import db

def _unique_instruments():
    ins = set()
    for it in db.list_pdfs():
        for k in it.get("instruments", []) or []:
            ins.add(k)
    return sorted(ins)

def render_dashboard():
    if not require_auth():
        st.stop()

    from modules.navbar import navbar
    navbar()

    # 顶部统计
    s = db.stats()
    c1, c2 = st.columns(2)
    with c1:
        st.metric(label="Total PDFs", value=s["total"])
    with c2:
        fig = px.pie(
            names=["CMCA Yes", "CMCA No"],
            values=[s["yes"], s["no"]],
            hole=0.55,
        )
        st.plotly_chart(fig, use_container_width=True, theme="streamlit")

    st.divider()

    # —— 左：上传；右：项目管理 ——
    up_col, proj_col = st.columns(2)

    # 上传 PDF
    with up_col:
        with st.expander("📤 Upload New PDF", expanded=False):
            f = st.file_uploader("Choose PDF", type=["pdf"], accept_multiple_files=False, key="uploader_pdf")
            meta_c1, meta_c2 = st.columns(2)
            with meta_c1:
                title = st.text_input("Title", placeholder="Auto use filename if empty", key="upload_title")
                # authors = st.text_input("Authors (comma-separated)", key="upload_authors")
                doi = st.text_input("DOI", key="upload_doi")
                year = st.selectbox("Year", ["2023", "2024", "2025"], index=1, key="upload_year")
            with meta_c2:
                projects = [p["name"] for p in db.list_projects()] or ["Documentation"]
                project = st.selectbox("Project", projects, index=0, key="upload_project")
                # instruments = st.text_input("Instruments (comma-separated)", key="upload_instruments")
                cmca_use = st.toggle("CMCA Use = Yes", value=True, key="upload_cmca_toggle")
            if st.button("Upload", type="primary", key="upload_btn"):
                meta = {
                    "title": title.strip() if title else None,
                    "authors": [a.strip() for a in authors.split(",") if a.strip()],
                    "affiliations": [],
                    "doi": doi.strip(),
                    "instruments": [x.strip() for x in instruments.split(",") if x.strip()],
                    "project": project,
                    "uploaded_by": st.session_state.get("user", {}).get("name", "Unknown"),
                    "size": f"{round((f.size/1024/1024),1)} MB" if f else "-",
                    "year": year,
                    "cosine": 0.0,
                    "cmca_use": "Yes" if cmca_use else "No",
                }
                db.add_pdf(f.read() if f else None, f.name if f else None, meta)
                st.success("Uploaded")
                st.session_state['_force_rerun'] = True

    # 新建 Project
    with proj_col:
        with st.expander("🗂️ Create New Project", expanded=False):
            p_name = st.text_input("Project Name", key="create_proj_name")
            p_year = st.selectbox("Year", ["2023", "2024", "2025"], index=1, key="create_proj_year")
            if st.button("Create Project", key="create_proj_btn"):
                try:
                    db.add_project(p_name, p_year)
                    st.success("Project created")
                    st.session_state['_force_rerun'] = True
                except Exception as e:
                    st.warning(str(e))

    st.divider()

    # 过滤/排序
    years = ["All"] + sorted({x.get("year") for x in db.list_pdfs() if x.get("year")})
    projects = ["All"] + [p["name"] for p in db.list_projects()]
    instruments_all = _unique_instruments()

    f1, f2, f3, f4 = st.columns([1, 1, 2, 1])
    with f1:
        year_filter = st.selectbox(
            "Year",
            years,
            index=years.index("2024") if "2024" in years else 0,
            key="filter_year",
        )
    with f2:
        project_filter = st.selectbox("Project", projects, key="filter_project")
    with f3:
        ins_sel = st.multiselect("Instrument Type", instruments_all, key="filter_instruments")
    with f4:
        sort_by = st.selectbox(
            "Sort By",
            ["Date (Newest First)", "Date (Oldest First)", "Title A→Z"],
            key="filter_sort",
        )

    items = db.list_pdfs(
        {
            "year": None if year_filter == "All" else year_filter,
            "project": None if project_filter == "All" else project_filter,
            "instruments": ins_sel if ins_sel else None,
        },
        sort_by=sort_by,
    )

    st.caption(f"Showing {len(items)} PDFs")

    for it in items:
        with st.container(border=True):
            cmca_badge = "CMCA Yes" if str(it.get("cmca_use", "")).lower() == "yes" else "CMCA No"
            st.markdown(f"**{it['title']}** — {cmca_badge}")
            st.caption(
                f"Project: {it.get('project','-')} · "
                f"Instruments: {', '.join(it.get('instruments', [])) or '-'} · "
                f"Uploaded: {it.get('upload_date','-')} · "
                f"Size: {it.get('size','-')} · "
                f"By: {it.get('uploaded_by','-')}"
            )
            st.button("Open", key=f"open_{it['id']}", on_click=lambda i=it['id']: _open_details(i))

def _open_details(pdf_id: str):
    go("details", current_pdf_id=pdf_id)
    st.session_state['_force_rerun'] = True
