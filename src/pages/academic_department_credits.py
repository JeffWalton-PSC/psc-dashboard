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


# @st.cache_data
def course_df(start_year:str) -> pd.DataFrame:

    sections = pc.select("SECTIONS", 
        fields=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',
            'EVENT_MED_NAME', 'EVENT_LONG_NAME', 'EVENT_STATUS', 'PROGRAM', 'COLLEGE', 'DEPARTMENT', 'CURRICULUM',
            'CREDITS', ],
        where=f"ACADEMIC_YEAR>='{int(start_year)}' " +
            "and ACADEMIC_TERM in ('FALL', '10-Week_1', '10-Week_2', 'SPRING', 'SUMMER', '10-Week_3', '10-Week_4' ) " +
            "and ACADEMIC_SESSION in ('MAIN', 'CULN', 'EXT', 'FNRR', 'HEOP', 'SLAB', 'BLOCK A', 'BLOCK AB', 'BLOCK B' ) " +
            "and EVENT_SUB_TYPE NOT in ('ACE', 'ADV', 'CELL', 'STAB') " +
            "and ADDS>0 and EVENT_STATUS='A' and CREDITS > 0 ", 
        )
    sections['ACADEMIC_TERM'] = sections['ACADEMIC_TERM'].str.upper()
    sections['ACADEMIC_SESSION'] = sections['ACADEMIC_SESSION'].str.upper()
    sections['EVENT_ID'] = sections['EVENT_ID'].str.upper()
    sections['EVENT_SUB_TYPE'] = sections['EVENT_SUB_TYPE'].str.upper()
    sections = sections.loc[(~sections['EVENT_ID'].str.startswith('REG')) & 
                            (~sections["EVENT_ID"].str.contains("STDY", case=False)) &
                            (~sections['EVENT_SUB_TYPE'].isin(['ACE', 'ADV', 'CELL', 'STAB'])), :]
    sections = sections.drop_duplicates(['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION'])
    sections = sections.sort_values(['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION'])

    keep_flds = [
        "ACADEMIC_YEAR",
        "ACADEMIC_TERM",
        "ACADEMIC_SESSION",
        "EVENT_ID",
        "COLLEGE",
    ]
    sections = ( sections.loc[:, keep_flds]
        .sort_values(keep_flds)
        .drop_duplicates(keep_flds, keep="last", )
        .rename(columns={"COLLEGE": "crs_dept"})
    )
    ay_func = ( lambda r: r['ACADEMIC_YEAR'] 
                if r['ACADEMIC_TERM'] in ['FALL', '10-WEEK_1', '10-WEEK_2']
                else str(int(r["ACADEMIC_YEAR"]) - 1)
        )
    sections['ay'] = sections.apply(ay_func, axis=1)
    sections['ay_label'] = sections['ay'] + '-' + (sections['ay'].astype(int) + 1 ).astype('string')

    transcriptdetail = pc.select("TRANSCRIPTDETAIL",
        fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION',
            'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION', 'CREDIT',
            ],
        where=f"ACADEMIC_YEAR>='{int(start_year)}' " +
            "and ACADEMIC_TERM in ('FALL', '10-Week_1', '10-Week_2', 'SPRING', 'SUMMER', '10-Week_3', '10-Week_4' ) " +
            "and ACADEMIC_SESSION in ('MAIN', 'CULN', 'EXT', 'FNRR', 'HEOP', 'SLAB', 'BLOCK A', 'BLOCK AB', 'BLOCK B' ) " +
            "and EVENT_SUB_TYPE NOT IN ('ADV') " +
            "and ADD_DROP_WAIT = 'A' and CREDIT > 0 and CREDIT_TYPE <> 'TRAN' ", 
    )
    transcriptdetail['ACADEMIC_SESSION'] = transcriptdetail['ACADEMIC_SESSION'].str.upper()
    transcriptdetail['ACADEMIC_TERM'] = transcriptdetail['ACADEMIC_TERM'].str.upper()
    transcriptdetail['EVENT_ID'] = transcriptdetail['EVENT_ID'].str.rstrip().str.upper()

    df = pd.merge(
        transcriptdetail,
        sections,
        on=["EVENT_ID", "ACADEMIC_YEAR", "ACADEMIC_TERM", 'ACADEMIC_SESSION', ],
        how="left",
    )

    df["yearterm"] = df["ACADEMIC_YEAR"] + "." + df["ACADEMIC_TERM"].str.title()
    df = df.loc[~(df["EVENT_ID"].str.contains("REG", case=False)) & ~(df["EVENT_ID"].str.contains("STDY", case=False))]
    df = pc.add_col_yearterm_sort(df)

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
        "CURRICULUM",
    ]
    academic = ( academic.loc[:, keep_flds]
        .sort_values(keep_flds)
        .drop_duplicates(keep_flds, keep="last", )
        .rename(
            columns={
                "COLLEGE": "stu_dept",
                "CURRICULUM": "stu_program",
                }
                )
        .drop(
            ['ACADEMIC_SESSION'],
            axis='columns',
        )
    )

    df = pd.merge(
        df,
        academic,
        on=["PEOPLE_CODE_ID", "ACADEMIC_YEAR", "ACADEMIC_TERM"],
        how="left",
    )

    return df


