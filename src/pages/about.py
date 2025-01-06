"""About page"""
import streamlit as st
import src.pages.components


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading About ..."):
        src.pages.components.page_header()
        st.markdown(
            """
            ## About
            Please contact Jeff Walton (x6441) for more information.
            """
        )
