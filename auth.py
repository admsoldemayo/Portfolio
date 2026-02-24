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
        from style import inject_css, login_header

        inject_css()

        # Centered login layout
        _spacer_l, col_center, _spacer_r = st.columns([1.2, 1, 1.2])

        with col_center:
            login_header()

            password = st.text_input(
                "Password",
                type="password",
                placeholder="Ingresa tu password",
                label_visibility="collapsed",
            )

            if st.button("Entrar", type="primary", use_container_width=True):
                if password == os.environ.get("DASHBOARD_PASSWORD", ""):
                    st.session_state.authenticated = True
                    st.rerun()
                else:
                    st.error("Password incorrecta")

        st.stop()
