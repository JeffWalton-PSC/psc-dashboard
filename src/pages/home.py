"""Home page"""
import streamlit as st
import src.pages.components


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Home ..."):
        src.pages.components.page_header()
        st.write(
            """
            ## Home
            Select the data you would like to see from the navigation sidebar to the left.
"""
        )
