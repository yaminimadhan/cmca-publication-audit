from __future__ import annotations
import streamlit as st

SESSION_KEYS = {
    "auth": False,
    "user": None,
    "page": "login",  # login | dashboard | details
    "current_pdf_id": None,
}

def init_session():
    for k, default in SESSION_KEYS.items():
        if k not in st.session_state:
            st.session_state[k] = default

def require_auth():
    if not st.session_state.get("auth"):
        st.switch_page = None
        st.session_state["page"] = "login"
        return False
    return True

def go(page: str, **kwargs):
    st.session_state["page"] = page
    for k, v in kwargs.items():
        st.session_state[k] = v
