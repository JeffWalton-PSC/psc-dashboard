import pandas as pd
import streamlit as st
import altair as alt
import datetime as dt
import src.pages.components

# PowerCampus utilities
import powercampus as pc

@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')


@st.cache_data
def academic_df(start_year:str) -> pd.DataFrame:

    academic = pc.select("ACADEMIC", 
        fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 
            'PROGRAM', 'DEGREE', 'CURRICULUM', 
            'COLLEGE', 'DEPARTMENT', 'CREDITS',
            ],
        where=f"ACADEMIC_YEAR>='{int(start_year)}' " +
            "and ACADEMIC_TERM IN ('FALL', '10-Week_1', '10-Week_2', 'SPRING', 'SUMMER', '10-Week_3', '10-Week_4' ) " +
            "and ACADEMIC_SESSION='' and PRIMARY_FLAG='Y' " +
            "and CURRICULUM NOT IN ('ADVST') and CREDITS > 0 ", 
        )
    academic['ACADEMIC_TERM'] = academic['ACADEMIC_TERM'].str.upper()
    academic['ACADEMIC_SESSION'] = academic['ACADEMIC_SESSION'].str.upper()

    keep_flds = [
        "ACADEMIC_YEAR",
        "ACADEMIC_TERM",
        "ACADEMIC_SESSION",
        "PEOPLE_CODE_ID",
        "COLLEGE",
    ]
    academic = ( academic.loc[:, keep_flds]
        .sort_values(keep_flds)
        .drop_duplicates(keep_flds, keep="last", )
        .rename(columns={"COLLEGE": "stu_dept"})
    )
    ay_func = ( lambda r: r['ACADEMIC_YEAR'] 
                if r['ACADEMIC_TERM'] in ['FALL', '10-WEEK_1', '10-WEEK_2']
                else str(int(r["ACADEMIC_YEAR"]) - 1)
        )
    academic['ay'] = academic.apply(ay_func, axis=1)
    academic['ay_label'] = academic['ay'] + '-' + (academic['ay'].astype(int) + 1 ).astype('string')

    academic = pc.add_col_yearterm(academic)
    academic = pc.add_col_yearterm_sort(academic)


    return academic


start_year = '2012'

