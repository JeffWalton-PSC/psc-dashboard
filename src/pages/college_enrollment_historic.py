import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path
import src.pages.components

# PowerCampus utilities
import powercampus as pc


@st.cache
def convert_df(df):
    return df.to_csv().encode('utf-8')


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading College Enrollment - Historic ..."):
        src.pages.components.logo()
        st.write(
            """
            ## College Enrollment - Historic
           
"""
        )

        data_path = Path(r"\\psc-data\E\Data\Census\enrollment")
        data_file = data_path / "RUNENROLL.xlsx"

        df = pd.read_excel(data_file)
        df['ACADEMIC_YEAR'] = df['term_year'].str.split(expand=True)[1]
        df['ACADEMIC_TERM'] = df['term_year'].str.split(expand=True)[0]
        df = pc.add_col_yearterm(df)
        df = pc.add_col_yearterm_sort(df)
        df = df.sort_values('yearterm_sort').reset_index()
        # df = df.fillna(0)
        df['as_total'] = df['as_new'].fillna(0) + df['as_return'].fillna(0)
        df['bs_total'] = df['bs_new'].fillna(0) + df['bs_return'].fillna(0)
        df['ms_total'] = df['ms_total'].fillna(0)
        df['total_headcount'] = df['as_total'] + df['bs_total'] + df['ms_total']
        df['total_headcount'] = df['total_headcount'].astype('int')
        # st.dataframe(df)

        term_filter = st.selectbox(
            'Term filter:',
            options=['Both Fall and Spring', 'Fall Only', 'Spring Only'],
            index=0,
        )

        term_list = df['yearterm'].unique()
        if term_filter == 'Fall Only':
            term_list = [t for t in term_list if 'Fall' in t]
        elif term_filter == 'Spring Only':
            term_list = [t for t in term_list if 'Spring' in t]

        terms = st.multiselect(
            'Select term(s):',
            options=term_list,
            default=term_list,
            )
        terms = [t for t in term_list if t in terms]
        # st.write(terms)

        if terms:
            enrollment = (
                df.loc[(df['yearterm'].isin(terms)), 
                ['yearterm', 'yearterm_sort', 'as_total', 'bs_total', 'ms_total', 'total_headcount']]
                # .reset_index()
                .rename(columns={'as_total': 'Assoc', 'bs_total': 'Bach', 'ms_total': 'Mast'})
                .sort_values(['yearterm_sort',])
                .astype({'Assoc': 'UInt16', 'Bach': 'UInt16', 'Mast': 'UInt16'})
            )

            # enrollment = selected_df[['yearterm', 'count']]
            # enrollment = enrollment.fillna(0)

            st.dataframe(enrollment)

            st.download_button(
                label="Download data as CSV",
                data=convert_df(enrollment),
                file_name=f'college_enrollment_historic.csv',
                mime='text/csv',
            )

            # col1, col2 = st.columns(2)

            degree_order = ['Assoc', 'Bach', 'Mast']
            degree_color_order = list(reversed(degree_order))

            c1 = alt.Chart(enrollment).transform_fold(
                degree_order,
                as_=['degree', 'students']
            ).transform_calculate(
                order=f"indexof({degree_order}, datum.degree)"
            ).mark_bar().encode(
                x=alt.X('yearterm:N', sort=terms),
                y=alt.Y('students:Q', axis=alt.Axis(title='number of students')),
                color=alt.Color('degree:N', sort=degree_color_order),
                tooltip=['yearterm', 
                    alt.Tooltip('students:Q', title='students'),
                    alt.Tooltip('degree:N', title='degree'),
                    alt.Tooltip('total_headcount:Q', title='total'),
                    ],
                order='order:Q'
            )

            st.altair_chart(c1)
            
