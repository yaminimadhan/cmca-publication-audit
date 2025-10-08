from __future__ import annotations
import os
import streamlit as st

st.set_page_config(page_title="CMCA PDF Dashboard", layout="wide", initial_sidebar_state="collapsed")

from core.state import init_session
init_session()


# --- HARD RESET: remove any previous background CSS ---
st.markdown("""
<style>
/* kill old injected backgrounds */
[data-testid="stAppViewContainer"]{ 
  background: #ffffff !important; 
  background-image: none !important;
}
.stApp{
  background: #ffffff !important;
  background-image: none !important;
}
</style>
""", unsafe_allow_html=True)

# === Dev switches (local only; safe to keep in repo) ===
DEV_BYPASS = os.getenv("DEV_BYPASS") == "1"   # real backend, skip login
DEV_MODE   = os.getenv("DEV_MODE") == "1"     # no backend, mock data

if DEV_BYPASS or DEV_MODE:
    st.session_state["page"] = "dashboard"

if DEV_MODE:
    st.warning("🧩 Running in LOCAL DEV MODE – backend calls disabled.")
    st.session_state.setdefault("mock_user", {"name": "Nat"})
    st.session_state.setdefault("mock_data", {"files": ["sample1.pdf", "sample2.pdf"]})

from modules.login import render_login
from pages.dashboard import render_dashboard
from pages.details import render_details

page = st.session_state.get("page", "login")

if page == "login":
    render_login()
elif page == "dashboard":
    render_dashboard()
elif page == "details":
    render_details()
else:
    render_login()


# --- Hide Streamlit built-in sidebar/nav ---
hide_streamlit_sidebar_css = """
    <style>
    [data-testid="stSidebarNav"] {display: none !important;}
    section[data-testid="stSidebar"] {display: none !important;}
    </style>
"""
st.markdown(hide_streamlit_sidebar_css, unsafe_allow_html=True)


# --- unified rerun gate ---
if st.session_state.pop('_force_rerun', False):
    st.rerun()
