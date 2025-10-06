# core/modules/login.py
from __future__ import annotations
import streamlit as st
from core.state import go
from core.api import post_json

CARD_MAX_W = 480  # adjust to 440–560 if you want


def render_login():
    _inject_css()
    mode = st.session_state.get("auth_mode", "signin")

    # One centered card with heading + form inside
    st.markdown(f"""
    <div class="auth-wrap">
      <div class="auth-card" style="max-width:{CARD_MAX_W}px;">
        <div class="auth-head">
          <div class="auth-title">Welcome</div>
          <div class="auth-sub">Sign in or create a new account</div>
        </div>
    """, unsafe_allow_html=True)

    if mode == "signin":
        _render_signin()
    else:
        _render_signup()

    st.markdown("</div></div>", unsafe_allow_html=True)  # close .auth-card & .auth-wrap


# ---------------- Views ----------------
def _render_signin():
    with st.form("login_form", clear_on_submit=False):
        username = st.text_input("Username", placeholder="Enter your username")
        pwd = st.text_input("Password", type="password", placeholder="Enter your password")
        sign_in = st.form_submit_button("Sign In", use_container_width=True, type="primary")

    if sign_in:
        _do_login(username, pwd)

    st.button(
        "Register",
        key="go_signup",
        use_container_width=True,
        on_click=lambda: st.session_state.update({"auth_mode": "signup"})
    )


def _render_signup():
    st.markdown("<div class='subhead'>Create Account</div>", unsafe_allow_html=True)
    with st.form("signup_form", clear_on_submit=False):
        su_username = st.text_input("Choose a username", key="su_user")
        su_pwd = st.text_input("Choose a password", type="password", key="su_pwd")
        su_pwd2 = st.text_input("Confirm password", type="password", key="su_pwd2")
        create = st.form_submit_button("Sign Up", use_container_width=True, type="primary")

    if create:
        if not su_username or not su_pwd:
            st.warning("Please fill username and password.")
        elif su_pwd != su_pwd2:
            st.warning("Passwords do not match.")
        else:
            _do_register_and_login(su_username, su_pwd)

    st.button(
        "Back to Sign In",
        key="back_login",
        use_container_width=True,
        on_click=lambda: st.session_state.update({"auth_mode": "signin"})
    )


# ---------------- Actions ----------------
def _do_login(username: str, pwd: str):
    if not username or not pwd:
        st.warning("Please enter both username and password.")
        return
    try:
        with st.spinner("Signing in..."):
            data = post_json("/auth/login", {"username": username, "password": pwd})
    except Exception as e:
        msg = getattr(getattr(e, "response", None), "text", None) or "Login failed. Check credentials or server."
        st.error(msg)
        return

    token = data.get("access_token")
    if not token:
        st.warning("No access token returned by server.")
        return

    st.session_state["auth"] = True
    st.session_state["token"] = token
    st.session_state["user"] = {"username": username, "token_type": data.get("token_type", "bearer")}
    go("dashboard")
    st.rerun()


def _do_register_and_login(username: str, pwd: str):
    # user_type intentionally NOT shown in the UI; default is general_user
    payload = {"username": username, "password": pwd, "user_type": "general_user"}
    try:
        with st.spinner("Creating your account..."):
            post_json("/auth/register", payload)
    except Exception as e:
        msg = getattr(getattr(e, "response", None), "text", None) or "Registration failed."
        st.error(msg)
        return

    st.success("Account created! Signing you in…")
    _do_login(username, pwd)


# ---------------- Styles ----------------
def _inject_css():
    st.markdown("""
    <style>
      /* page centering */
      .auth-wrap{
        display:flex; align-items:flex-start; justify-content:center;
        padding: 7vh 16px;
      }
      /* single card */
      .auth-card{
        width: 100%;
        background: #fff;
        border: 1px solid #e5e7eb;
        border-radius: 16px;
        padding: 22px 22px 18px;
        box-shadow: 0 2px 8px rgba(0,0,0,.06);
      }
      /* heading */
      .auth-head{ text-align:center; margin-bottom: 12px; }
      .auth-title{ font-size: 26px; font-weight: 800; margin: 0 0 4px; }
      .auth-sub{ color:#6b7280; font-size: 14px; margin: 0; }

      .subhead{ font-weight: 600; margin: 10px 0 8px; }

      /* small gap between stacked buttons inside forms */
      .stForm .stButton > button[kind="primary"]{
        margin-bottom: 10px;
      }
    </style>
    """, unsafe_allow_html=True)