current_yt_df = pc.current_yearterm()
current_term = current_yt_df['term'].iloc[0]
current_year = current_yt_df['year'].iloc[0]
current_yt = current_yt_df['yearterm'].iloc[0]
current_yt_sort = current_yt_df['yearterm_sort'].iloc[0]


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Academic Department - Enrollment ..."):
        src.pages.components.page_header()
        st.write(
            """
            ## Academic Department - Enrollment
"""
        )

        today = dt.datetime.today()
        today_str = today.strftime("%Y%m%d_%H%M")

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
        year_list = [y for y in year_list if ((y>=start_year) and (y<=current_year))]
        year_start, year_end = st.select_slider(
            "Select range of years:",
            options=year_list,
            value=('2014', current_year)
        )

        if year_start and year_end:

            df = academic_df(start_year)
            df0 = ( df.loc[(df['ACADEMIC_YEAR']>=year_start) & (df['ACADEMIC_YEAR']<=year_end)]
                    .rename(columns={"stu_dept": "department"})
            )
            df0['department'] = df0['department'].fillna('unlabeled')
            df0.loc[(df0['department']==''), 'department'] = 'unlabeled'

            df_yt = ( df0.groupby(['ACADEMIC_YEAR', 'ACADEMIC_TERM'])
                        .agg(
                            {'yearterm': ['first',],
                            'yearterm_sort': ['first',],
                            }
                        )
                        .reset_index()
                        .droplevel(1, axis=1)
                        .sort_values(['yearterm_sort'])
            )
            yt_sort_dict = { value: order for order, value in df_yt[['yearterm_sort', 'yearterm']].to_dict('split')['data']}
            yt_sorter = lambda x: x.map(yt_sort_dict).fillna(x)
            yt_list = df_yt['yearterm'].unique().tolist()
            
            # st.dataframe(df0)

            st.write(f"#### PSC Enrollment by Term ({year_start}-{year_end})")
            df1 = (
                df0.groupby(["yearterm"])["PEOPLE_CODE_ID"].count()
                .reset_index()
                .astype({'PEOPLE_CODE_ID': 'int'})
                .rename(columns={"PEOPLE_CODE_ID": "total_students"})
                .sort_values(['yearterm'], key=yt_sorter)
            )
            st.dataframe(df1)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df1),
                file_name=f"{year_start}-{year_end}_PSC_term__enrollment.csv",
                mime='text/csv',
            )

            c1 = alt.Chart(df1.reset_index()).mark_bar().encode(
                x=alt.X('yearterm:N', sort=yt_list),
                y=alt.Y('total_students:Q', axis=alt.Axis(title='total number of students')),
                tooltip=['yearterm:N', alt.Tooltip('total_students:Q', title='total students')],
            )
            st.altair_chart(c1)

            st.write(f"#### Department Enrollment by Term ({year_start}-{year_end})")
            df2 = (
                df0.groupby(["yearterm", "department"])["PEOPLE_CODE_ID"]
                .count()
                .reset_index()
                .astype({'PEOPLE_CODE_ID': 'int'})
                .rename(columns={"PEOPLE_CODE_ID": "students"})
                .sort_values(['yearterm', 'department'], key=yt_sorter)
            )
            df2 = df2.merge(
                df1,
                how='left',
                on='yearterm'
            ).loc[:,['yearterm', 'department', 'students', 'total_students' ]]
            df2['dept_pct'] = df2['students'] / df2['total_students'] * 100.0
            st.dataframe(df2)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df2),
                file_name=f"{year_start}-{year_end}_department_term_students.csv",
                mime='text/csv',
            )
            c2 = alt.Chart(df2).transform_calculate(
                    PercentOfTotal="datum.students / datum.total_students",
                ).mark_bar().encode(
                    x=alt.X('yearterm:N', sort=yt_list),
                    y=alt.Y('PercentOfTotal:Q', stack="normalize", axis=alt.Axis(format='.0%',title='percent of total students')),
                    color=alt.Color(shorthand='department:N'),
                    tooltip=['yearterm', 'department', 
                        alt.Tooltip('students:Q', title='dept students'), 
                        alt.Tooltip('total_students:Q', title='total students'), 
                        alt.Tooltip('PercentOfTotal:Q', title='pct of total', format='.1%')],
                )
            st.altair_chart(c2)

            st.write(f"#### Department Enrollments by Academic Year ({year_start}-{year_end})")
            df3 = (
                df0.loc[(df0['ay']>=year_start)]
                .groupby(["ay_label", "department"])["PEOPLE_CODE_ID"]
                .count()
                .reset_index()
                .astype({'PEOPLE_CODE_ID': 'int'})
                .rename(columns={"PEOPLE_CODE_ID": "dept_students"})
                .sort_values(['ay_label', 'department'], key=yt_sorter)
            )
            df4 = (
                df0.groupby(["ay_label"])["PEOPLE_CODE_ID"].count()
                .reset_index()
                .astype({'PEOPLE_CODE_ID': 'int'})
                .rename(columns={"PEOPLE_CODE_ID": "total_students"})
                .sort_values(['ay_label'])
            )
            df3 = df3.merge(
                df4,
                how='left',
                on='ay_label',
            ).loc[:,['ay_label', 'department', 'dept_students', 'total_students' ]]
            df3['dept_pct'] = df3['dept_students'] / df3['total_students'] * 100.0
            st.dataframe(df3)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df3),
                file_name=f"{year_start}-{year_end}_ay_department_enrollment.csv",
                mime='text/csv',
            )
            c3 = alt.Chart(df3).transform_calculate(
                    PercentOfTotal="datum.dept_students / datum.total_students",
                ).mark_bar().encode(
                    x=alt.X('ay_label:N', axis=alt.Axis(title='academic year')),
                    y=alt.Y('PercentOfTotal:Q', stack="normalize", axis=alt.Axis(format='.0%',title='percent of total AY enrollments')),
                    color=alt.Color(shorthand='department:N'),
                    tooltip=['ay_label', 'department', 
                        alt.Tooltip('dept_students:Q', title='dept students'), 
                        alt.Tooltip('total_students:Q', title='total students'), 
                        alt.Tooltip('PercentOfTotal:Q', title='pct of total', format='.1%')],
                )
            st.altair_chart(c3)
