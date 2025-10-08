# pages/details.py
from __future__ import annotations
import os
import json
import requests
import streamlit as st

# --- DEV MODE helpers (safe: only active when DEV_MODE=1) ---
import os
DEV_MODE = os.getenv("DEV_MODE") == "1"

def _mock_pdf(pdf_id: int = 101) -> dict:
    return {
        "pdf_id": pdf_id,
        "title": "sample1.pdf",
        "authors": "A. Smith; B. Jones",
        "affiliation": "UWA, CMCA",
        "doi": "10.1234/abcd.efgh",
        "instruments_json": ["SEM", "EDS"],
        "project_id": 1,
        "uploaded_by": 42,
        "upload_date": "2025-10-01",
        "publish_date": "2024-07-10",
        "cmca_result": "Yes",
        "cosine_similarity": 0.82,
    }


from core.state import require_auth, go
from core.api import get as api_get, delete as api_delete  # reuse existing helpers


# ------------------------------ API helpers ------------------------------
def _auth_token() -> str | None:
    return st.session_state.get("token")

def _api_get_pdf(pdf_id: int) -> dict:
    return api_get(f"/pdfs/{pdf_id}", token=_auth_token()) or {}

def _api_projects() -> dict[int, str]:
    """Return {project_id: project_name} for quick lookup."""
    try:
        data = api_get("/projects", token=_auth_token()) or []
        out: dict[int, str] = {}
        for p in data:
            pid = p.get("id") or p.get("project_id")
            pname = (p.get("project_name") or p.get("name") or "").strip()
            if pid is not None:
                out[int(pid)] = pname
        return out
    except Exception:
        return {}

def _api_get_user(user_id: int) -> dict:
    return api_get(f"/users/{user_id}", token=_auth_token()) or {}

def _api_patch_pdf(pdf_id: int, body: dict) -> dict:
    """PATCH /pdfs/{id} (we'll call requests directly since core.api has no patch helper)."""
    base = st.secrets.get("API_BASE_URL") or os.getenv("API_BASE_URL") or "http://localhost:8000"
    headers = {
        "Authorization": f"Bearer {_auth_token()}",
        "Accept": "application/json",
        "Content-Type": "application/json",
    }
    r = requests.patch(f"{base}/pdfs/{pdf_id}", headers=headers, data=json.dumps(body), timeout=60)
    r.raise_for_status()
    return r.json()

def _api_download_pdf_bytes(pdf_id: int) -> bytes:
    base = st.secrets.get("API_BASE_URL") or os.getenv("API_BASE_URL") or "http://localhost:8000"
    headers = {"Authorization": f"Bearer {_auth_token()}"}
    r = requests.get(f"{base}/pdfs/{pdf_id}/file", headers=headers, timeout=120)
    r.raise_for_status()
    return r.content


