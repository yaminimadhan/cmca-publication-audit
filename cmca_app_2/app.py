from __future__ import annotations
import streamlit as st
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
