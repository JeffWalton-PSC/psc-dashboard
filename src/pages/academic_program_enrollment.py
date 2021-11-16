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
    with st.spinner("Loading Home ..."):
        src.pages.components.logo()
        st.write(
            """
            ## Academic Program Enrollment
            Select the academic program(s) and term(s) you would like to see.
"""
        )

        # data_path = Path(r"E:\Data\Census\CensusDatabase")
        data_path = Path(r"C:\JW\IR\Python\census")
        data_file = data_path / "census_db.arr"

        df = (
            pd.read_feather(data_file)
            .sort_values(['yearterm_sort', 'curriculum', 'people_code_id'])
        )

        program_list = sorted(df['curriculum'].unique())
        programs = st.multiselect(
            'Select academic program(s):',
            options=program_list,
            default=program_list,
            )

        term_list = df.loc[(df['curriculum'].isin(programs)), :]['current_yearterm'].unique()
        terms = st.multiselect(
            'Select term(s):',
            options=term_list,
            default=[t for t in term_list if "Fall" in t],
            )
        # order terms
        terms = [t for t in term_list if t in terms]

        if programs and terms:
            selected_df = (
                df.loc[(df['curriculum'].isin(programs)) & (df['current_yearterm'].isin(terms)), 
                ['current_yearterm', 'yearterm_sort', 'curriculum', 'people_code_id']]
                .groupby(['yearterm_sort', 'current_yearterm', 'curriculum'])
                .count()
                .reset_index()
                .rename(columns={'people_code_id': 'count', 'current_yearterm': 'yearterm', 'curriculum': 'program'})
                .sort_values(['yearterm_sort', 'program'])
                .astype({'count': 'UInt16'})
            )

            program_enrollment = pd.pivot(
                selected_df,
                values='count',
                index=['program'],
                columns=['yearterm'],
            )[terms]

            st.dataframe(program_enrollment)

            csv = convert_df(program_enrollment)

            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name='academic_program_enrollment.csv',
                mime='text/csv',
            )

            c = alt.Chart(selected_df).mark_bar().encode(
                x='yearterm:N',
                y='sum(count):Q',
                color='yearterm:N',
                column='program:N'
            )

            st.altair_chart(c)
