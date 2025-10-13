from __future__ import annotations
import streamlit as st
from core.state import go


def navbar():
    left, right = st.columns([5,1])
    with left:
        st.markdown("### PDF Dashboard")
    with right:
        if st.button("Logout", use_container_width=True):
            for k in ("auth","user","page","current_pdf_id"):
                if k in st.session_state:
                    del st.session_state[k]
            go("login")
            st.session_state['_force_rerun'] = True