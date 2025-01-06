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


@st.cache_data
def grads_df(begin_date:dt.datetime) -> pd.DataFrame:

    transcriptdegree = pc.select("TRANSCRIPTDEGREE",
        fields=['PEOPLE_CODE_ID', 'PROGRAM', 'DEGREE', 'CURRICULUM', 'COLLEGE',
            'GRADUATION_DATE', 'FORMAL_TITLE',
            ],
        where=f"GRADUATION_DATE >= '{begin_date}' " +
            "and DEGREE IN ('MS', 'MPS', 'BA', 'BS', 'BPS', 'AA', 'AS', 'AAS', 'AOS', 'CERTIF', 'GCERT') "
     )
    transcriptdegree["degree_earned"] = False
    transcriptdegree.loc[(transcriptdegree["DEGREE"].isin(["MS", "MPS"])), "degree_earned"] = "Masters"
    transcriptdegree.loc[(transcriptdegree["DEGREE"].isin(["GCERT"])), "degree_earned"] = "Grad Cert"
    transcriptdegree.loc[(transcriptdegree["DEGREE"].isin(["BA", "BS", "BPS"])), "degree_earned"] = "Bachelors"
    transcriptdegree.loc[(transcriptdegree["DEGREE"].isin(["AA", "AS", "AAS", "AOS"])), "degree_earned"] = "Associates"
    transcriptdegree.loc[(transcriptdegree["DEGREE"].isin(["CERTIF"])), "degree_earned"] = "Certificate"
    transcriptdegree["grad_year"] = transcriptdegree["GRADUATION_DATE"].dt.year.astype(str)
    transcriptdegree["grad_month"] = transcriptdegree["GRADUATION_DATE"].dt.month.astype(str)

    return transcriptdegree


start_date = dt.datetime(2000, 1, 1 )
start_year = str(start_date.year)

current_yt_df = pc.current_yearterm()
current_term = current_yt_df['term'].iloc[0]
current_year = current_yt_df['year'].iloc[0]
current_yt = current_yt_df['yearterm'].iloc[0]
current_yt_sort = current_yt_df['yearterm_sort'].iloc[0]


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Academic Program - Graduates ..."):
        src.pages.components.logo()
        st.write(
            """
            ## Academic Program - Graduates
"""
        )

        today = dt.datetime.today()
        today_str = today.strftime("%Y%m%d")

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
        year_list = [y for y in year_list if ((y>=start_year) and (y<=current_year))]
        year_start, year_end = st.select_slider(
            "Select range of years:",
            options=year_list,
            value=('2010', current_year)
        )

        if year_start and year_end:

            df = grads_df(start_date)
            df0 = ( df.loc[(df['grad_year']>=year_start) & (df['grad_year']<=year_end)]
                    .rename(columns={"CURRICULUM": "academic_program"})
            )

            program_list = sorted(df0['academic_program'].unique())
            programs = st.multiselect(
                'Select academic program(s):',
                options=program_list,
                default=program_list,
                )
            df1 = df0.loc[(df0['academic_program'].isin(programs))]

            st.write(f"#### Number of Graduates by Year ({year_start}-{year_end})")
            df_yr = ( df1.groupby(['grad_year', 'academic_program' ])
                        .agg(
                            {'PEOPLE_CODE_ID': ['count',],
                            }
                        )
                        .reset_index()
                        .droplevel(1, axis=1)
                        .rename(
                            columns={'PEOPLE_CODE_ID': 'graduates'}
                        )
            )
            st.dataframe(df_yr)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df_yr),
                file_name=f"{year_start}-{year_end}_graduates_by_year.csv",
                mime='text/csv',
            )

            c = alt.Chart(df_yr).mark_bar().encode(
                x=alt.X('grad_year:N', title='year'),
                y=alt.Y('sum(graduates):Q', axis=alt.Axis(title='number of graduates')),
                # color='academic_program:N',
                column=alt.Column('academic_program:N', title='academic program'),
                tooltip=[
                        alt.Tooltip('academic_program:N', title='program'), 
                        alt.Tooltip('grad_year:N', title='year'),
                        alt.Tooltip('sum(graduates):Q', title='graduates')],
            )
            st.altair_chart(c)

            degree_sort = ['Masters', 'Grad Cert', 'Bachelors', 'Associates', 'Certificate']

            st.write(f"#### Total Graduates ({year_start}-{year_end})")
            st.write(f"Selected Programs: ({programs})")
            df2 = (
                df1.groupby(["grad_year", "degree_earned"])["PEOPLE_CODE_ID"].count()
                .reset_index()
                # .droplevel(1, axis=1)
                .rename(columns={'PEOPLE_CODE_ID': 'graduates'})
            )
            st.dataframe(df2)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df2),
                file_name=f"{year_start}-{year_end}_total_grads.csv",
                mime='text/csv',
            )

            c1 = alt.Chart(df2.reset_index()).mark_bar().encode(
                x=alt.X('grad_year:N'),
                y=alt.Y('graduates:Q', axis=alt.Axis(title='number of graduates')),
                color=alt.Color(shorthand='degree_earned:N', title='degree', sort=degree_sort),
                order=alt.Order('color_degree_earned_sort_index:Q', sort='descending'),
                tooltip=[alt.Tooltip('grad_year:N', title='year'), 
                        alt.Tooltip('degree_earned:N', title='degree'),
                        alt.Tooltip('graduates:Q', title='graduates')
                ],
            )
            st.altair_chart(c1)

            st.markdown("---")
            st.write(f"### PSC Total Graduates ({year_start}-{year_end})")
            df3 = ( df0[['PEOPLE_CODE_ID', 'grad_year', 'degree_earned', ]]
                        .groupby(
                            ['grad_year', 'degree_earned']
                        )
                        .count()
                        .reset_index()
                        .rename(
                            columns= {
                                'PEOPLE_CODE_ID': 'graduates'
                            }
                        )
            )
            st.dataframe(df3)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(df3),
                file_name=f"{year_start}-{year_end}_PSC_total_grads.csv",
                mime='text/csv',
            )
            c2 = alt.Chart(df3).transform_joinaggregate(
                total='sum(graduates)',
                groupby=['grad_year']
            ).transform_calculate(
                percent=alt.datum.graduates / alt.datum.total
            ).mark_bar().encode(
                x=alt.X('grad_year:N'),
                y=alt.Y('graduates:Q', axis=alt.Axis(title='number of graduates')),
                color=alt.Color(shorthand='degree_earned:N', title='degree', sort=degree_sort),
                order=alt.Order('color_degree_earned_sort_index:Q', sort='descending'),
                tooltip=[alt.Tooltip('grad_year:N', title='year'), 
                        alt.Tooltip('degree_earned:N', title='degree'),
                        alt.Tooltip('graduates:Q', title='graduates'),
                        alt.Tooltip('total:Q', title='total'),
                        alt.Tooltip('percent:Q', title='percent', format='.1%')
                ],
            )
            st.altair_chart(c2)
