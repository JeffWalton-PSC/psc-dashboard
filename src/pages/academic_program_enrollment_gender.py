import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path
from streamlit import cli as stcli
import src.pages.components


@st.cache
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Academic Program Enrollment - Gender ..."):
        src.pages.components.logo()
        st.write(
            """
            ## Academic Program Enrollment - Gender
            Select the academic program and term(s) you would like to see.
"""
        )

        data_path = Path(r"\\psc-data\E\Data\Census\CensusDatabase")
        data_file = data_path / "census_db.arr"

        df = (
            pd.read_feather(data_file)
            .sort_values(['yearterm_sort', 'curriculum', 'gender', 'people_code_id'])
        )

        program_list = sorted(df['curriculum'].unique())
        program = st.selectbox(
            'Select academic program:',
            options=program_list,
            index=0,
            )

        term_list = df.loc[(df['curriculum']==program), :]['current_yearterm'].unique()
        terms = st.multiselect(
            'Select term(s):',
            options=term_list,
            default=[t for t in term_list if "Fall" in t],
            )
        # order terms
        terms = [t for t in term_list if t in terms]

        if program and terms:
            selected_df = (
                df.loc[(df['curriculum']==program) & (df['current_yearterm'].isin(terms)), 
                ['current_yearterm', 'yearterm_sort', 'curriculum', 'gender', 'people_code_id']]
                .groupby(['yearterm_sort', 'current_yearterm', 'curriculum', 'gender'])
                .count()
                .reset_index()
                .rename(columns={'people_code_id': 'count', 'current_yearterm': 'yearterm', 'curriculum': 'program'})
                .sort_values(['yearterm_sort', 'program', 'gender'])
                .astype({'count': 'UInt16'})
            )

            program_enrollment = pd.pivot(
                selected_df,
                values='count',
                index=['program', 'gender'],
                columns=['yearterm'],
            )[terms]

            st.dataframe(program_enrollment)

            csv = convert_df(program_enrollment)

            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name=f'{program}_academic_program_enrollment_gender.csv',
                mime='text/csv',
            )

            col1, col2 = st.columns(2)

            c1 = alt.Chart(selected_df).mark_bar().encode(
                x='yearterm:N',
                y=alt.Y('sum(count):Q', axis=alt.Axis(title='number of students')),
                color='gender:N',
                column='program:N',
                tooltip=['program', 'yearterm', 'gender', alt.Tooltip('sum(count):Q', title='students')],
            )
            with col1:
                st.altair_chart(c1)
            
            c2 = alt.Chart(selected_df).transform_aggregate(
                c='sum(count)',
                groupby=['program', 'yearterm', 'gender']
            ).transform_joinaggregate(
                total='sum(c)',
                groupby=['program', 'yearterm']  
            ).transform_calculate(
                frac=alt.datum.c / alt.datum.total
            ).mark_bar().encode(
                x='yearterm:N',
                y=alt.Y('c:Q', stack="normalize", axis=alt.Axis(format='%', title='percent')),
                color='gender:N',
                column='program:N',
                tooltip=['program', 'yearterm', 'gender', 
                    alt.Tooltip('c:Q', title='total students'),
                    alt.Tooltip('frac:Q', title='percent of students', format='.0%')],
            )
            with col2:
                st.altair_chart(c2)
