from __future__ import annotations
import streamlit as st
from core.state import require_auth, go
from core import db


def render_details():
    if not require_auth():
        st.stop()

    from modules.navbar import navbar
    navbar()

    if not st.session_state.get("current_pdf_id"):
        st.info("No PDF selected.")
        if st.button("Back to Dashboard"):
            go("dashboard"); st.session_state['_force_rerun'] = True
        return

    item = db.get_pdf(st.session_state["current_pdf_id"]) or {}

    st.page_link("app.py", label="← Back to Dashboard", icon="⬅️")
    st.subheader("PDF Details")

    cols = st.columns(2)
    with cols[0]:
        st.markdown(f"**{item.get('title','Untitled')}**")
        st.caption("Authors")
        st.write(", ".join(item.get("authors", [])) or "-")
        st.caption("Affiliations")
        st.write(", ".join(item.get("affiliations", [])) or "-")
        st.caption("DOI")
        st.code(item.get("doi","-"))
        st.caption("Instruments")
        st.write(", ".join(item.get("instruments", [])) or "-")
        st.caption("Project")
        st.write(item.get("project","-"))
    with cols[1]:
        st.caption("Cosine Similarity")
        st.progress(min(float(item.get("cosine",0)),1.0))
        st.caption("Uploaded By")
        st.write(item.get("uploaded_by","-"))
        st.caption("File Size")
        st.write(item.get("size","-"))
        st.caption("Upload Date")
        st.write(item.get("upload_date","-"))
        st.caption("CMCA Use")
        current = item.get("cmca_use","No")
        toggled = st.toggle("Yes", value=(str(current).lower()=="yes"))
        if st.button("Save"):
            db.update_pdf(item["id"], {"cmca_use": "Yes" if toggled else "No"})
            st.success("Saved")

    st.divider()
    st.button("View PDF", type="primary")
    st.button("Delete PDF", type="secondary")