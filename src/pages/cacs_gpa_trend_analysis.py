import pandas as pd
import streamlit as st
import altair as alt
import datetime as dt
import hashlib
import src.pages.components

# PowerCampus utilities
import powercampus as pc

@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

def idstr_anonymous(idstr):
    hash_object = hashlib.sha1(idstr.encode('utf-8'))
    id = int(hash_object.hexdigest(),16) % (10**12)
    return '{0:012d}'.format(id)

start_year = pc.START_ACADEMIC_YEAR

current_yt_df = pc.current_yearterm()
current_term = current_yt_df['term'].iloc[0]
current_year = current_yt_df['year'].iloc[0]
current_yt = current_yt_df['yearterm'].iloc[0]
current_yt_sort = current_yt_df['yearterm_sort'].iloc[0]


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading CACS - GPA Trend Analysis ..."):
        src.pages.components.page_header()
        st.write(
            """
            ## CACS - GPA Trend Analysis
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
        # year_start, year_end = st.select_slider(
        #     "Select range of years:",
        #     options=year_list,
        #     value=('2012', current_year)
        # )
        year = st.selectbox(label="Select year:", options=year_list, index=year_list.index(current_year))

        term = st.selectbox(label="Select term:", options=['Fall', 'Spring'])
        # gpa_type = st.selectbox(label="Select GPA type:", options=['Cumulative', 'Term'])
        gpa_type = 'Term'

        # undergrad_only = st.checkbox("Undergraduate students only", value=True )
        undergrad_only = True

        if year and term and gpa_type:

            academic = pc.select("ACADEMIC",
                fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION',
                    'PROGRAM', 'DEGREE', 'CURRICULUM', 'COLLEGE', 'DEPARTMENT', 'CLASS_LEVEL', 'POPULATION',
                    'FULL_PART', 'ACADEMIC_STANDING', 'ENROLL_SEPARATION', 'SEPARATION_DATE', 'CREDITS',  
                    'COLLEGE_ATTEND', 'STATUS', 'PRIMARY_FLAG',
                    ],
                where=f"ACADEMIC_YEAR='{int(year)}' and ACADEMIC_TERM='{term}' " +
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
            academic = pc.add_col_yearterm(academic)
            academic = academic.rename(columns={'yearterm': 'selected_yearterm'})
            academic = pc.add_col_yearterm_sort(academic)
            academic = academic.rename(columns={'yearterm_sort': 'selected_yearterm_sort'})
            academic = academic.drop(columns=['ACADEMIC_YEAR', 'ACADEMIC_TERM'])

            st.write(f"ACADEMIC shape: {academic.shape}")
            # st.dataframe(academic)

            transcript_gpa = pc.select("TRANSCRIPTGPA",
                fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'RECORD_TYPE', 'GPA', 'ATTEMPTED_CREDITS',],
                where=f"ACADEMIC_YEAR>='{int(start_year)}' and ACADEMIC_YEAR<='{int(year)}' and ACADEMIC_TERM IN ('FALL', 'SPRING') " +
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
            transcript_gpa = pc.add_col_yearterm(transcript_gpa)
            transcript_gpa = transcript_gpa.rename(columns={'yearterm': 'gpa_yearterm'})
            transcript_gpa = pc.add_col_yearterm_sort(transcript_gpa)
            transcript_gpa = transcript_gpa.rename(columns={'yearterm_sort': 'gpa_yearterm_sort'})
            transcript_gpa = transcript_gpa.drop(columns=['ACADEMIC_YEAR', 'ACADEMIC_TERM'])
           
            st.write(f"TRANSCRIPTGPA shape: {transcript_gpa.shape}")
            # st.dataframe(transcript_gpa)
 
            atgpa = academic.merge(transcript_gpa,
                how='left',
                on=['PEOPLE_CODE_ID' ]
                )
            atgpa["id"] = atgpa["PEOPLE_CODE_ID"].map(idstr_anonymous)
            atgpa = atgpa.drop(columns=['PEOPLE_CODE_ID'])
            # st.write(f"atgpa shape: {atgpa.shape}")
            # st.dataframe(atgpa)

            # for each student for the selected_yearterm, rank terms by gpa_yearterm_sort
            atgpa = atgpa.sort_values(['id', 'selected_yearterm', 'gpa_yearterm_sort'])
            atgpa['term'] = atgpa.groupby(['id', 'selected_yearterm'])['gpa_yearterm_sort'].rank(method='dense', ascending=True)
            atgpa = atgpa.drop(columns=['gpa_yearterm', 'gpa_yearterm_sort', 'selected_yearterm', 'selected_yearterm_sort'])
            atgpa = atgpa.sort_values(['id', 'term'])
            st.write(f"atgpa shape: {atgpa.shape}")
            # st.dataframe(atgpa)

            # transpose atgpa to have one row per student, with columns for each term's GPA
            atgpa_transposed = atgpa.pivot(index='id', columns='term', values='GPA')
            # rename columns to term1, term2, etc.
            atgpa_transposed = atgpa_transposed.rename(columns=lambda x: f'term{int(x)}')
            # atgpa_transposed = atgpa_transposed.add_prefix('GPA_')
            st.write(f"atgpa_transposed shape: {atgpa_transposed.shape}")
            st.dataframe(atgpa_transposed)

            # calculate number of terms with gpa for each student, and filter to students with at least 2 terms of gpa
            atgpa_transposed['num_terms'] = atgpa_transposed.notna().sum(axis=1)
            twoterms_gpa = atgpa_transposed.loc[atgpa_transposed['num_terms'] >= 2]
            st.write(f"atgpa_transposed shape after filtering to students with at least 2 terms of gpa: {twoterms_gpa.shape}")
            st.dataframe(twoterms_gpa)

            # filter students with term 1 and term 2 gpas between 2.0 and 3.0
            murky_middle = twoterms_gpa.loc[    (twoterms_gpa['term1'] >= 2.0) & (twoterms_gpa['term1'] <= 3.0) &
                                                        (twoterms_gpa['term2'] >= 2.0) & (twoterms_gpa['term2'] <= 3.0)
                                                        ]
            st.write(f"Murky Middle: twoterms_gpa shape after filtering to students with term 1 and term 2 gpas between 2.0 and 3.0: {murky_middle.shape}")
            st.dataframe(murky_middle)  

            # calcualte slope of gpa change throughout students' academic careers, and filter to students with a positive slope (improving gpa)
            term_cols = [col for col in murky_middle.columns if col.startswith('term')]
            murky_middle['gpa_slope'] = murky_middle[term_cols].apply(lambda row: pd.Series(row.dropna().values).reset_index(drop=True).diff().mean(), axis=1)
            murky_middle_inc_gpa = murky_middle.loc[murky_middle['gpa_slope'] > 0]
            st.write(f"murky_middle_inc_gpa shape after filtering to students with a positive gpa slope: {murky_middle_inc_gpa.shape}")
            st.dataframe(murky_middle_inc_gpa)  

            # Plot chart of gpa vs term, with one line per student using altair
            murky_middle_reset = murky_middle_inc_gpa.reset_index().drop(columns=['gpa_slope', 'num_terms'])
            mm_long = murky_middle_reset.melt(id_vars='id', var_name='term', value_name='GPA')
            st.write(f"mm_long shape: {mm_long.shape}")
            mm_long = mm_long.dropna(subset=['GPA'])
            st.write(f"mm_long shape: {mm_long.shape}")
            st.dataframe(mm_long)
            c = alt.Chart(mm_long).mark_line().encode(
                x='term:N',
                y=alt.Y('GPA:Q', axis=alt.Axis(title='GPA')),
                color=alt.Color('id:N', legend=None),
                tooltip=['id:N', 'term:N', alt.Tooltip('GPA:Q', title='GPA', format='.3')],
            ).properties(
                width=600,
                height=400,
                title=f"{gpa_type} GPA Trend Analysis for {term} {year}"
            )
            st.altair_chart(c)


            # calcualte slope of gpa change throughout students' academic careers, and filter to students with a negative slope (declining gpa)
            murky_middle_dec_gpa = murky_middle.loc[murky_middle['gpa_slope'] < 0]
            st.write(f"murky_middle_dec_gpa shape after filtering to students with a negative gpa slope: {murky_middle_dec_gpa.shape}")
            
            st.dataframe(murky_middle_dec_gpa)  

            # Plot chart of gpa vs term, with one line per student using altair
            murky_middle_reset = murky_middle_dec_gpa.reset_index().drop(columns=['gpa_slope', 'num_terms'])
            mm_long = murky_middle_reset.melt(id_vars='id', var_name='term', value_name='GPA')
            st.write(f"mm_long shape: {mm_long.shape}")
            mm_long = mm_long.dropna(subset=['GPA'])
            st.write(f"mm_long shape: {mm_long.shape}")
            st.dataframe(mm_long)
            c = alt.Chart(mm_long).mark_line().encode(
                x='term:N',
                y=alt.Y('GPA:Q', axis=alt.Axis(title='GPA')),
                color=alt.Color('id:N', legend=None),
                tooltip=['id:N', 'term:N', alt.Tooltip('GPA:Q', title='GPA', format='.3')],
            ).properties(
                width=600,
                height=400,
                title=f"{gpa_type} GPA Trend Analysis for {term} {year}"
            )
            st.altair_chart(c)

            # using the murky_middle_dec_gpa dataframe, grouping by num_terms, calculate the mean GPA for each term, and plot using altair sort the term columns in order of term number rather than alphabetically
            murky_middle_grouped = murky_middle_dec_gpa.groupby('num_terms').mean().reset_index()
            # Drop the gpa_slope columns for the altair plot
            murky_middle_grouped = murky_middle_grouped.drop(columns=['gpa_slope'])
            # Sort the term columns in order of term number rather than alphabetically by extracting the term number and sorting by it
            term_cols = [col for col in murky_middle_grouped.columns if col.startswith('term')]
            murky_middle_grouped[term_cols] = murky_middle_grouped[term_cols].reindex(sorted(term_cols, key=lambda x: int(x.replace('term', ''))), axis=1)
            st.write(f"murky_middle_grouped shape: {murky_middle_grouped.shape}")
            st.dataframe(murky_middle_grouped)
            mmg_long = murky_middle_grouped.melt(id_vars='num_terms', var_name='term', value_name='GPA')
            mmg_long = mmg_long.dropna(subset=['GPA'])

            st.write(f"mmg_long shape: {mmg_long.shape}")
            st.dataframe(mmg_long)

            c = alt.Chart(mmg_long).mark_line().encode(
                x=alt.X('term:N', sort=term_cols),
                y=alt.Y('GPA:Q', axis=alt.Axis(title='mean GPA')),
                color=alt.Color('num_terms:N', legend=alt.Legend(title='Number of Terms with GPA')),
                tooltip=['num_terms:N', 'term:N', alt.Tooltip('GPA:Q', title='mean GPA', format='.3')],
            ).properties(
                width=600,
                height=400,
                title=f"{gpa_type} GPA Trend Analysis for {term} {year}"
            )
            st.altair_chart(c)



            # st.write("___")
            # st.write(f"#### GPA Statistics ({term} {year_start}-{year_end})")
            # agg_ytgpa = ( atgpa[['yearterm', 'GPA']].groupby(['yearterm']).agg(
            #         {'GPA': ['count', 'min', 'median', 'mean', 'max']}
            #         )
            #         .droplevel(0, axis=1)
            #         .sort_index()
            #         .rename(
            #             columns={
            #                 'count': 'students'
            #             },
            #             index={
            #                 1:'yearterm'
            #             }
            #         )
            # )
            # formatted_agg_ytgpa = agg_ytgpa.style.format({
            #     'min': '{:.2f}',
            #     'median': '{:.2f}',
            #     'mean': '{:.3f}',
            #     'max': '{:.2f}',
            # })
            # st.dataframe(formatted_agg_ytgpa)
            # st.download_button(
            #     label="Download data as CSV",
            #     data=convert_df(agg_ytgpa),
            #     file_name=f"{term}_{year_start}-{year_end}_gpa_statistics.csv",
            #     mime='text/csv',
            # )

            # c = alt.Chart(agg_ytgpa.reset_index()).mark_bar().encode(
            #     x='yearterm:N',
            #     y=alt.Y('mean:Q', axis=alt.Axis(title='mean gpa')),
            #     tooltip=['yearterm:N', alt.Tooltip('mean:Q', title='mean gpa', format='.3')],
            # )
            # st.altair_chart(c)

            # st.write("___")
            # st.write(f"#### GPA Bins ({term} {year_start}-{year_end})")
            # bins=[-0.1, 1, 2, 2.5, 3.0, 3.5, 4.0]
            # labels=['0.0-1.0', '1.0-2.0', '2.0-2.5', '2.5-3.0', '3.0-3.5', '3.5-4.0']
            # atgpa['gpa_bin'] = pd.cut(atgpa['GPA'], 
            #                                 bins=bins,
            #                                 labels=labels,
            #                                 )
            # atgpa['gpa_bin'] = atgpa['gpa_bin'].dropna().astype(str)
            # # st.write(atgpa.shape)
            # # st.dataframe(atgpa)

            # gpab = atgpa[['PEOPLE_CODE_ID', 'yearterm', 'gpa_bin']].groupby(['yearterm', 'gpa_bin'], observed=False).count()
            # gpab = ( gpab.reset_index()
            #     .rename(
            #         columns={
            #             'PEOPLE_CODE_ID': 'count'
            #         },
            #     )
            # )
            # # st.dataframe(gpab)

            # st.write("##### GPA Bins - Counts")
            # gpabc = gpab.pivot(
            #     index='yearterm', 
            #     columns='gpa_bin',
            #     values='count'
            # )
            # gpabc['Total'] = gpabc[labels].sum(axis=1)
            # st.dataframe(gpabc)
            # st.download_button(
            #     key='GPA Bins - Counts',
            #     label="Download data as CSV",
            #     data=gpabc.to_csv(index=True).encode('utf-8'),
            #     file_name=f"{term}_{year_start}-{year_end}_gpa_yt_bins_count.csv",
            #     mime='text/csv',
            # )

            # st.write("##### GPA Bins - Percentages")
            # # calculate percentage of each gpa bin within each yearterm
            # gpa_yt_bin = atgpa.groupby(['yearterm', 'gpa_bin'], group_keys=False).agg({'PEOPLE_CODE_ID':'count'}).rename(columns={'PEOPLE_CODE_ID':'count'})
            # # st.dataframe(gpa_yt_bin)
            # gpa_yt_bin_pcts = gpa_yt_bin.groupby(level=0, group_keys=False).apply(lambda x: 100 * x / float(x.sum())).rename(columns={'count':'pct'})
            # gpa_yt_bin_pcts = gpa_yt_bin_pcts.reset_index()
            # # st.dataframe(gpa_yt_bin_pcts)
            # gpabp = gpa_yt_bin_pcts.pivot(
            #              index='yearterm', 
            #              columns='gpa_bin',
            #              values='pct'
            #              )
            # st.dataframe(gpabp.style.format('{:.1f}'))
            # st.download_button(
            #     key='GPA Bins - Percentages',
            #     label="Download data as CSV",
            #     data=gpabp.to_csv(index=True).encode('utf-8'),
            #     file_name=f"{term}_{year_start}-{year_end}_gpa_yt_bins_pct.csv",
            #     mime='text/csv',
            # )

            # st.write("##### GPA Bins - Visualization")
            # c1 = alt.Chart(gpab).transform_joinaggregate(
            #         YearTermCount='sum(count)',
            #         groupby=['yearterm']
            #     ).transform_calculate(
            #         PercentOfTotal="datum.count / datum.YearTermCount",
            #     ).mark_bar().encode(
            #     x='yearterm:N',
            #     y=alt.Y('PercentOfTotal:Q', axis=alt.Axis(title='percent of yearterm GPAs', format='.0%')),
            #     color='yearterm:N',
            #     column=alt.Column(shorthand='gpa_bin:N',sort=labels),
            #     tooltip=['gpa_bin', 'yearterm', alt.Tooltip('sum(count):Q', title='GPAs'), alt.Tooltip('PercentOfTotal:Q', title='pct of yearterm', format='.3p')],
            # )
            # st.altair_chart(c1)

            # st.write("___")
            # st.write(f"#### GPA Above 2.0 ({term} {year_start}-{year_end})")
            # gpa_gt2 = atgpa.copy()
            # bins=[-0.1, 2, 4.0]
            # labels=['Below 2.0', '2.0 or Above', ]
            # gpa_gt2['gpa_bin2'] = pd.cut(atgpa['GPA'], 
            #                                 bins=bins,
            #                                 labels=labels,
            #                                 )
            # gpa_gt2['gpa_bin2'] = gpa_gt2['gpa_bin2'].dropna().astype(str)

            # gpab2 = gpa_gt2[['PEOPLE_CODE_ID', 'yearterm', 'gpa_bin2']].groupby(['yearterm', 'gpa_bin2'], observed=False).count()
            # gpab2 = ( gpab2.reset_index()
            #     .rename(
            #         columns={
            #             'PEOPLE_CODE_ID': 'count'
            #         },
            #     )
            # )
            # # st.dataframe(gpab2)

            # st.write("##### GPA Above 2.0 - Counts")
            # gpabc2 = gpab2.pivot(
            #     index='yearterm', 
            #     columns='gpa_bin2',
            #     values='count'
            # )
            # gpabc2['Total'] = gpabc2[labels].sum(axis=1)
            # st.dataframe(gpabc2)
            # st.download_button(
            #     key='GPA Above 2.0 - Counts',
            #     label="Download data as CSV",
            #     data=gpabc2.to_csv(index=True).encode('utf-8'),
            #     file_name=f"{term}_{year_start}-{year_end}_gpa_yt_gt2_bins_count.csv",
            #     mime='text/csv',
            # )

            # st.write("##### GPA Above 2.0 - Percentages")
            # # calculate percentage of each gpa bin within each yearterm
            # gpa_yt_bin2 = gpa_gt2.groupby(['yearterm', 'gpa_bin2'], group_keys=False).agg({'PEOPLE_CODE_ID':'count'}).rename(columns={'PEOPLE_CODE_ID':'count'})
            # # st.dataframe(gpa_yt_bin2)
            # gpa_yt_bin_pcts2 = gpa_yt_bin2.groupby(level=0, group_keys=False).apply(lambda x: 100 * x / float(x.sum())).rename(columns={'count':'pct'})
            # gpa_yt_bin_pcts2 = gpa_yt_bin_pcts2.reset_index()
            # # st.dataframe(gpa_yt_bin_pcts2)
            # gpabp2 = gpa_yt_bin_pcts2.pivot(
            #              index='yearterm', 
            #              columns='gpa_bin2',
            #              values='pct'
            #              )
            # st.dataframe(gpabp2.style.format('{:.1f}'))
            # st.download_button(
            #     key='GPA Above 2.0 - Percentages',
            #     label="Download data as CSV",
            #     data=gpabp2.to_csv(index=True).encode('utf-8'),
            #     file_name=f"{term}_{year_start}-{year_end}_gpa_yt_gt2_bins_pct.csv",
            #     mime='text/csv',
            # )

            # st.write("##### GPA Above 2.0 - Visualization")
            # c2 = alt.Chart(gpab2).transform_joinaggregate(
            #         YearTermCount='sum(count)',
            #         groupby=['yearterm']
            #     ).transform_calculate(
            #         PercentOfTotal="datum.count / datum.YearTermCount",
            #     ).mark_bar().encode(
            #     x='yearterm:N',
            #     y=alt.Y('PercentOfTotal:Q', axis=alt.Axis(title='percent of yearterm GPAs', format='.0%')),
            #     color='yearterm:N',
            #     column=alt.Column(shorthand='gpa_bin2:N',sort=labels),
            #     tooltip=['gpa_bin2', 'yearterm', alt.Tooltip('sum(count):Q', title='GPAs'), alt.Tooltip('PercentOfTotal:Q', title='pct of yearterm', format='.3p')],
            # )
            # st.altair_chart(c2)

