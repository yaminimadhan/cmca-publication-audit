from __future__ import annotations
import streamlit as st

import os
if os.getenv("DEV_BYPASS") == "1":
    st.session_state["page"] = "dashboard"

import os
if os.getenv("DEV_BYPASS") == "1":
    st.session_state["page"] = "dashboard"

# ===============================================================
# 💡 LOCAL DEV MODE SWITCH (for Nat's safe GUI editing)
# This block runs only if you set DEV_MODE=1 in your terminal.
# It will skip login and use mock data, but never affects others.
# ===============================================================
IS_DEV_MODE = os.getenv("DEV_MODE", "0") == "1"

if IS_DEV_MODE:
    st.warning("🧩 Running in LOCAL DEV MODE – backend calls disabled.")
    st.session_state["page"] = "dashboard"
    st.session_state["mock_user"] = {"name": "Nat"}
    st.session_state["mock_data"] = {"files": ["sample1.pdf", "sample2.pdf"]}

from core.state import init_session

st.set_page_config(page_title="CMCA PDF Dashboard", layout="wide", initial_sidebar_state="collapsed")
init_session()

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
