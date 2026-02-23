"""
Auth Gate - Google OAuth via Streamlit st.login()
==================================================
Restricts access to allowed email addresses.
"""

import streamlit as st

ALLOWED_EMAILS = ["flopez@soldemayosa.com"]


def require_auth():
    """Block access unless user is logged in with an allowed email."""
    if not st.user.is_logged_in:
        st.title("Portfolio Dashboard")
        st.write("Acceso restringido.")
        if st.button("Iniciar sesion con Google"):
            st.login()
        st.stop()

    if st.user.email not in ALLOWED_EMAILS:
        st.error(f"Acceso denegado para {st.user.email}")
        if st.button("Cerrar sesion"):
            st.logout()
        st.stop()
