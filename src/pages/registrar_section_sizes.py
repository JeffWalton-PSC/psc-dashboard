import pandas as pd
import streamlit as st
import altair as alt
import datetime as dt
import src.pages.components

# PowerCampus utilities
import powercampus as pc

@st.cache
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

start_year = pc.START_ACADEMIC_YEAR

current_yt_df = pc.current_yearterm()
current_term = current_yt_df['term'].iloc[0]
current_year = current_yt_df['year'].iloc[0]
current_yt = current_yt_df['yearterm'].iloc[0]
current_yt_sort = current_yt_df['yearterm_sort'].iloc[0]


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Registrar - Section Sizes ..."):
        src.pages.components.logo()
        st.write(
            """
            ## Registrar - Section Sizes
"""
        )

        today = dt.datetime.today()
        today_str = today.strftime("%Y%m%d_%H%M")
        # st.write(f"{today.strftime('%Y-%m-%d %H:%M')}")

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
        year_start, year_end = st.select_slider(
            "Select range of years:",
            options=year_list,
            value=('2012', current_year)
        )

        term = st.selectbox(label="Select term:", options=['Fall', 'Spring'])

        undergrad_only = st.checkbox("Undergrad sections only", value=True )
        exclude_online = st.checkbox("Exclude online sections", value=True )

        section_types = ['COMB', 'HYBD', 'LEC', 'PRAC', 'LAB', 'SI']
        include_section_types = st.multiselect("Include section types:", options=section_types, default=['COMB', 'HYBD', 'LEC', 'PRAC'])

        if year_start and year_end and term and include_section_types:

            sections = pc.select("SECTIONS", 
                fields=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',
                    'EVENT_LONG_NAME', 'PROGRAM', 'COLLEGE', 'EVENT_STATUS', 'CREDITS', 'MAX_PARTICIPANT', 'ADDS', 'WAIT_LIST', 
                    'START_DATE', 'END_DATE'],
                where=f"ACADEMIC_YEAR>='{int(year_start)}' and ACADEMIC_YEAR<='{int(year_end)}' and ACADEMIC_TERM='{term}' " +
                    "and ADDS>0 and EVENT_STATUS='A' ", 
                )
            sections = sections.loc[(~sections['EVENT_ID'].str.startswith('REG')) & (~sections['EVENT_SUB_TYPE'].isin(['ACE', 'ADV', 'CELL', 'STAB'])), :]
            sections = sections.drop_duplicates(['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION'])
            sections = sections.sort_values(['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION'])
            sections['section_id'] = (
                sections["EVENT_ID"].str.rstrip().str.upper() + "." + 
                sections["EVENT_SUB_TYPE"].str.upper() + "."  + 
                sections["SECTION"].str.upper()
                )
            sections['yearterm'] = sections["ACADEMIC_YEAR"] + "." + sections["ACADEMIC_TERM"].str.title()
            if undergrad_only:
                sections = sections.loc[(sections['PROGRAM'] != 'G')]
            if exclude_online:
                sections = sections.loc[(~sections['SECTION'].str.contains('ON'))]
            sections = sections.loc[(sections['EVENT_SUB_TYPE'].isin(include_section_types))]

            st.write(f"#### Section Sizes ({term} {year_start}-{year_end})")
            agg_ss = ( sections[['yearterm', 'section_id', 'ADDS']].groupby(['yearterm']).agg(
                    {'ADDS': ['count', 'min', 'median', 'mean', 'max']}
                    )
                    .droplevel(0, axis=1)
                    .sort_index()
                    .rename(
                        columns={
                            'count': 'sections'
                        },
                        index={
                            1:'yearterm'
                        }
                    )
            )
            st.dataframe(agg_ss)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(agg_ss),
                file_name=f"{term}_{year_start}-{year_end}_section_sizes.csv",
                mime='text/csv',
            )

            c = alt.Chart(agg_ss.reset_index()).mark_bar().encode(
                x='yearterm:N',
                y=alt.Y('mean:Q', axis=alt.Axis(title='mean section size')),
                tooltip=['yearterm:N', alt.Tooltip('mean:Q', title='mean section size', format='.3')],
            )
            st.altair_chart(c)

            st.write(f"#### Section Size Bins ({term} {year_start}-{year_end})")
            bins=[0, 2, 9, 19, 29, 39, 49, 99, 1000]
            labels=['1', '2-9', '10-19', '20-29', '30-39', '40-49', '50-99', '100-999']
            sections['size_bin'] = pd.cut(sections['ADDS'], 
                                            bins=bins,
                                            labels=labels,
                                            )
            ss = sections[['yearterm', 'section_id', 'size_bin']].groupby(['yearterm', 'size_bin']).count()
            ss = ( ss.reset_index()
                .rename(
                    columns={
                        'section_id': 'count'
                    },
                )
            )

            ssb = ss.pivot(
                index='yearterm', 
                columns='size_bin',
                values='count'
            ).reset_index()

            # st.dataframe(ss)
            st.dataframe(ssb)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(ssb),
                file_name=f"{term}_{year_start}-{year_end}_section_size_bins.csv",
                mime='text/csv',
            )

            # c = alt.Chart(ss).mark_bar().encode(
            #     x='yearterm:N',
            #     y=alt.Y('sum(count):Q', axis=alt.Axis(title='number of sections')),
            #     color='yearterm:N',
            #     column=alt.Column(shorthand='size_bin:N',sort=labels),
            #     tooltip=['size_bin', 'yearterm', alt.Tooltip('sum(count):Q', title='sections')],
            # )
            # st.altair_chart(c)

            c1 = alt.Chart(ss).transform_joinaggregate(
                    YearTermCount='sum(count)',
                    groupby=['yearterm']
                ).transform_calculate(
                    PercentOfTotal="datum.count / datum.YearTermCount",
                ).mark_bar().encode(
                x='yearterm:N',
                y=alt.Y('PercentOfTotal:Q', axis=alt.Axis(title='percent of yearterm sections', format='.0%')),
                color='yearterm:N',
                column=alt.Column(shorthand='size_bin:N',sort=labels),
                tooltip=['size_bin', 'yearterm', alt.Tooltip('sum(count):Q', title='sections'), alt.Tooltip('PercentOfTotal:Q', title='pct of yearterm', format='.3p')],
            )
            st.altair_chart(c1)

