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

        undergrad_only = st.checkbox("Undergrad students only", value=True )
        # exclude_online = st.checkbox("Exclude online sections", value=True )

        section_types = ['COMB', 'HYBD', 'LEC', 'ONLN', 'PRAC', 'LAB', 'SI']
        include_section_types = st.multiselect("Include section types:", options=section_types, default=['COMB', 'HYBD', 'LEC', 'ONLN', 'PRAC'])

        if st.radio( "Select grade:", options=['Mid-term', 'Final'], index=1 ) == 'Mid-term':
            grade_type = 'MID_GRADE'
        else:
            grade_type = 'FINAL_GRADE'


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

            if undergrad_only:
                academic = academic.loc[(academic['PROGRAM'] != 'G')]

            transcriptdetail = pc.select("TRANSCRIPTDETAIL",
                fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION',
                    'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION', 'EVENT_TYPE', 'EVENT_MED_NAME', 'EVENT_LONG_NAME',
                    'CREDIT', 'MID_GRADE', 'FINAL_GRADE', 'ADD_DROP_WAIT',
                    ],
                where=f"ACADEMIC_YEAR>='{int(year_start)}' and ACADEMIC_YEAR<='{int(year_end)}' and ACADEMIC_TERM='{term}' " +
                    "and ADD_DROP_WAIT='A' ", 
            )
            transcriptdetail = transcriptdetail.loc[(transcriptdetail['EVENT_SUB_TYPE'].isin(include_section_types))]

            atd = academic.merge(transcriptdetail,
                how='left',
                on=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', ]
                )
            atd = pc.add_col_yearterm(atd)
            atd = pc.add_col_yearterm_sort(atd)
            atd['course_section_id'] = (
                atd["EVENT_ID"].str.rstrip().str.upper() + "." + 
                atd["EVENT_SUB_TYPE"].str.upper() + "."  + 
                atd["ACADEMIC_YEAR"] + "."  + 
                atd["ACADEMIC_TERM"].str.title()  + "."  + 
                atd["SECTION"].str.upper()
                )
            keep_cols = [
                'PEOPLE_CODE_ID', 'yearterm', 'course_section_id', 'MID_GRADE', 'FINAL_GRADE',
            ]
            atd = atd.loc[:, keep_cols]

            grade_mapping = [
                ["A+",   "A+"],
                ["A+*",  "A+"],
                ["A",    "A"],
                ["A*",   "A"],
                ["B+",   "B+"],
                ["B+*",  "B+"],
                ["B",    "B"],
                ["B*",   "B"],
                ["C+",   "C+"],
                ["C+*",  "C+"],
                ["C",    "C"],
                ["C*",   "C"],
                ["D+",   "D+"],
                ["D+*",  "D+"],
                ["D",    "D"],
                ["D*",   "D"],
                ["F",    "F"],
                ["F*",   "F"],
                ["P",    "P"],
                ["P*",   "P"],
                ["DEF",  "INC"],
                ["INC",  "INC"],
                ["INC*", "INC"],
                ["W",    "W"],
                ["W*",   "W"],
                ["WF",   "W"],
                ["WF*",  "W"],
                ["WP",   "W"],
                ["WP*",  "W"],
                ["AU",   "AU"],
            ]
            grades = pd.DataFrame(
                grade_mapping,
                columns=['pc_grade', 'grade']
            )
            atd = atd.merge(grades,
                how='left',
                left_on=grade_type,
                right_on='pc_grade'
                )


            st.write(f"#### Grade Distribution ({term} {year_start}-{year_end})")

            grade_sort = [ "A+", "A", "B+", "B", "C+", "C", "D+", "D", "F", "P", "INC", "W", "AU", ]
            grade_sort_dict = {value: order for order, value in enumerate(grade_sort)}
            # st.write(grade_sort_dict)
            grade_sorter = lambda x: x.map(grade_sort_dict).fillna(x)

            # def grade_sorter(column):
            #     cat = pd.Categorical(column, categories=grade_sort, ordered=True).fillna(column)
            #     return pd.Series(cat)

            g = ( atd[['yearterm', 'PEOPLE_CODE_ID', 'course_section_id', 'grade',]].groupby(['yearterm', 'grade']).agg(
                    {'PEOPLE_CODE_ID': ['count', ]}
                )
                .droplevel(0, axis=1)
                # .sort_index(level=['yearterm', 'grade'], key=grade_sorter )
                .sort_index()
                .reset_index()
            )
            # st.write(pd.Categorical(g['grade'], categories=grade_sort, ordered=True))
            

            g = g.sort_values(['yearterm', 'grade'], key=grade_sorter)


            grade_dist = ( g.pivot(
                    index='yearterm', 
                    columns='grade',
                    values='count'
                    )
                .fillna(0)
                .reset_index()
                .loc[:,['yearterm'] + grade_sort]
            )
            grade_dist[grade_sort] = grade_dist[grade_sort].astype(int)
            st.dataframe(grade_dist)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(grade_dist),
                file_name=f"{term}_{year_start}-{year_end}_grade_distribution.csv",
                mime='text/csv',
            )

            # st.dataframe(g)
            # st.write(grade_sort)
            c1 = alt.Chart(g).transform_joinaggregate(
                    YearTermCount='sum(count)',
                    groupby=['yearterm']
                ).transform_calculate(
                    PercentOfTotal="datum.count / datum.YearTermCount",
                ).mark_bar().encode(
                x='yearterm:N',
                y=alt.Y('PercentOfTotal:Q', axis=alt.Axis(title='percent of yearterm grades', format='.0%')),
                color='yearterm:N',
                column=alt.Column(shorthand='grade:N', sort=grade_sort),
                tooltip=['grade', 'yearterm', alt.Tooltip('sum(count):Q', title='count'), alt.Tooltip('PercentOfTotal:Q', title='pct of yearterm', format='.3p')],
            )
            st.altair_chart(c1)
