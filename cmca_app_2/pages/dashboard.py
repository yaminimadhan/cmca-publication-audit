# pages/dashboard.py
from __future__ import annotations
from collections import Counter
from datetime import datetime

import streamlit as st
import plotly.express as px

from core.state import require_auth, go
from core.api import get as api_get, post_json as api_post, post_multipart as api_post_multipart


# ------------------------------ API wrappers ------------------------------
def _auth_token() -> str | None:
    return st.session_state.get("token")

def _api_projects() -> list[dict]:
    """GET /projects; normalize to [{'id','name'}]."""
    data = api_get("/projects", token=_auth_token()) or []
    out: list[dict] = []
    for p in data:
        out.append({
            "id": p.get("id") or p.get("project_id"),
            "name": (p.get("project_name") or p.get("name") or "").strip(),
        })
    return out

def _projects_map() -> dict[int, str]:
    """project_id -> project_name"""
    m: dict[int, str] = {}
    for p in _api_projects():
        pid = p.get("id")
        if pid is not None:
            m[int(pid)] = p["name"]
    return m

def _api_create_project(name: str) -> dict:
    """POST /projects  { 'project_name': '<name>' }"""
    payload = {"project_name": name.strip()}
    return api_post("/projects", payload, token=_auth_token())

def _api_list_pdfs(project_id: int | None = None, limit: int = 50, offset: int = 0) -> list[dict]:
    """GET /pdfs  (optional ?project_id=&limit=&offset=)"""
    params = {"limit": limit, "offset": offset}
    if project_id is not None:
        params["project_id"] = project_id
    return api_get("/pdfs", token=_auth_token(), params=params) or []

def _api_get_pdf(pdf_id: int) -> dict:
    """GET /pdfs/{pdf_id}"""
    return api_get(f"/pdfs/{pdf_id}", token=_auth_token()) or {}

def _api_upload_pdf(file, project_id: int | None = None, overrides: dict | None = None) -> dict:
    """
    POST /pdfs/upload (multipart/form-data)
    files = {"file": (filename, bytes, "application/pdf")}
    data  = {project_id, ...}
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


# ------------------------------ Utilities ------------------------------
def _fmt_date(iso_str: str | None) -> str:
    """
    Convert ISO-like string to dd-mm-yyyy. Returns '-' on failure.
    """
    if not iso_str:
        return "-"
    s = str(iso_str)
    # try common formats
    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%S.%f%z",
                "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d", "%Y-%m-%d %H:%M:%S"):
        try:
            # handle trailing Z
            if s.endswith("Z"):
                s2 = s.replace("Z", "+00:00")
            else:
                s2 = s
            dt = datetime.fromisoformat(s2) if "T" in s2 or "+" in s2 else datetime.strptime(s2, fmt)
            return dt.strftime("%d-%m-%Y")
        except Exception:
            continue
    # last attempt: best-effort parse of first 10 chars (YYYY-MM-DD)
    try:
        return datetime.strptime(s[:10], "%Y-%m-%d").strftime("%d-%m-%Y")
    except Exception:
        return "-"


# ------------------------------ Page ------------------------------
def render_dashboard():
    if not require_auth():
        st.stop()

    # Navbar (optional)
    try:
        from modules.navbar import navbar
        navbar()
    except Exception:
        pass

    # ---- Top charts: Pie (CMCA) + Bar (Top instruments by #PDFs) ----
    try:
        all_pdfs = _api_list_pdfs(limit=200, offset=0)
    except Exception as e:
        st.warning(f"Could not load PDFs for stats: {e}")
        all_pdfs = []

    yes = sum(1 for x in all_pdfs if (x.get("cmca_result") or "").lower() == "yes")
    no  = sum(1 for x in all_pdfs if (x.get("cmca_result") or "").lower() == "no")

    counts = Counter()
    for row in all_pdfs:
        instruments = row.get("instruments_json") or []
        for inst in set(str(i) for i in instruments):
            counts[inst] += 1
    bar_rows = [{"instrument": k, "pdfs": v} for k, v in counts.most_common(5)]

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
            f = st.file_uploader("Choose PDF", type=["pdf"], accept_multiple_files=False, key="uploader_pdf")

            # Projects dropdown
            projects_data = _api_projects()
            project_names = [p["name"] for p in projects_data] or ["Documentation"]
            project_sel = st.selectbox("Project", project_names, index=0, key="upload_project")

            if st.button("Upload", type="primary", key="upload_btn", disabled=(f is None)):
                try:
                    # Map selected name -> id
                    project_id = None
                    for p in projects_data:
                        if p["name"] == project_sel:
                            project_id = p.get("id")
                            break

                    resp = _api_upload_pdf(f, project_id=project_id, overrides={})
                    st.success(f"Uploaded: {resp.get('title') or f.name} (pdf_id {resp.get('pdf_id')})")
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
    proj_map = _projects_map()
    project_names_for_filter = ["All"] + list({name for name in proj_map.values()})

    def _unique_instruments(items: list[dict]) -> list[str]:
        ins = set()
        for it in items:
            for k in (it.get("instruments_json") or []):
                ins.add(k)
        return sorted(ins)

    f1, f2, f3 = st.columns([1, 2, 1])
    with f1:
        project_filter = st.selectbox("Project", project_names_for_filter, key="filter_project")
    with f2:
        instruments_all = _unique_instruments(all_pdfs)
        ins_sel = st.multiselect("Instrument Type", instruments_all, key="filter_instruments")
    with f3:
        sort_by = st.selectbox("Sort By", ["Date (Newest First)", "Date (Oldest First)", "Title A→Z"], key="filter_sort")

    # Server-side project filter; others client-side
    try:
        project_filter_id = None
        if project_filter != "All":
            # reverse map name -> id (first match)
            for pid, name in proj_map.items():
                if name == project_filter:
                    project_filter_id = pid
                    break
        raw_items = _api_list_pdfs(project_id=project_filter_id, limit=200, offset=0)
    except Exception as e:
        st.error(f"Failed to load PDFs: {e}")
        raw_items = []

    filtered = []
    for it in raw_items:
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

    # -------------------- List cards (neat layout) --------------------
    for it in filtered:
        pdf_id = it.get("pdf_id")
        title = it.get("title") or "(untitled)"
        instruments = it.get("instruments_json") or []
        project_name = proj_map.get(it.get("project_id"), "-")
        upload_date = _fmt_date(it.get("upload_date"))
        cmca = str(it.get("cmca_result", "-")).strip()

        with st.container(border=True):
            top_l, top_r = st.columns([5, 1])
            with top_l:
                # Title + small CMCA badge
                badge = "✅ CMCA Yes" if cmca.lower() == "yes" else "❌ CMCA No" if cmca.lower() == "no" else "—"
                st.markdown(f"**{title}**  ·  {badge}")
                st.caption(
                    f"Project: {project_name}  ·  "
                    f"Instruments: {', '.join(instruments) or '-'}  ·  "
                    f"Uploaded: {upload_date}"
                )
            with top_r:
                st.button("Open", key=f"open_{pdf_id}", use_container_width=True,
                          on_click=lambda i=pdf_id: _open_details(i))

# ------------------------------ Navigation ------------------------------
def _open_details(pdf_id: int):
    go("details", current_pdf_id=pdf_id)
    st.session_state['_force_rerun'] = True
