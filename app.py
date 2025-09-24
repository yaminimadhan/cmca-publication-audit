import streamlit as st
from pathlib import Path

# ---- load CSS ----
def local_css(path: str):
    with open(path, "r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("static/css/tokens.css")

# ---------- Dashboard ----------
st.subheader("CMCA Dashboard")

# ---------- toolbar with 2 buttons (right aligned, with gap) ----------
left, b1, gap, b2 = st.columns([10, 3, 1, 3])  # gap=1 gives clear space

with b1:
    if st.button("📤 Upload New PDF", key="btn_upload"):
        st.session_state.show_upload = True
        st.session_state.show_create = False

with b2:
    if st.button("➕ Create New Project", key="btn_create"):
        st.session_state.show_create = True
        st.session_state.show_upload = False

st.write("")  # spacer

# ---------- Upload Form ----------
def upload_form():
    st.subheader("Upload New PDF")
    with st.form("upload_pdf"):
        project = st.selectbox("Select Project", ["Demo Project", "Microscopy 2025"])
        file = st.file_uploader("Choose a PDF", type=["pdf"])
        title = st.text_input("Publication Title (optional)")
        notes = st.text_area("Notes (optional)")

        cA, cB = st.columns([1,1])
        submit = cA.form_submit_button("Upload")
        cancel = cB.form_submit_button("Cancel")

    if submit:
        if not file:
            st.error("Please choose a PDF file")
        else:
            st.success(f"Uploaded **{file.name}** to **{project}**")
            st.session_state.show_upload = False
            st.rerun()
    if cancel:
        st.session_state.show_upload = False
        st.rerun()

# ---------- Create Project Form ----------
def create_project_form():
    st.subheader("Create New Project")
    with st.form("create_project"):
        name = st.text_input("Project Name")
        cA, cB = st.columns([1,1])
        create = cA.form_submit_button("Create")
        cancel = cB.form_submit_button("Cancel")

    if create:
        if not name.strip():
            st.error("Project name is required")
        else:
            st.success(f"Created project **{name.strip()}**")
            st.session_state.show_create = False
            st.rerun()
    if cancel:
        st.session_state.show_create = False
        st.rerun()

# ---------- conditional rendering ----------
if st.session_state.get("show_upload"):
    upload_form()
if st.session_state.get("show_create"):
    create_project_form()
