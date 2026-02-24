"""
Auth Gate - Password protection
================================
Simple password gate using DASHBOARD_PASSWORD env var.
"""

import streamlit as st
import os


def require_auth():
    """Block access unless correct password is entered."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False

    if not st.session_state.authenticated:
        st.title("Portfolio Dashboard")
        password = st.text_input("Password", type="password")
        if st.button("Entrar"):
            if password == os.environ.get("DASHBOARD_PASSWORD", ""):
                st.session_state.authenticated = True
                st.rerun()
            else:
                st.error("Password incorrecta")
        st.stop()
