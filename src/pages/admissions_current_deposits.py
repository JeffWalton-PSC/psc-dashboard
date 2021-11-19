import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
import datetime as dt
from pathlib import Path
import src.pages.components

# local connection information
import local_db

WEEKS_FOR_PREVIOUS_DEPOSITS = 3

@st.cache
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Admissions - Current Deposits ..."):
        src.pages.components.logo()
        st.write(
            """
            ## Admissions - Current Deposits
            ### Current deposits by academic program from PowerCampus
"""
        )

        connection = local_db.connection()

        today = dt.date.today()
        today_str = today.strftime("%Y%m%d")

        sql_str = f"""
            SELECT *
            FROM dbo.[ACADEMICCALENDAR]
            WHERE [ACADEMICCALENDAR].[END_DATE] > '{today - dt.timedelta(weeks=WEEKS_FOR_PREVIOUS_DEPOSITS)}'
            """
        df_cal = pd.read_sql_query(sql_str, connection)
        yearterm_sort = ( lambda r: 
            r['ACADEMIC_YEAR'] + '01' if r['ACADEMIC_TERM']=='SPRING' else
            r['ACADEMIC_YEAR'] + '02' if r['ACADEMIC_TERM']=='SUMMER' else
            r['ACADEMIC_YEAR'] + '03' if r['ACADEMIC_TERM']=='FALL' else
            r['ACADEMIC_YEAR'] + '00'
        )
        df_cal['yearterm_sort'] = df_cal.apply(yearterm_sort, axis=1)

        df_cal['yearterm'] = df_cal['ACADEMIC_YEAR'] + '.' +  df_cal['ACADEMIC_TERM'].str.title()
        keep_cols = [
        'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'END_DATE', 'yearterm_sort', 'yearterm',
        ]
        df_cal = ( df_cal.loc[:,keep_cols]
                .sort_values(['yearterm_sort', 'END_DATE', ])
                .drop_duplicates(['yearterm_sort'], keep='last')
                )

        year_list = sorted(df_cal['ACADEMIC_YEAR'].unique())
        term_list = sorted(df_cal['ACADEMIC_TERM'].unique())
        yearterm_list = df_cal['yearterm'].unique()

        sql_str = f"""
        SELECT 
            [ACADEMIC].[PEOPLE_CODE_ID],
            [ACADEMIC].[DEGREE],
            [ACADEMIC].[CURRICULUM],
            [ACADEMIC].[ACADEMIC_YEAR],
            [ACADEMIC].[ACADEMIC_TERM],
            [ACADEMIC].[ADMIT_YEAR],
            [ACADEMIC].[ADMIT_TERM],
            [ACADEMIC].[APP_STATUS_DATE],
            [ACADEMIC].[APP_STATUS]
        FROM dbo.[ACADEMIC]
        WHERE (  
            [ACADEMIC].[ADMIT_YEAR] = [ACADEMIC].[ACADEMIC_YEAR]  AND
            [ACADEMIC].[ADMIT_TERM] = [ACADEMIC].[ACADEMIC_TERM]  AND
            [ACADEMIC].[ACADEMIC_YEAR] IN {tuple(year_list)}  AND
            [ACADEMIC].[ACADEMIC_TERM] IN {tuple(term_list)}  AND
            [ACADEMIC].[APP_STATUS] = N'500'  AND
            [ACADEMIC].[ACADEMIC_SESSION] = N''   AND
            (ACADEMIC.APP_DECISION = 'DPAC' OR
            ACADEMIC.APP_DECISION = 'TRDP')
            )
        GROUP BY 
            [ACADEMIC].[PEOPLE_CODE_ID],
            [ACADEMIC].[DEGREE], 
            [ACADEMIC].[CURRICULUM], 
            [ACADEMIC].[ACADEMIC_YEAR], 
            [ACADEMIC].[ACADEMIC_TERM], 
            [ACADEMIC].[ADMIT_YEAR],
            [ACADEMIC].[ADMIT_TERM], 
            [ACADEMIC].[APP_STATUS_DATE], 
            [ACADEMIC].[APP_STATUS]
        ORDER BY 
            [ACADEMIC].[APP_STATUS_DATE]
        """
        df_dep = pd.read_sql_query(sql_str, connection)
        df_dep['yearterm_sort'] = df_dep.apply(yearterm_sort, axis=1)
        df_dep['yearterm'] = df_dep['ACADEMIC_YEAR'] + '.' +  df_dep['ACADEMIC_TERM'].str.title()
        df_dep = df_dep.sort_values(['yearterm_sort', 'DEGREE', 'CURRICULUM', 'PEOPLE_CODE_ID' ])

        df = (
            df_dep.loc[(df_dep['yearterm'].isin(yearterm_list)), 
            ['yearterm_sort', 'yearterm', 'DEGREE', 'CURRICULUM', 'PEOPLE_CODE_ID']]
            .groupby(['yearterm_sort', 'yearterm', 'DEGREE', 'CURRICULUM', ])
            .count()
            .reset_index()
            .rename(columns={'PEOPLE_CODE_ID': 'count', 'CURRICULUM': 'program'})
            .sort_values(['yearterm_sort', 'program'])
            .astype({'count': 'UInt16'})
        )

        program_deposits = pd.pivot(
            df,
            values='count',
            index=['program'],
            columns=['yearterm'],
        )[yearterm_list]

        st.dataframe(program_deposits)

        csv = convert_df(program_deposits)

        st.download_button(
            label="Download data as CSV",
            data=csv,
            file_name=f'{today_str}_program_deposits.csv',
            mime='text/csv',
        )

        st.markdown("---")

        program_deposits_total = (
            df.groupby(['yearterm_sort', 'yearterm', ])
            .sum()
            .reset_index()
            .rename(columns={'count': 'deposits', })
            .drop(columns=['yearterm_sort'])
            .astype({'deposits': 'UInt16'})
        )
        st.markdown("### Total Deposits")
        st.dataframe(program_deposits_total)

        c = alt.Chart(df).mark_bar().encode(
            x='yearterm:N',
            y=alt.Y('sum(count):Q', axis=alt.Axis(title='deposits')),
            # color=alt.Color('program:N', legend=alt.Legend(title="program")),
            # tooltip=['yearterm', 'program', alt.Tooltip('sum(count):Q', title='deposits')],
        )

        st.altair_chart(c)
