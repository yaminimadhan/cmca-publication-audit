from __future__ import annotations
import streamlit as st
from core.state import go

# 简单内置用户
USERS = {
    "admin@example.com": {"password": "admin", "role": "admin", "name": "Admin"},
    "user@example.com": {"password": "user", "role": "user", "name": "Regular"},
}


def render_login():
    st.markdown("""
    <div style='display:flex; justify-content:center; margin-top:40px;'>
      <div style='width:420px; padding:28px; border:1px solid #eee; border-radius:14px; background:#fff;'>
        <h3 style='margin:0 0 6px;'>Welcome Back</h3>
        <p style='color:#6b7280;margin:0 0 18px;'>Sign in to your account to continue</p>
    """, unsafe_allow_html=True)

    with st.form("login_form"):
        email = st.text_input("Email", placeholder="Enter your email")
        pwd = st.text_input("Password", type="password", placeholder="Enter your password")
        col1, col2 = st.columns([1,1])
        with col1:
            st.form_submit_button("Sign In", use_container_width=True, on_click=lambda: _do_login(email, pwd))
        with col2:
            st.write(" ")
            st.caption("Forgot password?")

    st.markdown("</div></div>", unsafe_allow_html=True)


def _do_login(email: str, pwd: str):
    user = USERS.get(email)
    if user and user["password"] == pwd:
        st.session_state["auth"] = True
        st.session_state["user"] = {"email": email, "role": user["role"], "name": user["name"]}
        go("dashboard")
        st.session_state['_force_rerun'] = True
    else:
        st.warning("Invalid email or password")