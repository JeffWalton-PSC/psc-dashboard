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

    sectionper = pc.select("SECTIONPER", 
        fields=['PERSON_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 
            'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION', 
            ],
        where=f"ACADEMIC_YEAR>='{int(start_year)}' ",
        )
    sectionper['ACADEMIC_TERM'] = sectionper['ACADEMIC_TERM'].str.upper()
    sectionper['ACADEMIC_SESSION'] = sectionper['ACADEMIC_SESSION'].str.upper()
    keep_flds = [
        "ACADEMIC_YEAR",
        "ACADEMIC_TERM",
        "ACADEMIC_SESSION",
        "PERSON_CODE_ID",
        'EVENT_ID', 
        'EVENT_SUB_TYPE', 
        'SECTION',
    ]
    sectionper = ( sectionper.loc[:, keep_flds]
        .sort_values(keep_flds)
        .drop_duplicates(keep_flds, keep="last", )
    )
    people = pc.select('PEOPLE',
        fields=['PEOPLE_CODE_ID', 'FIRST_NAME', 'LAST_NAME', ],
        where="DECEASED_FLAG<>'Y' and BIRTH_DATE>'1899-01-01' and BIRTH_DATE<'2500-01-01'",
        )
    people['instructor'] = people['LAST_NAME'] + ", " + people['FIRST_NAME']
    sectionper = sectionper.merge(people,
        how='left',
        left_on='PERSON_CODE_ID',
        right_on='PEOPLE_CODE_ID'
        )
    sectionper = sectionper.drop(
            ['PERSON_CODE_ID', 'PEOPLE_CODE_ID', ],
            axis='columns',
        )

    df = pd.merge(
        df,
        sectionper,
        on=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 
            'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION' ],
        how="left",
    )

    df = df.drop(
            ['FIRST_NAME', 'LAST_NAME', ],
            axis='columns',
        )


    return df


start_year = '2012'

current_yt_df = pc.current_yearterm()
ay_func = ( lambda r: r['year'] 
            if r['term'] in ['FALL', '10-WEEK_1', '10-WEEK_2']
            else str(int(r["year"]) - 1)
    )
current_yt_df['ay'] = current_yt_df.apply(ay_func, axis=1)
current_yt_df['ay_label'] = current_yt_df['ay'] + '-' + (current_yt_df['ay'].astype(int) + 1 ).astype('string')
current_term = current_yt_df['term'].iloc[0]
current_year = current_yt_df['year'].iloc[0]
current_yt = current_yt_df['yearterm'].iloc[0]
current_yt_sort = current_yt_df['yearterm_sort'].iloc[0]
current_ay = current_yt_df['ay'].iloc[0]
current_ay_label = current_yt_df['ay_label'].iloc[0]


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Faculty - Teaching ..."):
        src.pages.components.page_header()
        st.write(
            """
            ## Faculty - Teaching
"""
        )

        today = dt.datetime.today()
        today_str = today.strftime("%Y%m%d")

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
            
            st.write(f"#### Faculty Credits Taught by Term ({year_start}-{year_end})")
            df1 = (
                df0.groupby(["instructor", "yearterm", ])["CREDIT"].sum()
                .reset_index()
                .astype({'CREDIT': 'int'})
                .rename(columns={"CREDIT": "total_credits"})
                .sort_values(["instructor", 'yearterm'], key=yt_sorter)
            )
            st.dataframe(df1)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df1),
                file_name=f"{year_start}-{year_end}_faculty_term_total_credits.csv",
                mime='text/csv',
            )

            st.write(f"#### Faculty Credits Taught in Current Year.Term ({current_yt})")
            df2 = df1.loc[(df1['yearterm']==current_yt)]
            c1 = alt.Chart(df2).mark_bar().encode(
                x=alt.X('instructor:N', sort=yt_list),
                y=alt.Y('total_credits:Q', axis=alt.Axis(title='total credits')),
                tooltip=['yearterm:N', 
                    alt.Tooltip('instructor:N', title='instructor'),
                    alt.Tooltip('total_credits:Q', title='total credits taught'),
                    ],
            )
            st.altair_chart(c1)

            st.write(f"#### Faculty Credits Taught by Academic Year ({year_start}-{year_end})")
            df3 = (
                df0.groupby(["instructor", "ay_label", ])["CREDIT"].sum()
                .reset_index()
                .astype({'CREDIT': 'int'})
                .rename(columns={"CREDIT": "total_credits"})
                .sort_values(["instructor", 'ay_label'], key=yt_sorter)
            )
            st.dataframe(df3)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df3),
                file_name=f"{year_start}-{year_end}_faculty_ay_total_credits.csv",
                mime='text/csv',
            )

            st.write(f"#### Faculty Credits Taught in Current Academic Year ({current_ay_label})")
            df4 = df3.loc[(df3['ay_label']==current_ay_label)]
            c2 = alt.Chart(df4).mark_bar().encode(
                x=alt.X('instructor:N', sort=yt_list),
                y=alt.Y('total_credits:Q', axis=alt.Axis(title='total credits')),
                tooltip=[
                    alt.Tooltip('ay_label:N', title='academic year'),
                    alt.Tooltip('instructor:N', title='instructor'),
                    alt.Tooltip('total_credits:Q', title='total credits taught'),
                    ],
            )
            st.altair_chart(c2)

            st.write(f"#### Faculty Credits Taught by Student's Academic Program ({year_start}-{year_end})")
            df5 = (
                df0.groupby(["instructor", "yearterm", "stu_program"])["CREDIT"].sum()
                .reset_index()
                .astype({'CREDIT': 'int'})
                .rename(columns={"CREDIT": "total_credits"})
                .sort_values(["instructor", 'yearterm', "stu_program"], key=yt_sorter)
            )
            df6 = ( pd.merge(
                        df5,
                        df1,
                        on=['instructor', 'yearterm' ],
                        how="left",
                    ).rename(
                        columns={
                            'total_credits_x': 'credits',
                            'total_credits_y': 'total_credits',
                            'stu_program': 'program',
                        }
                    )
            )
            df6['percent'] = df6['credits'] / df6['total_credits']
            st.dataframe(df6)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df6),
                file_name=f"{year_start}-{year_end}_faculty_term_program_credits.csv",
                mime='text/csv',
            )

            st.write(f"#### Faculty Credits Taught by Student's Academic Program in Current Year.Term ({current_yt})")
            df7 = df6.loc[(df6['yearterm']==current_yt)]
            c3 = alt.Chart(df7).mark_bar().encode(
                    x=alt.X('instructor:N'),
                    y=alt.Y('percent:Q', stack="normalize", axis=alt.Axis(format='.0%',title='percent of credits')),
                    color=alt.Color(shorthand='program:N'),
                    tooltip=['yearterm:N', 
                        alt.Tooltip('instructor:N', title='instructor'),
                        alt.Tooltip('program:N', title='program'),
                        alt.Tooltip('credits:Q', title='credits'),
                        alt.Tooltip('total_credits:Q', title='instructor credits'),
                        alt.Tooltip('percent:Q', format='.0%',title='percent'),
                        ],
                ).properties(
                    height=800
                )
            st.altair_chart(c3)