start_year = '2012'

current_yt_df = pc.current_yearterm()
current_term = current_yt_df['term'].iloc[0]
current_year = current_yt_df['year'].iloc[0]
current_yt = current_yt_df['yearterm'].iloc[0]
current_yt_sort = current_yt_df['yearterm_sort'].iloc[0]


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Academic Department - Credits ..."):
        src.pages.components.page_header()
        st.write(
            """
            ## Academic Department - Credits
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
            value=('2016', current_year)
        )

        if year_start and year_end:

            df = course_df(start_year)
            df0 = ( df.loc[(df['ACADEMIC_YEAR']>=year_start) & (df['ACADEMIC_YEAR']<=year_end)]
                    .rename(columns={"crs_dept": "department"})
            )
            df0['department'] = df0['department'].fillna('unlabeled')
            df0.loc[(df0['department']==''), 'department'] = 'unlabeled'
            df0['stu_dept'] = df0['stu_dept'].fillna('unlabeled')
            df0.loc[(df0['stu_dept']==''), 'stu_dept'] = 'unlabeled'
            df0.loc[(df0['stu_dept']==' '), 'stu_dept'] = 'unlabeled'
            # st.dataframe(df0)

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

            st.write(f"#### PSC Total Credits by Term ({year_start}-{year_end})")
            df1 = (
                df0.groupby(["yearterm"])["CREDIT"].sum()
                .reset_index()
                .astype({'CREDIT': 'int'})
                .rename(columns={"CREDIT": "total_credit"})
                .sort_values(['yearterm'], key=yt_sorter)
            )
            st.dataframe(df1)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df1),
                file_name=f"{year_start}-{year_end}_term_total_credits.csv",
                mime='text/csv',
            )

            c1 = alt.Chart(df1.reset_index()).mark_bar().encode(
                x=alt.X('yearterm:N', sort=yt_list),
                y=alt.Y('total_credit:Q', axis=alt.Axis(title='total credits')),
                tooltip=['yearterm:N', alt.Tooltip('total_credit:Q', title='total credits')],
            )
            st.altair_chart(c1)

            st.write(f"#### Department Credits by Term ({year_start}-{year_end})")
            df2 = (
                df0.groupby(["yearterm", "department"])["CREDIT"]
                .sum()
                .reset_index()
                .astype({'CREDIT': 'int'})
                .rename(columns={"CREDIT": "dept_credit"})
                .sort_values(['yearterm', 'department'], key=yt_sorter)
            )
            df2 = df2.merge(
                df1,
                how='left',
                on='yearterm'
            ).loc[:,['yearterm', 'department', 'dept_credit', 'total_credit' ]]
            df2['dept_pct'] = df2['dept_credit'] / df2['total_credit'] * 100.0
            st.dataframe(df2)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df2),
                file_name=f"{year_start}-{year_end}_term_department_credits.csv",
                mime='text/csv',
            )
            c2 = alt.Chart(df2).transform_calculate(
                    PercentOfTotal="datum.dept_credit / datum.total_credit",
                ).mark_bar().encode(
                    x=alt.X('yearterm:N', sort=yt_list),
                    y=alt.Y('PercentOfTotal:Q', stack="normalize", axis=alt.Axis(format='.0%',title='percent of total credits')),
                    color=alt.Color(shorthand='department:N'),
                    tooltip=['yearterm', 'department', 
                        alt.Tooltip('dept_credit:Q', title='dept credit'), 
                        alt.Tooltip('total_credit:Q', title='total credit'), 
                        alt.Tooltip('PercentOfTotal:Q', title='pct of total', format='.1%')],
                )
            st.altair_chart(c2)

            st.write(f"#### Department Credits by Academic Year ({year_start}-{year_end})")
            df3 = (
                df0.loc[(df0['ay']>=year_start)]
                .groupby(["ay_label", "department"])["CREDIT"]
                .sum()
                .reset_index()
                .astype({'CREDIT': 'int'})
                .rename(columns={"CREDIT": "dept_credit"})
                .sort_values(['ay_label', 'department'], key=yt_sorter)
            )
            df4 = (
                df0.groupby(["ay_label"])["CREDIT"].sum()
                .reset_index()
                .astype({'CREDIT': 'int'})
                .rename(columns={"CREDIT": "total_credit"})
                .sort_values(['ay_label'])
            )
            df3 = df3.merge(
                df4,
                how='left',
                on='ay_label',
            ).loc[:,['ay_label', 'department', 'dept_credit', 'total_credit' ]]
            df3['dept_pct'] = df3['dept_credit'] / df3['total_credit'] * 100.0
            st.dataframe(df3)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df3),
                file_name=f"{year_start}-{year_end}_ay_department_credits.csv",
                mime='text/csv',
            )
            c3 = alt.Chart(df3).transform_calculate(
                    PercentOfTotal="datum.dept_credit / datum.total_credit",
                ).mark_bar().encode(
                    x=alt.X('ay_label:N', axis=alt.Axis(title='academic year')),
                    y=alt.Y('PercentOfTotal:Q', stack="normalize", axis=alt.Axis(format='.0%',title='percent of total credits')),
                    color=alt.Color(shorthand='department:N'),
                    tooltip=['ay_label', 'department', 
                        alt.Tooltip('dept_credit:Q', title='dept credit'), 
                        alt.Tooltip('total_credit:Q', title='total credit'), 
                        alt.Tooltip('PercentOfTotal:Q', title='pct of total', format='.1%')],
                )
            st.altair_chart(c3)


            st.write(f"#### Department Credits by Student Department ({year_start}-{year_end})")
            df5 = (
                df0.groupby(["ay_label", "department", "stu_dept"])["CREDIT"].sum()
                .reset_index()
                .astype({'CREDIT': 'int'})
                .rename(columns={"CREDIT": "stu_credit"})
                .sort_values(['ay_label'])
            )
            # st.dataframe(df5)
            df6 = df3.merge(
                df5,
                how='left',
                on=['ay_label', 'department'],
            ).loc[:,['ay_label', 'department', 'dept_credit', 'stu_dept', 'stu_credit' ]]
            df6['stu_pct'] = df6['stu_credit'] / df6['dept_credit'] * 100.0
            # st.dataframe(df6)
            st.write("##### Department Teaching - Credits")
            st.write("Teaching Department in rows; Student Departments in columns.")
            df6_pivot = ( df6.pivot(index=['ay_label', 'department'], columns='stu_dept', values='stu_credit')
                            .fillna(0)
                            .astype('int')
            )
            st.dataframe(df6_pivot)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df6_pivot.reset_index()),
                file_name=f"{year_start}-{year_end}_ay_department_student_credits.csv",
                mime='text/csv',
            )
            st.write("##### Department Teaching - Percentge")
            st.write("Teaching Department in rows; Student Departments in columns.")
            df6_pivot_pct = ( df6.pivot(index=['ay_label', 'department'], columns='stu_dept', values='stu_pct')
                            .fillna(0)
                            # .astype('int')
            )
            st.dataframe(df6_pivot_pct)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df6_pivot_pct.reset_index()),
                file_name=f"{year_start}-{year_end}_ay_department_student_credits_pct.csv",
                mime='text/csv',
            )
            c4 = alt.Chart(df6).transform_calculate(
                    PercentOfTotal="datum.stu_credit / datum.dept_credit",
                ).mark_bar().encode(
                    x=alt.X('stu_pct:Q', stack="normalize", axis=alt.Axis(title='student department')),
                    y=alt.Y('department:N', axis=alt.Axis(title='teaching department')),
                    color=alt.Color(shorthand='stu_dept:N'),
                    row='ay_label:N',
                    tooltip=[
                        alt.Tooltip('ay_label', title='academic year'), 
                        alt.Tooltip('department', title='department'), 
                        alt.Tooltip('dept_credit:Q', title='dept credit'), 
                        alt.Tooltip('stu_dept:N', title='student dept'), 
                        alt.Tooltip('stu_credit:Q', title='student credit'),
                        alt.Tooltip('PercentOfTotal:Q', title='pct of dept', format='.1%'),
                        ],
                )
            st.altair_chart(c4)
