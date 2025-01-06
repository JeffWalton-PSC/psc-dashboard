import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path
import src.pages.components


begin_year = '2017'

@st.cache_data
def convert_df(df):
    return df.to_csv().encode('utf-8')


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading College Enrollment - Class Level ..."):
        src.pages.components.logo()
        st.write(
            """
            ## College Enrollment - Class Level
           
"""
        )

        data_path = Path(r"F:\Data\Census\CensusDatabase")
        data_file = data_path / "census_db.arr"

        df = (
            pd.read_feather(data_file)
            .sort_values(['yearterm_sort', 'people_code_id'])
        )

        term_list = df['current_yearterm'].unique()
        term_list = [t for t in term_list if ("Fall" in t) and (t >= begin_year)]  # remove restrictions after cleaning CLASS_LEVEL data
        terms = st.multiselect(
            'Select term(s):',
            options=term_list,
            default=term_list,
            )
        # order terms
        terms = [t for t in term_list if t in terms]

        class_level_sort = ['FRES', 'SOPH', 'JUN', 'SEN', 'GRAD', ]
        class_level_sort_dict = {value: order for order, value in enumerate(class_level_sort)}
        # st.write(class_level_sort_dict)
        class_level_sorter = lambda x: x.map(class_level_sort_dict).fillna(x)

        if terms:
            selected_df = (
                df.loc[(df['current_yearterm'].isin(terms)), 
                ['current_yearterm', 'yearterm_sort', 'CLASS_LEVEL', 'people_code_id']]
                .groupby(['yearterm_sort', 'current_yearterm', 'CLASS_LEVEL'])
                .count()
                .reset_index()
                .rename(columns={'people_code_id': 'count', 'current_yearterm': 'yearterm', 'CLASS_LEVEL': 'class_level'})
                .sort_values(['yearterm_sort', 'class_level'])
                .astype({'count': 'UInt16'})
            )

            enrollment = pd.pivot(
                selected_df,
                values='count',
                index=['class_level'],
                columns=['yearterm'],
            )[terms]
            enrollment = enrollment.fillna(0)
            enrollment = enrollment.sort_values('class_level', key=class_level_sorter)

            st.dataframe(enrollment)

            st.download_button(
                label="Download data as CSV",
                data=convert_df(enrollment),
                file_name=f'college_enrollment_class_level.csv',
                mime='text/csv',
            )

            color_class_level_sort = list(reversed(class_level_sort))
            
            col1, col2 = st.columns(2)

            c1 = alt.Chart(selected_df).transform_joinaggregate(
                total='sum(count)',
                groupby=['yearterm']  
            ).transform_calculate(
                order=f"indexof({class_level_sort}, datum.class_level)"
                ).mark_bar().encode(
                    x=alt.X('yearterm:N', sort=terms),
                    y=alt.Y('sum(count):Q', axis=alt.Axis(title='number of students')),
                    color=alt.Color('class_level:N', sort=color_class_level_sort),
                    tooltip=['yearterm', 
                        'class_level',
                        alt.Tooltip('sum(count):Q', title='students'),
                        alt.Tooltip('total:Q', title='total')
                        ],
                    order='order:Q'
                )
            with col1:
                st.altair_chart(c1)
            
            c2 = alt.Chart(selected_df).transform_aggregate(
                c='sum(count)',
                groupby=['yearterm', 'class_level']
            ).transform_joinaggregate(
                total='sum(c)',
                groupby=['yearterm']  
            ).transform_calculate(
                frac=alt.datum.c / alt.datum.total
            ).transform_calculate(
                order=f"indexof({class_level_sort}, datum.class_level)"
            ).mark_bar().encode(
                x=alt.X('yearterm:N', sort=terms),
                y=alt.Y('c:Q', stack="normalize", axis=alt.Axis(format='.0%', title='percent')),
                color=alt.Color('class_level:N', sort=color_class_level_sort),
                tooltip=['yearterm', 'class_level', 
                    alt.Tooltip('c:Q', title='students'),
                    alt.Tooltip('total:Q', title='total'),
                    alt.Tooltip('frac:Q', title='percent of students', format='.1%')],
                order='order:Q'
            )
            with col2:
                st.altair_chart(c2)
