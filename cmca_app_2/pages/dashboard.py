# pages/dashboard.py
from __future__ import annotations
from collections import Counter

import streamlit as st
import plotly.express as px


import base64
from pathlib import Path

def _b64_file(p: str) -> str:
    with open(Path(p), "rb") as f:
        return base64.b64encode(f.read()).decode()



# --- DEV MODE helpers (safe: only active when DEV_MODE=1) ---
import os
DEV_MODE = os.getenv("DEV_MODE") == "1"

def _mock_pdfs():
    return [
        {"pdf_id": 101, "title": "sample1.pdf", "project_id": 1,
         "instruments_json": ["SEM"], "upload_date": "2025-10-01",
         "uploaded_by": "alice", "cmca_result": "Yes", "publish_date": "2024-07-10"},
        {"pdf_id": 102, "title": "sample2.pdf", "project_id": 2,
         "instruments_json": ["TEM", "EDS"], "upload_date": "2025-10-02",
         "uploaded_by": "bob", "cmca_result": "No", "publish_date": "2024-05-03"},
        {"pdf_id": 103, "title": "draft3.pdf", "project_id": 1,
         "instruments_json": ["AFM"], "upload_date": "2025-10-03",
         "uploaded_by": "charlie", "cmca_result": "Yes", "publish_date": "2023-12-20"},
    ]


from core.state import require_auth, go
from core.api import get as api_get, post_json as api_post, post_multipart as api_post_multipart


# ------------------------------ API wrappers ------------------------------
def _auth_token() -> str | None:
    return st.session_state.get("token")

def _api_projects() -> list[dict]:
    """
    GET /projects  (Authorization: Bearer <token>)
    Normalizes to [{'id', 'name'}] where 'id' may be 'project_id' in backend.
    """
    data = api_get("/projects", token=_auth_token()) or []
    out: list[dict] = []
    for p in data:
        out.append({
            "id": p.get("id") or p.get("project_id"),
            "name": (p.get("project_name") or p.get("name") or "").strip(),
        })
    return out

def _api_create_project(name: str) -> dict:
    """
    POST /projects  { "project_name": "<name>" }
    """
    payload = {"project_name": name.strip()}
    return api_post("/projects", payload, token=_auth_token())

