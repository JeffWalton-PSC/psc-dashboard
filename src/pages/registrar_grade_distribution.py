import pandas as pd
import streamlit as st
import altair as alt
import datetime as dt
import src.pages.components

# PowerCampus utilities
import powercampus as pc

@st.cache
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

start_year = pc.START_ACADEMIC_YEAR

current_yt_df = pc.current_yearterm()
current_term = current_yt_df['term'].iloc[0]
current_year = current_yt_df['year'].iloc[0]
current_yt = current_yt_df['yearterm'].iloc[0]
current_yt_sort = current_yt_df['yearterm_sort'].iloc[0]


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Registrar - Grade Distribution ..."):
        src.pages.components.logo()
        st.write(
            """
            ## Registrar - Grade Distribution
"""
        )

        today = dt.datetime.today()
        today_str = today.strftime("%Y%m%d_%H%M")
        # st.write(f"{today.strftime('%Y-%m-%d %H:%M')}")

        calendar = pc.select("ACADEMICCALENDAR",
            fields=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 
                'START_DATE', 'END_DATE', 'FINAL_END_DATE' ], 
            where=f"ACADEMIC_YEAR>='{start_year}' AND ACADEMIC_TERM IN ('FALL', 'SPRING', 'SUMMER')", 
            distinct=True
            )
        calendar = pc.add_col_yearterm(calendar)
        calendar = pc.add_col_yearterm_sort(calendar)
        term_df = ( calendar.drop_duplicates(['yearterm_sort', 'yearterm'])
                        .sort_values(['yearterm_sort'], ascending=True)
                        .loc[:,['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'yearterm_sort', 'yearterm']]
        )
        term_df = term_df.set_index('yearterm')

        year_list = term_df['ACADEMIC_YEAR'].unique().tolist()
        year_start, year_end = st.select_slider(
            "Select range of years:",
            options=year_list,
            value=('2012', current_year)
        )

        term = st.selectbox(label="Select term:", options=['Fall', 'Spring'])

        undergrad_only = st.checkbox("Undergrad sections only", value=True )
        # exclude_online = st.checkbox("Exclude online sections", value=True )

        section_types = ['COMB', 'HYBD', 'LEC', 'PRAC', 'LAB', 'SI']
        include_section_types = st.multiselect("Include section types:", options=section_types, default=['COMB', 'HYBD', 'LEC', 'PRAC'])

        if year_start and year_end and term and include_section_types:

            academic = pc.select("ACADEMIC",
                fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION',
                    'PROGRAM', 'DEGREE', 'CURRICULUM', 'COLLEGE', 'DEPARTMENT', 'CLASS_LEVEL', 'POPULATION',
                    'FULL_PART', 'ACADEMIC_STANDING', 'ENROLL_SEPARATION', 'SEPARATION_DATE', 'CREDITS',  
                    'COLLEGE_ATTEND', 'STATUS', 'PRIMARY_FLAG',
                    ],
                where=f"ACADEMIC_YEAR>='{int(year_start)}' and ACADEMIC_YEAR<='{int(year_end)}' and ACADEMIC_TERM='{term}' " +
                    "and ACADEMIC_SESSION='' and CREDITS>0 and CURRICULUM<>'ADVST' ", 
            )
            st.write(f"{academic.shape=}")

            if undergrad_only:
                academic = academic.loc[(sections['PROGRAM'] != 'G')]
            # if exclude_online:
            #     sections = sections.loc[(~sections['SECTION'].str.contains('ON'))]
            st.write(f"{academic.shape=}")

            transcriptdetail = pc.select("TRANSCRIPTDETAIL",
                fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION',
                    'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION', 'EVENT_TYPE', 'EVENT_MED_NAME', 'EVENT_LONG_NAME',
                    'CREDIT', 'MID_GRADE', 'FINAL_GRADE', 'ADD_DROP_WAIT',
                    ],
                where=f"ACADEMIC_YEAR>='{int(year_start)}' and ACADEMIC_YEAR<='{int(year_end)}' and ACADEMIC_TERM='{term}' " +
                    "and ACADEMIC_SESSION='' and CREDITS>0 and CURRICULUM<>'ADVST' ", 
            )
            st.write(f"{transcriptdetail.shape=}")

            atd = academic.merge(transcriptdetail,
                how='left',
                on=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', ]
                )
            st.write(f"{atd.shape=}")
            atd = pc.add_col_yearterm(atd)
            atd = pc.add_col_yearterm_sort(atd)
            atd['course_section_id'] = (
                atd["EVENT_ID"].str.rstrip().str.upper() + "." + 
                atd["EVENT_SUB_TYPE"].str.upper() + "."  + 
                atd["ACADEMIC_YEAR"] + "."  + 
                atd["ACADEMIC_TERM"].str.title()  + "."  + 
                atd["SECTION"].str.upper()
                )
            st.write(f"{atd.shape=}")



            st.write(f"#### Grade Distribution ({term} {year_start}-{year_end})")

            # st.dataframe(agg_ss)
            # st.download_button(
            #     label="Download data as CSV",
            #     data=convert_df(agg_ss),
            #     file_name=f"{term}_{year_start}-{year_end}_section_sizes.csv",
            #     mime='text/csv',
            # )
