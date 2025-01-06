# from click import style
# import numpy as np
import pandas as pd
import streamlit as st
import altair as alt
from pathlib import Path
import src.pages.components

# PowerCampus utilities
import powercampus as pc

start_year = '2010-11'

@st.cache_data
def convert_df(df):
    return df.to_csv().encode('utf-8')


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading College Enrollment - Attrition ..."):
        src.pages.components.logo()
        st.write(
            """
            ## College Enrollment - Attrition
            ##### Attrition includes withdrawals, LEOS (Leave at End Of Semester), and net suspensions.           
"""
        )

        data_path = Path(r"F:\Data\Census\attrition")
        data_file = data_path / "net_attrition.csv"

        df = pd.read_csv(data_file)
        # st.dataframe(df)

        df['ay'] = df['ay'].astype('string')
        ay_list = df['ay'].unique().tolist()
        ay_start, ay_end = st.select_slider(
            "Select range of academic years:",
            options=ay_list,
            value=(start_year, ay_list[-1])
        )

        if ay_start and ay_end:
            df_1 = (
                df.loc[((df['ay'] >= ay_start) & (df['ay'] <= ay_end)), 
                ['ay', 'net_attrition_fall', 'pct_attrition_fall', 
                'net_attrition_spring', 'pct_attrition_spring', 
                'net_attrition_total', 'pct_attrition_total',
                ]]
                # .reset_index()
                .astype({'net_attrition_fall': 'UInt16', 'net_attrition_spring': 'UInt16',
                    'net_attrition_total': 'UInt16'})
                .rename(columns={'net_attrition_fall': 'Fall', 'net_attrition_spring': 'Spring', 
                            'net_attrition_total': 'Total',
                            'pct_attrition_fall': 'pct_Fall', 'pct_attrition_spring': 'pct_Spring', 
                            'pct_attrition_total': 'pct_Total',
                            })
                .sort_values(['ay',])
            )

            st.dataframe(df_1)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df_1),
                file_name=f'college_enrollment_attrition.csv',
                mime='text/csv',
            )

            col1, col2 = st.columns(2)

            term_order = ['Fall', 'Spring']
            term_color_order = list(reversed(term_order))

            c1 = alt.Chart(df_1).transform_fold(
                    term_order,
                    as_=['term', 'students']
                ).transform_calculate(
                    order=f"indexof({term_order}, datum.term)"
                ).mark_bar().encode(
                    x=alt.X('ay:N', title='academic year'),
                    y=alt.Y('students:Q', axis=alt.Axis(title='number of students')),
                    color=alt.Color('term:N', sort=term_color_order),
                    tooltip=['ay', 
                        alt.Tooltip('term:N', title='term'),
                        alt.Tooltip('students:Q', title='students'),
                        alt.Tooltip('Total:Q', title='total'),
                        ],
                    order='order:Q'
                )
            with col1:
                st.altair_chart(c1)

            term_order = ['pct_Fall', 'pct_Spring']
            term_color_order = list(reversed(term_order))

            c2 = alt.Chart(df_1).transform_fold(
                    term_order,
                    as_=['term', 'percent']
                ).transform_calculate(
                    order=f"indexof({term_order}, datum.term)"
                ).mark_bar().encode(
                    x=alt.X('ay:N', title='academic year'),
                    y=alt.Y('percent:Q', axis=alt.Axis(format='.0%', title='percent of students')),
                    color=alt.Color('term:N', sort=term_color_order),
                    tooltip=['ay', 
                        alt.Tooltip('term:N', title='term'),
                        alt.Tooltip('percent:Q', title='percent', format='.1%'),
                        alt.Tooltip('pct_Total:Q', title='pct_total', format='.1%'),
                        ],
                    order='order:Q'
                )
            with col2:
                st.altair_chart(c2)

            df_2 = df_1.loc[:,['ay', 'pct_Total']]
            df_2['ay'] = df_2['ay'].str.slice(stop=4).astype('UInt16')
            c3 = alt.Chart(df_2).mark_line(
                    point=alt.OverlayMarkDef(shape='diamond')
                ).encode(
                    x=alt.X('ay:N', title='academic year', ),
                    y=alt.Y('pct_Total:Q', axis=alt.Axis(format='.0%', title='total attrition')),
                    tooltip=[ 
                        alt.Tooltip('ay:N', title='academic year'),
                        alt.Tooltip('pct_Total:Q', title='total attrition', format='.1%'),
                        ],
                )
            fit = c3.transform_regression(
                    'ay', 'pct_Total', method='linear', as_=['ay', 'linear']
                ).mark_line(
                    # point=alt.OverlayMarkDef(shape='circle', size=10),
                    opacity=0.5
                ).transform_fold(
                    ['linear'],
                    as_=['trendline', 'pct_Total']
                ).encode(
                    color=alt.Color('trendline:N', scale=alt.Scale(range=['red'])),
                    tooltip=[ 
                        alt.Tooltip('ay:N', title='academic year'),
                        alt.Tooltip('pct_Total:Q', title='total attrition', format='.1%'),
                        ],
                )
            fit_params = alt.Chart(df_2).transform_regression(
                    'ay', 'pct_Total', method='linear', as_=['ay', 'linear'], params=True,
                ).mark_text(align='left'
                ).transform_calculate(
                    slope='round(datum.coef[1] * 10000)/100'
                ).encode(
                    x=alt.value(10),
                    y=alt.value(10),
                    text=alt.Text('slope:N', title='slope'),
                    tooltip=[
                        alt.Tooltip('slope:N', title='trendline slope (%/yr)')
                    ]
                )
            st.altair_chart(
                alt.layer(c3, fit, fit_params),
                use_container_width=True
                )

