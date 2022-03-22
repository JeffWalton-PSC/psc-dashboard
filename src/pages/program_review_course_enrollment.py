import pandas as pd
import streamlit as st
import altair as alt
import datetime as dt
import io
import src.pages.components

# PowerCampus utilities
import powercampus as pc


@st.cache
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')


@st.cache
def convert_df_xlsx(df_list):
    xl_buffer = io.BytesIO()
    with pd.ExcelWriter(
        xl_buffer,
        date_format="YYYY-MM-DD",
        datetime_format="YYYY-MM-DD HH:MM:SS"
    ) as writer:
        for d in df_list:
            df = d[0]
            sheet = d[1]
            df.to_excel( writer,
                sheet_name=sheet,
                index=False
                )
    return xl_buffer.getvalue()


@st.cache
def course_df(start_year):

    academic = pc.select("ACADEMIC",
        fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION',
            'PROGRAM', 'DEGREE', 'CURRICULUM', 'COLLEGE', 'DEPARTMENT', 'CLASS_LEVEL', 'POPULATION',
            'FULL_PART', 'ACADEMIC_STANDING', 'ENROLL_SEPARATION', 'SEPARATION_DATE', 'CREDITS',  
            'COLLEGE_ATTEND', 'STATUS', 'PRIMARY_FLAG',
            ],
        where=f"ACADEMIC_YEAR>='{int(start_year)}' AND ACADEMIC_TERM IN ('FALL', 'SPRING', 'SUMMER') " +
            "and ACADEMIC_SESSION='' and CREDITS>0 and CURRICULUM<>'ADVST' and PRIMARY_FLAG='Y' ", 
    )
    academic = pc.add_col_yearterm(academic)
    academic = pc.add_col_yearterm_sort(academic)
 

    transcriptdetail = pc.select("TRANSCRIPTDETAIL",
        fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION',
            'ORG_CODE_ID', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION', 'EVENT_TYPE',
            'CREDIT', 'ADD_DROP_WAIT',
            ],
        where=f"ACADEMIC_YEAR>='{start_year}' AND ACADEMIC_TERM IN ('FALL', 'SPRING', 'SUMMER') " +
            "and ADD_DROP_WAIT='A' and ORG_CODE_ID='O000000001' ", 
    )
    transcriptdetail['section_id'] = (
        transcriptdetail["EVENT_ID"].str.rstrip().str.upper() + "." + 
        transcriptdetail["EVENT_SUB_TYPE"].str.upper() + "."  + 
        transcriptdetail["SECTION"].str.upper()
        )
    
    sectionper = pc.select("SECTIONPER", 
        fields=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',
            'PERSON_CODE_ID'],
        where=f"ACADEMIC_YEAR>='{start_year}' AND ACADEMIC_TERM IN ('FALL', 'SPRING', 'SUMMER') ",
        )
    people = pc.select('PEOPLE',
        fields=['PEOPLE_CODE_ID', 'FIRST_NAME', 'LAST_NAME', ],
        )
    people['instructor'] = people['LAST_NAME'] + ", " + people['FIRST_NAME']
    sectionper = sectionper.merge(people,
        how='left',
        left_on='PERSON_CODE_ID',
        right_on='PEOPLE_CODE_ID'
        )
    sectionper = sectionper.loc[:,['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION', 'instructor']]
    transcriptdetail = transcriptdetail.merge(sectionper,
        how='left',
        on=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',]
        )

    keep_cols = ['yearterm', 'yearterm_sort', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'section_id', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION', 'PEOPLE_CODE_ID', 'CURRICULUM', 'COLLEGE', 'instructor']
    atd = ( academic.merge(transcriptdetail,
        how='left',
        on=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', ]
        )
        .loc[:,keep_cols]
    )
    atd['EVENT_ID'] = atd['EVENT_ID'].str.strip().str.upper()
    atd = atd.drop_duplicates(['PEOPLE_CODE_ID', 'yearterm', 'section_id', ])

    return atd


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Program Review - Course Enrollment ..."):
        src.pages.components.logo()
        st.write(
            """
            ## Program Review - Course Enrollment
"""
        )

        start_year = pc.START_ACADEMIC_YEAR

        current_yt_df = pc.current_yearterm()
        current_term = current_yt_df['term'].iloc[0]
        current_year = current_yt_df['year'].iloc[0]
        current_yt = current_yt_df['yearterm'].iloc[0]
        current_yt_sort = current_yt_df['yearterm_sort'].iloc[0]

        df = course_df(start_year)

        today = dt.datetime.today()
        today_str = today.strftime("%Y%m%d_%H%M")

        calendar = pc.select("ACADEMICCALENDAR",
            fields=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 
                'START_DATE', 'END_DATE', 'FINAL_END_DATE' ], 
            where=f"ACADEMIC_YEAR>='{start_year}' AND ACADEMIC_TERM IN ('FALL', 'SPRING') ", 
            distinct=True
            )
        calendar = pc.add_col_yearterm(calendar)
        calendar = pc.add_col_yearterm_sort(calendar)
        term_df = ( calendar.drop_duplicates(['yearterm_sort', 'yearterm'])
                        .sort_values(['yearterm_sort'], ascending=True)
                        .loc[:,['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'yearterm_sort', 'yearterm']]
        )

        year_list = term_df['ACADEMIC_YEAR'].unique().tolist()
        year_start, year_end = st.select_slider(
            "Select range of years:",
            options=year_list,
            value=(str(int(current_year)-6), current_year)
        )

        if year_start and year_end:

            section_types = ['COMB', 'HYBD', 'LEC', 'ONLN', 'PRAC', 'LAB', 'SI']

            df1 = df.loc[
                (df['ACADEMIC_YEAR']>=year_start) 
                & (df['ACADEMIC_YEAR']<=year_end)
                & (df['EVENT_SUB_TYPE'].isin(section_types)),
                :
                ]
            df1 = df1.sort_values(['EVENT_ID', 'EVENT_SUB_TYPE', 'yearterm_sort' ])

            event_id_list = df1['EVENT_ID'].sort_values().unique().tolist()
            event_id = st.selectbox(
                label="Select course:",
                options=event_id_list,
            )

            include_section_types = st.multiselect("Include section types:", options=section_types, default=['COMB', 'HYBD', 'LEC', 'ONLN', 'PRAC'])
            df1 = df1.loc[(df1['EVENT_SUB_TYPE'].isin(include_section_types))]

            st.write(f"#### Course Enrollment - {event_id} ({year_start}-{year_end})")

            enrl_yt = ( df1.loc[
                (df1['EVENT_ID']==event_id),
                ['yearterm', 'yearterm_sort', 'EVENT_ID', 'EVENT_SUB_TYPE', 'section_id', 'instructor', 'CURRICULUM', 'PEOPLE_CODE_ID']
                ]
                .groupby(['EVENT_ID', 'yearterm', 'EVENT_SUB_TYPE']).agg(
                    {
                        'PEOPLE_CODE_ID': 'count',
                        'yearterm_sort': 'first',
                    }
                    )
                .reset_index()
                .sort_values(['EVENT_ID', 'yearterm_sort', 'EVENT_SUB_TYPE' ])
                .drop(['yearterm_sort'], axis=1)
                .rename(
                    columns={
                        'EVENT_ID': 'course',
                        'EVENT_SUB_TYPE': 'section_type',
                        'PEOPLE_CODE_ID': 'course_enrollment'
                    },
                )
            )
            
            st.dataframe(enrl_yt)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(enrl_yt),
                file_name=f"{event_id}_{year_start}-{year_end}_course_enrollment_by_yearterm.csv",
                mime='text/csv',
            )

            st.write(f"#### Course Enrollment by Instructor - {event_id} ({year_start}-{year_end})")

            enrl_inst_yt = ( df1.loc[
                (df1['EVENT_ID']==event_id),
                ['yearterm', 'yearterm_sort', 'EVENT_ID', 'EVENT_SUB_TYPE', 'section_id', 'instructor', 'CURRICULUM', 'PEOPLE_CODE_ID']
                ]
                .groupby(['EVENT_ID', 'yearterm', 'EVENT_SUB_TYPE', 'instructor']).agg(
                    {
                        'PEOPLE_CODE_ID': 'count',
                        # 'instructor': 'first',
                        'yearterm_sort': 'first',
                    }
                    )
                .reset_index()
                .sort_values(['EVENT_ID', 'yearterm_sort', 'EVENT_SUB_TYPE', 'instructor' ])
                .drop(['yearterm_sort'], axis=1)
                .rename(
                    columns={
                        'EVENT_ID': 'course',
                        'EVENT_SUB_TYPE': 'section_type',
                        'PEOPLE_CODE_ID': 'course_enrollment'
                    },
                )
            )
            
            st.dataframe(enrl_inst_yt)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(enrl_inst_yt),
                file_name=f"{event_id}_{year_start}-{year_end}_course_enrollment_by_instructor_by_yearterm.csv",
                mime='text/csv',
            )

            st.write(f"#### Course Enrollment by Major - {event_id} ({year_start}-{year_end})")

            enrl_curr_yt = ( df1.loc[
                (df1['EVENT_ID']==event_id),
                ['yearterm', 'yearterm_sort', 'EVENT_ID', 'EVENT_SUB_TYPE', 'section_id', 'instructor', 'CURRICULUM', 'PEOPLE_CODE_ID']
                ]
                .groupby(['EVENT_ID', 'yearterm', 'EVENT_SUB_TYPE', 'CURRICULUM']).agg(
                    {
                        'PEOPLE_CODE_ID': 'count',
                        'yearterm_sort': 'first',
                    }
                    )
                .reset_index()
                .sort_values(['EVENT_ID', 'yearterm_sort', 'EVENT_SUB_TYPE', 'CURRICULUM' ])
                .drop(['yearterm_sort'], axis=1)
                .rename(
                    columns={
                        'EVENT_ID': 'course',
                        'EVENT_SUB_TYPE': 'section_type',
                        'CURRICULUM': 'curriculum',
                        'PEOPLE_CODE_ID': 'curr_enrollment',
                    },
                )
            )

            enrl_curr_yt = ( enrl_curr_yt.merge(enrl_yt,
                how='left',
                on=['course', 'section_type', 'yearterm', ]
                )
            )
            enrl_curr_yt = enrl_curr_yt[['course', 'yearterm', 'section_type', 'course_enrollment', 'curriculum', 'curr_enrollment',]]
            enrl_curr_yt['curr_pct'] = (enrl_curr_yt['curr_enrollment'] / enrl_curr_yt['course_enrollment'] * 100.0).map('{:,.2f}%'.format)

            
            st.dataframe(enrl_curr_yt)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(enrl_curr_yt),
                file_name=f"{event_id}_{year_start}-{year_end}_course_enrollment_by_major_by_yearterm.csv",
                mime='text/csv',
            )

            st.markdown("---")

            # Export to Excel
            st.write(f"#### {event_id} Excel workbook with all course enrollment tables")

            df_to_add = [
                    [enrl_yt, 'course enrollment'],
                    [enrl_inst_yt, 'by instructor'],
                    [enrl_curr_yt, 'by major'],
            ]

            st.download_button(
                label=f"Download Excel workbook for {event_id} as .xlsx",
                data=convert_df_xlsx(df_to_add),
                file_name=f"{event_id}_{year_start}-{year_end}_course_enrollment_{today_str}.xlsx",
                mime='application/vnd.ms-excel',
            )
            