def _api_list_pdfs(project_id: int | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    """
    GET /pdfs  (optional ?project_id=&limit=&offset=)
    """
    params = {"limit": limit, "offset": offset}
    if project_id is not None:
        params["project_id"] = project_id
    return api_get("/pdfs", token=_auth_token(), params=params) or []

def _api_get_pdf(pdf_id: int) -> dict:
    """
    GET /pdfs/{pdf_id}
    """
    return api_get(f"/pdfs/{pdf_id}", token=_auth_token()) or {}

def _api_upload_pdf(file, project_id: int | None = None, overrides: dict | None = None) -> dict:
    """
    POST /pdfs/upload  (multipart/form-data)
    files = {"file": (filename, bytes, "application/pdf")}
    data  = {project_id, title, authors, affiliation, doi, publish_date}
    """
    files = None
    if file is not None:
        files = {"file": (file.name, file.getvalue(), "application/pdf")}
    data: dict = {}
    if project_id is not None:
        data["project_id"] = str(project_id)
    if overrides:
        for k, v in overrides.items():
            if v not in (None, ""):
                data[k] = v
    return api_post_multipart("/pdfs/upload", files=files, data=data, token=_auth_token())


# ------------------------------ Page ------------------------------
def render_dashboard():
    if not (DEV_MODE or require_auth()):
        st.stop()

    # ---- Navbar (unchanged if you have one) ----
    try:
        from modules.navbar import navbar
        navbar()
    except Exception:
        pass

    # --- DEV MODE mock dashboard: skip backend calls and render preview ---
    if DEV_MODE:
        st.title("CMCA PDF Dashboard (Mock)")
        st.caption("Previewing layout in DEV MODE – no backend calls")

        all_pdfs = _mock_pdfs()

        # KPIs + charts (same layout as real)
        yes = sum(1 for x in all_pdfs if (x.get("cmca_result") or "").lower() == "yes")
        no  = sum(1 for x in all_pdfs if (x.get("cmca_result") or "").lower() == "no")

        from collections import Counter
        counts = Counter()
        for row in all_pdfs:
            for inst in set(str(i) for i in (row.get("instruments_json") or [])):
                counts[inst] += 1
        top_items = counts.most_common(5)
        bar_rows = [{"instrument": k, "pdfs": v} for k, v in top_items]


        # ----------- CMCA image banner with overlaid title -----------
        img_path = "website_images/CMCA_Images_hero_color.jpg"

        if not Path(img_path).exists():
            st.error(f"Image not found: {img_path}")
        else:
            b64 = _b64_file(img_path)  # ← use your helper here

            st.markdown(f"""
            <style>
            .cmca-hero {{
                position: relative;
                height: 230px;
                border-radius: 12px;
                overflow: hidden;
                box-shadow: 0 6px 22px rgba(0,0,0,0.15);
                margin: .5rem 0 1rem 0;
                background: url("data:image/jpeg;base64,{b64}") center/cover no-repeat;
            }}
            .cmca-hero::before {{
                content: "";
                position: absolute; inset: 0;
                background: rgba(0,0,0,0.18);
            }}
            .cmca-hero__text {{
                position: absolute;
                top: 50%; left: 50%;
                transform: translate(-50%, -50%);
                text-align: center;
                color: #FFF;
                z-index: 2;
                text-shadow: 0 2px 10px rgba(0,0,0,0.55);
            }}
            .cmca-hero__text h2 {{
                margin: 0;
                font-size: 2.0rem;
                font-weight: 800;
            }}
            .cmca-hero__text h3 {{
                margin: .35rem 0 0;
                font-size: 1.75rem;
                font-weight: 800;
            }}
            </style>

            <div class="cmca-hero">
            <div class="cmca-hero__text">
                <h2>Centre for Microscopy</h2>
                <h3>Characterisation and Analysis</h3>
            </div>
            </div>
            """, unsafe_allow_html=True)

        st.divider()


        # ---------- Charts ---------
        c_pie, c_bar = st.columns(2)
        with c_pie:
            if yes + no > 0:
                fig = px.pie(names=["CMCA Yes", "CMCA No"], values=[yes, no], hole=0.55)
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No CMCA-labelled PDFs yet — upload a PDF to see this chart.")
        with c_bar:
            st.subheader("Top instruments by PDFs")
            if not bar_rows:
                st.info("No instrument data yet.")
            else:
                fig_bar = px.bar(bar_rows, x="instrument", y="pdfs")
                fig_bar.update_layout(xaxis_title="Instrument", yaxis_title="# PDFs", bargap=0.25)
                st.plotly_chart(fig_bar, use_container_width=True)

        st.divider()
        st.caption(f"Showing {len(all_pdfs)} PDFs")

        for it in all_pdfs:
            with st.container(border=True):
                cmca_badge = "CMCA Yes" if str(it.get("cmca_result")).lower() == "yes" else "CMCA No"
                st.markdown(f"**{it.get('title','(untitled)')}** — {cmca_badge}")
                st.caption(
                    f"Project: {it.get('project_id','-')} · "
                    f"Instruments: {', '.join(it.get('instruments_json', [])) or '-'} · "
                    f"Uploaded: {it.get('upload_date','-')} · "
                    f"By: {it.get('uploaded_by','-')}"
                )
                if st.button("Open", key=f"open_{it['pdf_id']}"):
                    go("details", current_pdf_id=it["pdf_id"])
                    st.session_state['_force_rerun'] = True
                    st.rerun()

        return  # important: do not run the real backend code below when in DEV


    # ---- Top stats (computed from backend PDFs) ----
    # ---- Top charts: Pie (CMCA) + Bar (Top instruments by #PDFs) ----
    try:
        all_pdfs = _api_list_pdfs(limit=200, offset=0)
    except Exception as e:
        st.warning(f"Could not load PDFs for stats: {e}")
        all_pdfs = []

    yes = sum(1 for x in all_pdfs if (x.get("cmca_result") or "").lower() == "yes")
    no  = sum(1 for x in all_pdfs if (x.get("cmca_result") or "").lower() == "no")


    # count PDFs per instrument (a PDF counts once per instrument)
    counts = Counter()
    for row in all_pdfs:
        instruments = row.get("instruments_json") or []
        # dedupe within a single PDF just in case
        for inst in set(str(i) for i in instruments):
            counts[inst] += 1

    # top 5 bars
    top_items = counts.most_common(5)
    bar_rows = [{"instrument": k, "pdfs": v} for k, v in top_items]

    # ------CMCA Header Image ------
    st.markdown("### 🧪 Centre for Microscopy, Characterisation & Analysis")
    st.image("website_images/CMCA_Images.tif", use_container_width=True)
    st.divider()

    
    c_pie, c_bar = st.columns(2)

    # Top charts: Pie (CMCA) + Bar (Top instruments by #PDFs) 
    c_pie, c_bar = st.columns(2)

    with c_pie:
        if yes + no > 0:
            fig = px.pie(names=["CMCA Yes", "CMCA No"], values=[yes, no], hole=0.55)
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("No CMCA-labelled PDFs yet — upload a PDF to see this chart.")

    with c_bar:
        st.subheader("Top instruments by PDFs")
        if not bar_rows:
            st.info("No instrument data yet.")
        else:
            fig_bar = px.bar(bar_rows, x="instrument", y="pdfs")
            fig_bar.update_layout(xaxis_title="Instrument", yaxis_title="# PDFs", bargap=0.25)
            st.plotly_chart(fig_bar, use_container_width=True)

    st.divider()

    # —— Left: Upload —— Right: Project management ——
    up_col, proj_col = st.columns(2)

    # ------------------------ Upload PDF (file + project only) ------------------------
    with up_col:
        with st.expander("📤 Upload New PDF", expanded=False):
            # nonce ensures the uploader gets a fresh key after each successful upload
            nonce = st.session_state.get("upload_nonce", 0)

            with st.form("upload_form", clear_on_submit=True):
                f = st.file_uploader(
                    "Choose PDF",
                    type=["pdf"],
                    accept_multiple_files=False,
                    key=f"uploader_pdf_{nonce}",
                )

                # Pull projects from API
                projects_data = _api_projects()
                project_names = [p["name"] for p in projects_data] or ["Documentation"]
                project_sel = st.selectbox(
                    "Project",
                    project_names,
                    index=0,
                    key=f"upload_project_{nonce}",
                )

                submitted = st.form_submit_button("Upload", disabled=(f is None))
                if submitted and f is not None:
                    try:
                        # Map selected project name -> id
                        project_id = None
                        for p in projects_data:
                            if p["name"] == project_sel:
                                project_id = p.get("id")
                                break

                        # No overrides — extractor/LLM will populate metadata
                        resp = _api_upload_pdf(f, project_id=project_id, overrides={})
                        st.success(f"Uploaded: {resp.get('title') or f.name} (pdf_id {resp.get('pdf_id')})")

                        # add these two lines for auto-refresh
                        st.session_state["upload_nonce"] = nonce + 1
                        st.session_state['_force_rerun'] = True
                        st.rerun()

                    except Exception as e:
                        st.error(f"Upload failed: {e}")




    # -------------------- Create Project (API) --------------------
    if "exp_create_open" not in st.session_state:
        st.session_state["exp_create_open"] = False

    with proj_col:
        with st.expander("🗂️ Create New Project", expanded=st.session_state["exp_create_open"]):
            p_name = st.text_input("Project Name", key="create_proj_name")
            if st.button("Create Project", key="create_proj_btn", type="primary", use_container_width=True):
                if not p_name.strip():
                    st.warning("Please enter a project name.")
                else:
                    try:
                        created = _api_create_project(p_name)
                        shown = created.get("project_name") or p_name
                        st.success(f"Project “{shown}” created.")
                        st.session_state["create_proj_name"] = ""
                        st.session_state["exp_create_open"] = False
                        st.session_state['_force_rerun'] = True
                        st.rerun()
                    except Exception as e:
                        st.error(f"Failed to create project: {e}")

    st.divider()

    # -------------------- Filters / sorting --------------------
    # Build filter sources
    project_names_for_filter = ["All"] + [p["name"] for p in _api_projects()]

    def _unique_instruments(items: list[dict]) -> list[str]:
        ins = set()
        for it in items:
            for k in (it.get("instruments_json") or []):
                ins.add(k)
        return sorted(ins)

    f1, f2, f3, f4 = st.columns([1, 1, 2, 1])
    with f1:
        # publish_date is optional; derive year only for display filter
        years = ["All"] + sorted({(it.get("publish_date") or "")[:4] for it in all_pdfs if it.get("publish_date")})
        default_index = years.index("2024") if "2024" in years else 0
        year_filter = st.selectbox("Year", years, index=default_index, key="filter_year")
    with f2:
        project_filter = st.selectbox("Project", project_names_for_filter, key="filter_project")
    with f3:
        instruments_all = _unique_instruments(all_pdfs)
        ins_sel = st.multiselect("Instrument Type", instruments_all, key="filter_instruments")
    with f4:
        sort_by = st.selectbox("Sort By", ["Date (Newest First)", "Date (Oldest First)", "Title A→Z"], key="filter_sort")

    # Fetch filtered list from backend (project filter server-side; others client-side)
    try:
        project_filter_id = None
        if project_filter != "All":
            for p in _api_projects():
                if p["name"] == project_filter:
                    project_filter_id = p.get("id")
                    break
        raw_items = _api_list_pdfs(project_id=project_filter_id, limit=200, offset=0)
    except Exception as e:
        st.error(f"Failed to load PDFs: {e}")
        raw_items = []

    # Client-side filter for year and instruments
    def _year_of(it: dict) -> str | None:
        d = it.get("publish_date")
        return (d or "")[:4] if d else None

    filtered = []
    for it in raw_items:
        y = _year_of(it)
        if year_filter != "All" and y != year_filter:
            continue
        if ins_sel:
            have = set(it.get("instruments_json") or [])
            if not have.issuperset(ins_sel):
                continue
        filtered.append(it)

    # Sorting
    if sort_by == "Date (Newest First)":
        filtered.sort(key=lambda x: x.get("upload_date") or "", reverse=True)
    elif sort_by == "Date (Oldest First)":
        filtered.sort(key=lambda x: x.get("upload_date") or "")
    else:  # Title A→Z
        filtered.sort(key=lambda x: (x.get("title") or "").lower())

    st.caption(f"Showing {len(filtered)} PDFs")

    # Normalize for display and render cards
    for it in filtered:
        display = {
            "id": it.get("pdf_id"),
            "title": it.get("title") or "(untitled)",
            "project": it.get("project_id"),
            "instruments": it.get("instruments_json") or [],
            "upload_date": it.get("upload_date"),
            "uploaded_by": it.get("uploaded_by"),
            "cmca_use": it.get("cmca_result", "-"),
            "year": _year_of(it),
        }
        with st.container(border=True):
            cmca_badge = "CMCA Yes" if str(display["cmca_use"]).lower() == "yes" else "CMCA No"
            st.markdown(f"**{display['title']}** — {cmca_badge}")
            st.caption(
                f"Project: {display.get('project','-')} · "
                f"Instruments: {', '.join(display.get('instruments', [])) or '-'} · "
                f"Uploaded: {display.get('upload_date','-')} · "
                f"By: {display.get('uploaded_by','-')}"
            )
            st.button("Open", key=f"open_{display['id']}", on_click=lambda i=display['id']: _open_details(i))


# ------------------------------ Navigation ------------------------------
def _open_details(pdf_id: int):
    # If your 'details' page expects data in session, set it here
    go("details", current_pdf_id=pdf_id)
    st.session_state['_force_rerun'] = True
