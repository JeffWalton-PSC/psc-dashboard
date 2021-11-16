"""Main module for the streamlit app"""
import sys
import streamlit as st

import src.pages
import src.pages.home
import src.pages.academic_program_enrollment
import src.pages.about

PAGES = {
    "Home": src.pages.home,
    "Academic Program Enrollment": src.pages.academic_program_enrollment, 
    "About": src.pages.about,
}


def main():
    """Main function of the App"""
    st.sidebar.write(
        "[![Paul Smith's College](https://www.paulsmiths.edu/news/wp-content/themes/paulsmiths-divi-2019/images/logo.png)]"
        "(https://www.paulsmiths.edu)"
    )

    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(PAGES.keys()), index=0)
    
    page = PAGES[selection]
    
    with st.spinner(f"Loading {selection} ..."):
        src.pages.write_page(page)
    st.sidebar.markdown("---")
    st.sidebar.title("Info")
    st.sidebar.write(
        "Paul Smith's College data prepared by the Office of Institutional Research. "
    )
    st.sidebar.markdown("---")
    st.sidebar.title("Questions?")
    st.sidebar.write(
        """
        Please contact Jeff Walton ([jwalton@paulsmiths.edu](mailto:jwalton@paulsmiths.edu), x6441) for more information.
"""
    )


if __name__ == '__main__':
    if st._is_running_with_streamlit:
        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
