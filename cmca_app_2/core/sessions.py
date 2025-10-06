# core/session.py
import streamlit as st
from .api import post_json

def login(username: str, password: str):
    data = post_json("/auth/login", {"username": username, "password": password})
    st.session_state["token"] = data.get("access_token")
    st.session_state["user"]  = data.get("user")
    return data

def require_auth():
    if "token" not in st.session_state:
        st.warning("Please log in to continue.")
        st.stop()