# ------------------------------ Page ------------------------------
def render_details():
    if not (DEV_MODE or require_auth()):
        st.stop()

    # optional navbar
    try:
        from modules.navbar import navbar
        navbar()
    except Exception:
        pass

        # --- DEV MODE short-circuit: render mock details, no backend calls ---
    if DEV_MODE:
        # pick a current id (from dashboard mock “Open”, or default)
        pdf_id = st.session_state.get("current_pdf_id") or 101
        item = _mock_pdf(int(pdf_id))

        # basic navigation
        if st.button("⬅️ Back to Dashboard", type="secondary"):
            go("dashboard")
            st.session_state['_force_rerun'] = True
            st.rerun()

        st.subheader("PDF Details (Mock)")
        uploader_name = "mock_user"
        proj_name = f"Project {item.get('project_id', '-')}"
        title = item.get("title") or "Untitled"
        authors_text = item.get("authors") or "-"
        affiliation = item.get("affiliation") or "-"
        doi = item.get("doi") or "-"
        instruments = item.get("instruments_json") or []
        upload_date = item.get("upload_date") or "-"
        publish_date = item.get("publish_date") or "-"
        cmca_result_current = item.get("cmca_result") or "-"
        cosine_val = float(item.get("cosine_similarity") or 0.0)
        cosine_val = max(0.0, min(cosine_val, 1.0))

        cols = st.columns(2)
        with cols[0]:
            st.markdown(f"**{title}**")
            st.caption("Authors");       st.write(authors_text)
            st.caption("Affiliation");   st.write(affiliation)
            st.caption("DOI");           st.code(doi)
            st.caption("Instruments");   st.write(", ".join(instruments) if instruments else "-")
            st.caption("Project");       st.write(proj_name)

        with cols[1]:
            st.caption("CMCA Use")
            st.radio(
                "Set CMCA Result",
                options=["Yes", "No"],
                index=0 if str(cmca_result_current).lower() == "yes" else 1,
                horizontal=True,
                key="cmca_edit_mock",
                disabled=True,  # mock only
            )
            st.caption("Cosine Similarity"); st.progress(cosine_val)
            st.caption("Uploaded By");       st.write(uploader_name)
            st.caption("Upload Date");       st.write(upload_date)
            st.caption("Publish Date");      st.write(publish_date)

        st.divider()
        st.info("📎 Download/Delete are disabled in DEV MODE (no backend).")

        return  # IMPORTANT: don’t run real backend path in DEV


    pdf_id = st.session_state.get("current_pdf_id")
    if not pdf_id:
        st.info("No PDF selected.")
        if st.button("Back to Dashboard"):
            go("dashboard"); st.session_state['_force_rerun'] = True
        return

    # Fetch details from backend
    try:
        item = _api_get_pdf(int(pdf_id))
    except Exception as e:
        st.error(f"Failed to load PDF #{pdf_id}: {e}")
        if st.button("Back to Dashboard"):
            go("dashboard"); st.session_state['_force_rerun'] = True
        return

    # Resolve uploader username from user_id
    uploader_name = "-"
    uploader_id = item.get("uploaded_by")
    if uploader_id is not None:
        try:
            u = _api_get_user(int(uploader_id))
            uploader_name = u.get("username") or uploader_name
        except Exception:
            pass

    # Lookup projects map to show project name
    proj_map = _api_projects()

    # Normalize fields from backend
    title = item.get("title") or "Untitled"
    authors_text = item.get("authors") or "-"           # TEXT in DB
    affiliation = item.get("affiliation") or "-"
    doi = item.get("doi") or "-"
    instruments = item.get("instruments_json") or []    # list[str]
    project_name = proj_map.get(item.get("project_id"), str(item.get("project_id") or "-"))
    uploaded_by = uploader_name
    upload_date = item.get("upload_date") or "-"
    publish_date = item.get("publish_date") or "-"
    cmca_result_current = (item.get("cmca_result") or "-")
    cosine = item.get("cosine_similarity")
    try:
        cosine_val = max(0.0, min(float(cosine or 0.0), 1.0))
    except Exception:
        cosine_val = 0.0

    # Back button via your custom router
    if st.button("⬅️ Back to Dashboard", type="secondary"):
        go("dashboard")
        st.session_state['_force_rerun'] = True
        st.rerun()

    st.subheader("PDF Details")

    cols = st.columns(2)
    with cols[0]:
        st.markdown(f"**{title}**")
        st.caption("Authors")
        st.write(authors_text)
        st.caption("Affiliation")
        st.write(affiliation)
        st.caption("DOI")
        st.code(doi)
        st.caption("Instruments")
        st.write(", ".join(instruments) if instruments else "-")
        st.caption("Project")
        st.write(project_name)

    with cols[1]:
        st.caption("CMCA Use")
        # Editable CMCA result
        cmca_val = st.radio(
            "Set CMCA Result",
            options=["Yes", "No"],
            index=0 if str(cmca_result_current).lower() == "yes" else 1,
            horizontal=True,
            key="cmca_edit",
        )
        if st.button("Save CMCA Result"):
            try:
                updated = _api_patch_pdf(int(pdf_id), {"cmca_result": cmca_val})
                st.success(f"Saved: CMCA Result = {updated.get('cmca_result', cmca_val)}")
                # refresh page state
                st.session_state['_force_rerun'] = True
                st.rerun()
            except Exception as e:
                st.error(f"Update failed: {e}")

        st.caption("Cosine Similarity")
        st.progress(cosine_val)
        st.caption("Uploaded By")
        st.write(uploaded_by)
        st.caption("Upload Date")
        st.write(upload_date)
        st.caption("Publish Date")
        st.write(publish_date)

    st.divider()

    # ---------- Download + Delete ----------
    # Download directly
    try:
        pdf_bytes = _api_download_pdf_bytes(int(pdf_id))
        st.download_button(
            "Download PDF",
            data=pdf_bytes,
            file_name=f"{(title or 'document')}.pdf",
            mime="application/pdf",
            use_container_width=True,
        )
    except Exception as e:
        st.error(f"Could not fetch PDF for download: {e}")

    # Delete with a simple confirm pattern
    del_col1, del_col2 = st.columns([3, 1])
    with del_col1:
        confirm = st.checkbox("Confirm delete this PDF", value=False, key="confirm_delete")
    with del_col2:
        if st.button("Delete PDF", type="secondary", use_container_width=True, disabled=not confirm):
            try:
                api_delete(f"/pdfs/{int(pdf_id)}", token=_auth_token())
                st.success("PDF deleted")
                go("dashboard")
                st.session_state['_force_rerun'] = True
                st.rerun()
            except Exception as e:
                st.error(f"Delete failed: {e}")
