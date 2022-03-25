import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path
import src.pages.components


@st.cache
def convert_df(df):
    return df.to_csv().encode('utf-8')


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading College Enrollment - Attend Status ..."):
        src.pages.components.logo()
        st.write(
            """
            ## College Enrollment - Attend Status
           
"""
        )

        data_path = Path(r"\\psc-data\E\Data\Census\CensusDatabase")
        data_file = data_path / "census_db.arr"

        df = (
            pd.read_feather(data_file)
            .sort_values(['yearterm_sort', 'people_code_id'])
        )

        term_list = df['current_yearterm'].unique()
        term_list = [t for t in term_list if ("Fall" in t) and (t > '2019')]  # remove restrictions after cleaning COLLEGE_ATTEND data
        terms = st.multiselect(
            'Select term(s):',
            options=term_list,
            default=term_list,
            )
        # order terms
        terms = [t for t in term_list if t in terms]

        if terms:
            selected_df = (
                df.loc[(df['current_yearterm'].isin(terms)), 
                ['current_yearterm', 'yearterm_sort', 'COLLEGE_ATTEND', 'people_code_id']]
                .groupby(['yearterm_sort', 'current_yearterm', 'COLLEGE_ATTEND'])
                .count()
                .reset_index()
                .rename(columns={'people_code_id': 'count', 'current_yearterm': 'yearterm', 'COLLEGE_ATTEND': 'attend_status'})
                .sort_values(['yearterm_sort', 'attend_status'])
                .astype({'count': 'UInt16'})
            )

            enrollment = pd.pivot(
                selected_df,
                values='count',
                index=['attend_status'],
                columns=['yearterm'],
            )[terms]
            enrollment = enrollment.fillna(0)

            st.dataframe(enrollment)

            st.download_button(
                label="Download data as CSV",
                data=convert_df(enrollment),
                file_name=f'college_enrollment_attend_status.csv',
                mime='text/csv',
            )

            col1, col2 = st.columns(2)

            c1 = alt.Chart(selected_df).transform_joinaggregate(
                total='sum(count)',
                groupby=['yearterm']  
            ).mark_bar().encode(
                x=alt.X('yearterm:N', sort=terms),
                y=alt.Y('sum(count):Q', axis=alt.Axis(title='number of students')),
                color='attend_status:N',
                tooltip=['yearterm',
                    'attend_status',
                    alt.Tooltip('sum(count):Q', title='students'),
                    alt.Tooltip('total:Q', title='total')
                    ],
            )
            with col1:
                st.altair_chart(c1)
            
            c2 = alt.Chart(selected_df).transform_aggregate(
                c='sum(count)',
                groupby=['yearterm', 'attend_status']
            ).transform_joinaggregate(
                total='sum(c)',
                groupby=['yearterm']  
            ).transform_calculate(
                frac=alt.datum.c / alt.datum.total
            ).mark_bar().encode(
                x=alt.X('yearterm:N', sort=terms),
                y=alt.Y('c:Q', stack="normalize", axis=alt.Axis(format='.0%', title='percent')),
                color='attend_status:N',
                tooltip=['yearterm', 'attend_status', 
                    alt.Tooltip('c:Q', title='students'),
                    alt.Tooltip('total:Q', title='total'),
                    alt.Tooltip('frac:Q', title='percent of students', format='.1%')],
            )
            with col2:
                st.altair_chart(c2)
