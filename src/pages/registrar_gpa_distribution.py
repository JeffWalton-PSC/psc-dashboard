import pandas as pd
import streamlit as st
import altair as alt
import datetime as dt
import src.pages.components

# PowerCampus utilities
import powercampus as pc

@st.cache_data
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
    with st.spinner("Loading Registrar - GPA Distribution ..."):
        src.pages.components.page_header()
        st.write(
            """
            ## Registrar - GPA Distribution
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
        gpa_type = st.selectbox(label="Select GPA type:", options=['Cumulative', 'Term'])

        undergrad_only = st.checkbox("Undergraduate students only", value=True )

        if year_start and year_end and term and gpa_type:

            academic = pc.select("ACADEMIC",
                fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION',
                    'PROGRAM', 'DEGREE', 'CURRICULUM', 'COLLEGE', 'DEPARTMENT', 'CLASS_LEVEL', 'POPULATION',
                    'FULL_PART', 'ACADEMIC_STANDING', 'ENROLL_SEPARATION', 'SEPARATION_DATE', 'CREDITS',  
                    'COLLEGE_ATTEND', 'STATUS', 'PRIMARY_FLAG',
                    ],
                where=f"ACADEMIC_YEAR>='{int(year_start)}' and ACADEMIC_YEAR<='{int(year_end)}' and ACADEMIC_TERM='{term}' " +
                    "and ACADEMIC_SESSION='' and CREDITS>0 and CURRICULUM<>'ADVST' and PRIMARY_FLAG='Y' ", 
            )
            if undergrad_only:
                academic = academic.loc[(academic['PROGRAM'] != 'G')]
            keep_cols = [
                'PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM',
            ]
            academic = academic.loc[:, keep_cols]
            academic = academic.drop_duplicates(keep_cols)
            academic = academic.sort_values(keep_cols)
            # st.write(academic.shape)
            # st.dataframe(academic)

            transcript_gpa = pc.select("TRANSCRIPTGPA",
                fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'RECORD_TYPE', 'GPA', 'ATTEMPTED_CREDITS',],
                where=f"ACADEMIC_YEAR>='{int(year_start)}' and ACADEMIC_YEAR<='{int(year_end)}' and ACADEMIC_TERM='{term}' " +
                    "and ACADEMIC_SESSION='' and ATTEMPTED_CREDITS>0.0 ", 
                )
            if gpa_type == 'Cumulative':
                transcript_gpa = transcript_gpa.loc[(transcript_gpa['RECORD_TYPE'] == 'O')]
            else:
                transcript_gpa = transcript_gpa.loc[(transcript_gpa['RECORD_TYPE'] == 'T')]
            keep_cols = [
                'PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'GPA', 
            ]
            transcript_gpa = transcript_gpa.loc[:, keep_cols]
            transcript_gpa = transcript_gpa.drop_duplicates(keep_cols)
            transcript_gpa = transcript_gpa.sort_values(keep_cols)
            # st.write(transcript_gpa.shape)
            # st.dataframe(transcript_gpa)
 
            atgpa = academic.merge(transcript_gpa,
                how='left',
                on=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', ]
                )
            atgpa = pc.add_col_yearterm(atgpa)
            atgpa = pc.add_col_yearterm_sort(atgpa)
            # st.write(atgpa.shape)
            # st.dataframe(atgpa)

            st.write(f"#### GPA Statistics ({term} {year_start}-{year_end})")
            agg_ytgpa = ( atgpa[['yearterm', 'GPA']].groupby(['yearterm']).agg(
                    {'GPA': ['count', 'min', 'median', 'mean', 'max']}
                    )
                    .droplevel(0, axis=1)
                    .sort_index()
                    .rename(
                        columns={
                            'count': 'students'
                        },
                        index={
                            1:'yearterm'
                        }
                    )
            )
            formatted_agg_ytgpa = agg_ytgpa.style.format({
                'min': '{:.2f}',
                'median': '{:.2f}',
                'mean': '{:.3f}',
                'max': '{:.2f}',
            })
            st.dataframe(formatted_agg_ytgpa)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(agg_ytgpa),
                file_name=f"{term}_{year_start}-{year_end}_gpa_statistics.csv",
                mime='text/csv',
            )

            c = alt.Chart(agg_ytgpa.reset_index()).mark_bar().encode(
                x='yearterm:N',
                y=alt.Y('mean:Q', axis=alt.Axis(title='mean gpa')),
                tooltip=['yearterm:N', alt.Tooltip('mean:Q', title='mean gpa', format='.3')],
            )
            st.altair_chart(c)

            st.write(f"#### GPA Bins ({term} {year_start}-{year_end})")
            bins=[-0.1, 1, 2, 2.5, 3.0, 3.5, 4.0]
            labels=['0.0-1.0', '1.0-2.0', '2.0-2.5', '2.5-3.0', '3.0-3.5', '3.5-4.0']
            atgpa['gpa_bin'] = pd.cut(atgpa['GPA'], 
                                            bins=bins,
                                            labels=labels,
                                            )
            atgpa['gpa_bin'] = atgpa['gpa_bin'].dropna().astype(str)
            # st.write(atgpa.shape)
            # st.dataframe(atgpa)

            gpab = atgpa[['PEOPLE_CODE_ID', 'yearterm', 'gpa_bin']].groupby(['yearterm', 'gpa_bin'], observed=False).count()
            gpab = ( gpab.reset_index()
                .rename(
                    columns={
                        'PEOPLE_CODE_ID': 'count'
                    },
                )
            )
            # st.dataframe(gpab)

            st.write("##### GPA Bins - Counts")
            gpabc = gpab.pivot(
                index='yearterm', 
                columns='gpa_bin',
                values='count'
            )
            gpabc['Total'] = gpabc[labels].sum(axis=1)
            st.dataframe(gpabc)
            st.download_button(
                label="Download data as CSV",
                data=gpabc.to_csv(index=True).encode('utf-8'),
                file_name=f"{term}_{year_start}-{year_end}_gpa_bins_count.csv",
                mime='text/csv',
            )

            st.write("##### GPA Bins - Percentages")
            # calculate percentage of each gpa bin within each yearterm
            gpa_yt_bin = atgpa.groupby(['yearterm', 'gpa_bin'], group_keys=False).agg({'PEOPLE_CODE_ID':'count'}).rename(columns={'PEOPLE_CODE_ID':'count'})
            # st.dataframe(gpa_yt_bin)
            gpa_yt_bin_pcts = gpa_yt_bin.groupby(level=0, group_keys=False).apply(lambda x: 100 * x / float(x.sum())).rename(columns={'count':'pct'})
            gpa_yt_bin_pcts = gpa_yt_bin_pcts.reset_index()
            # st.dataframe(gpa_yt_bin_pcts)
            gpabp = gpa_yt_bin_pcts.pivot(
                         index='yearterm', 
                         columns='gpa_bin',
                         values='pct'
                         )
            st.dataframe(gpabp.style.format('{:.1f}'))
            st.download_button(
                label="Download data as CSV",
                data=convert_df(gpabp),
                file_name=f"{term}_{year_start}-{year_end}_gpa_yt_bins_pct.csv",
                mime='text/csv',
            )

            st.write("##### GPA Bins - Visualization")
            c1 = alt.Chart(gpab).transform_joinaggregate(
                    YearTermCount='sum(count)',
                    groupby=['yearterm']
                ).transform_calculate(
                    PercentOfTotal="datum.count / datum.YearTermCount",
                ).mark_bar().encode(
                x='yearterm:N',
                y=alt.Y('PercentOfTotal:Q', axis=alt.Axis(title='percent of yearterm GPAs', format='.0%')),
                color='yearterm:N',
                column=alt.Column(shorthand='gpa_bin:N',sort=labels),
                tooltip=['gpa_bin', 'yearterm', alt.Tooltip('sum(count):Q', title='GPAs'), alt.Tooltip('PercentOfTotal:Q', title='pct of yearterm', format='.3p')],
            )
            st.altair_chart(c1)

