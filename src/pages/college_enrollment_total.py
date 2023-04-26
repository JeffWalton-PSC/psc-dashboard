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
    with st.spinner("Loading College Enrollment - Total ..."):
        src.pages.components.logo()
        st.write(
            """
            ## College Enrollment - Total
           
"""
        )

        data_path = Path(r"F:\Data\Census\CensusDatabase")
        data_file = data_path / "census_db.arr"

        df = (
            pd.read_feather(data_file)
            .sort_values(['yearterm_sort', 'people_code_id'])
        )


        term_list = df['current_yearterm'].unique()
        terms = st.multiselect(
            'Select term(s):',
            options=term_list,
            default=term_list,
            )
        terms = [t for t in term_list if t in terms]

        if terms:
            selected_df = (
                df.loc[(df['current_yearterm'].isin(terms)), 
                ['current_yearterm', 'yearterm_sort', 'people_code_id']]
                .groupby(['yearterm_sort', 'current_yearterm'])
                .count()
                .reset_index()
                .rename(columns={'people_code_id': 'count', 'current_yearterm': 'yearterm'})
                .sort_values(['yearterm_sort',])
                .astype({'count': 'UInt16'})
            )

            enrollment = selected_df[['yearterm', 'count']]
            enrollment = enrollment.fillna(0)

            st.dataframe(enrollment)

            st.download_button(
                label="Download data as CSV",
                data=convert_df(enrollment),
                file_name=f'college_enrollment_total.csv',
                mime='text/csv',
            )

            col1, col2 = st.columns(2)

            c1 = alt.Chart(selected_df).mark_bar().encode(
                x=alt.X('yearterm:N', sort=terms),
                y=alt.Y('sum(count):Q', axis=alt.Axis(title='number of students')),
                tooltip=['yearterm', alt.Tooltip('sum(count):Q', title='students')],
            )
            with col1:
                st.altair_chart(c1)
            
            
