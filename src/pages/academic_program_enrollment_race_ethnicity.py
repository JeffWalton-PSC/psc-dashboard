import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path
import src.pages.components


# begin_year = '2014'

@st.cache_data
def convert_df(df):
    # IMPORTANT: Cache the conversion to prevent computation on every rerun
    return df.to_csv().encode('utf-8')


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Academic Program Enrollment - Race/Ethnicity ..."):
        src.pages.components.page_header()
        st.write(
            """
            ## Academic Program Enrollment - Race/Ethnicity
            Select the academic program and term(s) you would like to see.
"""
        )

        data_path = Path(r"F:\Data\Census\CensusDatabase")
        data_file = data_path / "census_db.arr"

        df = (
            pd.read_feather(data_file)
            .sort_values(['yearterm_sort', 'curriculum', 'updated_ethnicity_code', 'people_code_id'])
        )
        df.loc[df['curriculum']=='', 'curriculum']='UNDM'
        df['curriculum'] = df['curriculum'].fillna('UNDM')
        df.loc[df['updated_ethnicity_code']=='', 'updated_ethnicity_code']='U'
        df['updated_ethnicity_code'] = df['updated_ethnicity_code'].fillna('U')

        program_list = sorted(list(df['curriculum'].unique()))
        program = st.selectbox(
            'Select academic program:',
            options=program_list,
            index=0,
            )

        term_list = df.loc[(df['curriculum']==program), :]['current_yearterm'].unique()
        # term_list = [t for t in term_list if ("Fall" in t) and (t >= begin_year)]  # remove restrictions after cleaning data
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
                ['current_yearterm', 'yearterm_sort', 'curriculum', 'updated_ethnicity_code', 'people_code_id']]
                .groupby(['yearterm_sort', 'current_yearterm', 'curriculum', 'updated_ethnicity_code'])
                .count()
                .reset_index()
                .rename(columns={'people_code_id': 'count', 'current_yearterm': 'yearterm', 'curriculum': 'program'})
                .sort_values(['yearterm_sort', 'program', 'updated_ethnicity_code'])
                .astype({'count': 'UInt16'})
            )

            program_enrollment = pd.pivot(
                selected_df,
                values='count',
                index=['program', 'updated_ethnicity_code'],
                columns=['yearterm'],
            )[terms]
            program_enrollment = program_enrollment.fillna(0)

            st.dataframe(program_enrollment)

            st.download_button(
                label="Download data as CSV",
                data=convert_df(program_enrollment),
                file_name=f'{program}_academic_program_enrollment_race_ethnicity.csv',
                mime='text/csv',
            )

            col1, col2 = st.columns(2)

            c1 = alt.Chart(selected_df).transform_joinaggregate(
                total='sum(count)',
                groupby=['yearterm']  
            ).mark_bar().encode(
                x=alt.X('yearterm:N', sort=terms),
                y=alt.Y('sum(count):Q', axis=alt.Axis(title='number of students')),
                color=alt.Color('updated_ethnicity_code:N', legend=alt.Legend(title="Race/Ethnicity")),
                column='program:N',
                tooltip=['program',
                    'yearterm', 
                    'updated_ethnicity_code',
                    alt.Tooltip('sum(count):Q', title='students'),
                    alt.Tooltip('total:Q', title='total')
                    ],
            )
            with col1:
                st.altair_chart(c1)
            
            c2 = alt.Chart(selected_df).transform_aggregate(
                c='sum(count)',
                groupby=['program', 'yearterm', 'updated_ethnicity_code']
            ).transform_joinaggregate(
                total='sum(c)',
                groupby=['program', 'yearterm']  
            ).transform_calculate(
                frac=alt.datum.c / alt.datum.total
            ).mark_bar().encode(
                x=alt.X('yearterm:N', sort=terms),
                y=alt.Y('c:Q', stack="normalize", axis=alt.Axis(format='.0%', title='percent')),
                color=alt.Color('updated_ethnicity_code:N', legend=alt.Legend(title="Race/Ethnicity")),
                column='program:N',
                tooltip=['program', 'yearterm', 'updated_ethnicity_code', 
                    alt.Tooltip('c:Q', title='students'),
                    alt.Tooltip('total:Q', title='total'),
                    alt.Tooltip('frac:Q', title='percent of students', format='.1%')],
            )

            with col2:
                st.altair_chart(c2)
