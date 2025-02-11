"""Main module for the streamlit app"""
import sys
import streamlit as st
import streamlit.web.cli as stcli
from streamlit import runtime

import src.pages
import src.pages.home
import src.pages.definitions
import src.pages.academic_department_credits
import src.pages.academic_department_enrollment
import src.pages.academic_program_enrollment
import src.pages.academic_program_enrollment_gender
import src.pages.academic_program_enrollment_race_ethnicity
import src.pages.academic_program_graduates
import src.pages.admissions_current_deposits
import src.pages.admissions_historic_data_by_stage
import src.pages.college_enrollment_total
import src.pages.college_enrollment_historic
import src.pages.college_enrollment_attrition
# import src.pages.college_enrollment_retention
import src.pages.college_enrollment_attend_status
import src.pages.college_enrollment_class_level
import src.pages.college_enrollment_degree
import src.pages.college_enrollment_gender
import src.pages.college_enrollment_race_ethnicity
import src.pages.faculty_teaching
import src.pages.program_review_course_enrollment
import src.pages.registrar_class_times
import src.pages.registrar_course_scheduling
import src.pages.registrar_grade_distribution
import src.pages.registrar_section_sizes
import src.pages.about

PAGES = {
    "Home": src.pages.home,
    "Definitions": src.pages.definitions, 
    "Academic Department - Credits": src.pages.academic_department_credits, 
    "Academic Department - Enrollment": src.pages.academic_department_enrollment, 
    "Academic Program - Enrollment": src.pages.academic_program_enrollment, 
    "Academic Program - Gender": src.pages.academic_program_enrollment_gender,
    "Academic Program - Race/Ethnicity": src.pages.academic_program_enrollment_race_ethnicity,
    "Academic Program - Graduates": src.pages.academic_program_graduates,
    "Admissions - Current Deposits": src.pages.admissions_current_deposits,
    "Admissions - Historic Data By Stage": src.pages.admissions_historic_data_by_stage,
    "College Enrollment - Total": src.pages.college_enrollment_total,
    "College Enrollment - Historic": src.pages.college_enrollment_historic,
    "College Enrollment - Attrition": src.pages.college_enrollment_attrition,
    # "College Enrollment - Retention": src.pages.college_enrollment_retention,
    "College Enrollment - Attend Status": src.pages.college_enrollment_attend_status,
    "College Enrollment - Class Level": src.pages.college_enrollment_class_level,
    "College Enrollment - Degree": src.pages.college_enrollment_degree,
    "College Enrollment - Gender": src.pages.college_enrollment_gender,
    "College Enrollment - Race/Ethnicity": src.pages.college_enrollment_race_ethnicity,
    "Faculty - Teaching": src.pages.faculty_teaching, 
    "Program Review - Course Enrollment": src.pages.program_review_course_enrollment,
    "Registrar - Class Times": src.pages.registrar_class_times,
    "Registrar - Course Scheduling": src.pages.registrar_course_scheduling,
    "Registrar - Grade Distribution": src.pages.registrar_grade_distribution,
    "Registrar - Section Sizes": src.pages.registrar_section_sizes,
    "About": src.pages.about,
}


def main():
    """Main function of the App"""
    st.set_page_config(
        page_title="PSC IR Dashboard",
        page_icon="static/favicon.png",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    st.logo(
        "static/PaulSmithsCollege-logo_ParentMark_FullColor.png",
        size="large",
        link="https://www.paulsmiths.edu"
    )

    st.sidebar.title("IR Dashboard")
    st.sidebar.markdown("---")
    st.sidebar.title("Navigation")
    selection = st.sidebar.radio("Go to", list(PAGES.keys()), index=0)
    
    page = PAGES[selection]
    with st.spinner(f"Selecting {selection} ..."):
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
    if runtime.exists():
        main()
    else:
        sys.argv = ["streamlit", "run", sys.argv[0]]
        sys.exit(stcli.main())
