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
    with st.spinner("Loading Retention - GPA Trend Analysis ..."):
        src.pages.components.page_header()
        st.write(
            """
            ## Retention - GPA Trend Analysis
"""
        )

        today = dt.datetime.today()
        today_str = today.strftime("%Y%m%d_%H%M")
        st.write(f"{today.strftime('%Y-%m-%d %H:%M')}")

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
        term_df = term_df.loc[term_df['yearterm_sort'] <= current_yt_sort]
        term_df = term_df.set_index('yearterm')

        year_list = term_df['ACADEMIC_YEAR'].unique().tolist()
        year_start, year_end = st.select_slider(
            "Select range of years:",
            options=year_list,
            value=('2012', current_year),
        )
        # year = st.selectbox(label="Select year:", options=year_list, index=year_list.index(current_year))

        term = st.selectbox(label="Select term:", options=['Fall', 'Spring'])
        # gpa_type = st.selectbox(label="Select GPA type:", options=['Cumulative', 'Term'])
        gpa_type = 'Term'

        # undergrad_only = st.checkbox("Undergraduate students only", value=True )
        undergrad_only = True

        if year_start and year_end and term and gpa_type:

            academic = pc.select("ACADEMIC",
                fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION',
                    'PROGRAM', 'DEGREE', 'CURRICULUM', 'COLLEGE', 'DEPARTMENT', 'CLASS_LEVEL', 'POPULATION',
                    'FULL_PART', 'ACADEMIC_STANDING', 'ENROLL_SEPARATION', 'SEPARATION_DATE', 'CREDITS',  
                    'COLLEGE_ATTEND', 'STATUS', 'PRIMARY_FLAG', 'GRADUATED',
                    ],
                where=f"ACADEMIC_YEAR>='{int(year_start)}' and ACADEMIC_YEAR<='{int(year_end)}' and ACADEMIC_TERM IN ('FALL', 'SPRING') " +
                    "and ACADEMIC_SESSION='' and PROGRAM='U' and CREDITS>0 and CURRICULUM<>'ADVST' and PRIMARY_FLAG='Y' ", 
            )
            if undergrad_only:
                academic = academic.loc[(academic['PROGRAM'] != 'G')]
            keep_cols = [
                'PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'GRADUATED',
            ]
            academic = academic.loc[:, keep_cols]
            academic = academic.drop_duplicates(keep_cols)
            academic = academic.sort_values(keep_cols)
            academic = pc.add_col_yearterm(academic)
            # academic = academic.rename(columns={'yearterm': 'selected_yearterm'})
            academic = pc.add_col_yearterm_sort(academic)
            # academic = academic.rename(columns={'yearterm_sort': 'selected_yearterm_sort'})
            academic = academic.loc[academic['yearterm_sort'] <= current_yt_sort]
            academic = academic.drop(columns=['ACADEMIC_YEAR', 'ACADEMIC_TERM'])
            academic['currently_enrolled'] = academic['yearterm'] == current_yt

            st.write(f"ACADEMIC shape: {academic.shape}")
            # st.dataframe(academic)

            transcript_degree = pc.select("TRANSCRIPTDEGREE",
                fields=['PEOPLE_CODE_ID', 'PROGRAM', 'DEGREE', 'CURRICULUM', 'GRADUATION_DATE'],
                where=f"GRADUATION_DATE IS NOT NULL AND GRADUATION_DATE>='2001-01-01' AND GRADUATION_DATE<='{today.strftime('%Y-%m-%d')}' AND PROGRAM='U' AND DEGREE NOT IN ('CERTIF', 'MS', 'MPS' )", 
                )
            # st.dataframe(transcript_degree)
            keep_cols = [
                'PEOPLE_CODE_ID', 'GRADUATION_DATE', 
            ]
            transcript_degree = transcript_degree.loc[:, keep_cols]
            transcript_degree = transcript_degree.sort_values(keep_cols)
            transcript_degree = transcript_degree.drop_duplicates(['PEOPLE_CODE_ID',], keep='last')
            st.write(f"TRANSCRIPTDEGREE shape: {transcript_degree.shape}")
            # st.dataframe(transcript_degree)

            academic = academic.merge(transcript_degree,
                how='left',
                on=['PEOPLE_CODE_ID', ] 
                )
            academic = academic.sort_values(['PEOPLE_CODE_ID', 'yearterm_sort'])
            st.write(f"ACADEMIC shape: {academic.shape}")
            # st.dataframe(academic)

            # aggregate academic to one row per student, with columns for first yearterm_sort, last yearterm_sort, whether they graduated, and if currently enrolled
            academic = academic.sort_values(['PEOPLE_CODE_ID', 'yearterm_sort'])
            academic = academic.groupby('PEOPLE_CODE_ID').agg({
                'yearterm_sort': ['min', 'max'],
                'GRADUATED': 'max',
                'currently_enrolled': 'max'
            }).reset_index()
            academic.columns = ['PEOPLE_CODE_ID', 'min_yearterm_sort', 'max_yearterm_sort', 'GRADUATED', 'currently_enrolled']
            academic['graduated'] = (academic['GRADUATED'] == 'G')
            academic['droppedout'] = (~academic['currently_enrolled']) & (~academic['graduated'])
            academic = academic.drop(columns=['GRADUATED', 'min_yearterm_sort', 'max_yearterm_sort'])
            st.write(f"ACADEMIC shape after grouping: {academic.shape}")
            # st.dataframe(academic)


            transcript_gpa = pc.select("TRANSCRIPTGPA",
                fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'RECORD_TYPE', 'GPA', 'ATTEMPTED_CREDITS',],
                where=f"ACADEMIC_YEAR>='{int(start_year)}' and ACADEMIC_YEAR<='{int(year_end)}' and ACADEMIC_TERM IN ('FALL', 'SPRING') " +
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
            transcript_gpa = transcript_gpa.sort_values(keep_cols)
            transcript_gpa = transcript_gpa.drop_duplicates(keep_cols, keep='last')
            transcript_gpa = pc.add_col_yearterm(transcript_gpa)
            # transcript_gpa = transcript_gpa.rename(columns={'yearterm': 'gpa_yearterm'})
            transcript_gpa = pc.add_col_yearterm_sort(transcript_gpa)
            # transcript_gpa = transcript_gpa.rename(columns={'yearterm_sort': 'gpa_yearterm_sort'})
            transcript_gpa = transcript_gpa.loc[transcript_gpa['yearterm_sort'] <= current_yt_sort]
            transcript_gpa = transcript_gpa.drop(columns=['ACADEMIC_YEAR', 'ACADEMIC_TERM'])
            st.write(f"TRANSCRIPTGPA shape: {transcript_gpa.shape}")
            # st.dataframe(transcript_gpa)
 
            # for each student for the yearterm, rank terms by gpa_yearterm_sort
            transcript_gpa = transcript_gpa.sort_values(['PEOPLE_CODE_ID', 'yearterm_sort', 'GPA'])
            transcript_gpa = transcript_gpa.drop_duplicates(['PEOPLE_CODE_ID', 'yearterm_sort', 'GPA'], keep='last')
            transcript_gpa['term'] = transcript_gpa.groupby(['PEOPLE_CODE_ID'])['yearterm_sort'].rank(method='dense', ascending=True)
            # transcript_gpa = transcript_gpa.drop(columns=['yearterm', 'yearterm_sort'])
            transcript_gpa = transcript_gpa.sort_values(['PEOPLE_CODE_ID', 'term', 'GPA'])
            transcript_gpa = transcript_gpa.drop_duplicates(['PEOPLE_CODE_ID', 'term'], keep='last')
            st.write(f"transcript_gpa shape: {transcript_gpa.shape}")
            # st.dataframe(transcript_gpa)

            # transpose transcript_gpa to have one row per student, with columns for each term's GPA
            tgpa_transposed = transcript_gpa.pivot(index='PEOPLE_CODE_ID', columns='term', values='GPA')
            # rename columns to term1, term2, etc.
            tgpa_transposed = tgpa_transposed.rename(columns=lambda x: f'term{int(x):02d}')
            # tgpa_transposed = tgpa_transposed.add_prefix('GPA_')
            # calculate number of terms with gpa for each student, and filter to students with at least 2 terms of gpa
            tgpa_transposed['num_terms'] = tgpa_transposed.notna().sum(axis=1)
            st.write(f"tgpa_transposed shape: {tgpa_transposed.shape}")
            # st.dataframe(tgpa_transposed)


            atgpa = academic.merge(tgpa_transposed,
                how='left',
                on=['PEOPLE_CODE_ID'] 
                )
            atgpa["id"] = atgpa["PEOPLE_CODE_ID"].map(idstr_anonymous)
            atgpa = atgpa.drop(columns=['PEOPLE_CODE_ID'])
            st.write(f"atgpa shape: {atgpa.shape}")
            # st.dataframe(atgpa)


            # filter to students with at least 2 terms of gpa
            twoterms_gpa = atgpa.loc[atgpa['num_terms'] >= 2]
            st.write(f"atgpa shape after filtering to students with at least 2 terms of gpa: {twoterms_gpa.shape}")
            # st.dataframe(twoterms_gpa)

            # filter students with term 1 and term 2 gpas between 2.0 and 3.0
            murky_middle = twoterms_gpa.loc[    (twoterms_gpa['term01'] >= 2.0) & (twoterms_gpa['term01'] <= 3.0) 
                                                        & (twoterms_gpa['term02'] >= 2.0) & (twoterms_gpa['term02'] <= 3.0)
                                                        ]
            st.write(f"Murky Middle: twoterms_gpa shape after filtering to students with term 1 and term 2 gpas between 2.0 and 3.0: {murky_middle.shape}")
            # st.dataframe(murky_middle)

            # calculate slope of gpa change throughout students' academic careers, and filter to students with a positive slope (improving gpa)
            term_cols = [col for col in murky_middle.columns if col.startswith('term')]
            murky_middle['gpa_slope'] = murky_middle[term_cols].apply(lambda row: pd.Series(row.dropna().values).reset_index(drop=True).diff().mean(), axis=1)

            # create status column for graduated, dropped out, or still enrolled based on academic dataframe columns
            murky_middle['status'] = murky_middle.apply(lambda row: 'graduated' if row['graduated'] == 1 else 'dropped_out' if row['droppedout'] == 1 else 'currently_enrolled', axis=1)
            murky_middle = murky_middle.loc[murky_middle['status'].isin(['graduated', 'dropped_out' ])]
            st.write(f"murky_middle shape after calculating gpa slope and status: {murky_middle.shape}")
            # st.dataframe(murky_middle)

            # murky_middle_inc_gpa = murky_middle.loc[murky_middle['gpa_slope'] > 0]
            # st.write(f"murky_middle_inc_gpa shape after filtering to students with a positive gpa slope: {murky_middle_inc_gpa.shape}")
            # st.dataframe(murky_middle_inc_gpa)  
            
            # murky_middle_reset = murky_middle_inc_gpa.reset_index().drop(columns=['gpa_slope', 'num_terms', 'min_yearterm_sort', 'max_yearterm_sort', 'index' ])
            # st.write(f"murky_middle_reset: {murky_middle_reset.shape}")
            # st.dataframe(murky_middle_reset)
            # mm_long = murky_middle_reset.melt(id_vars='id', var_name='term', value_name='GPA')
            # st.write(f"mm_long shape: {mm_long.shape}")
            # mm_long = mm_long.dropna(subset=['GPA'])
            # st.write(f"mm_long shape: {mm_long.shape}")
            # st.dataframe(mm_long)
            # c = alt.Chart(mm_long).mark_line().encode(
            #     x='term:N',
            #     y=alt.Y('GPA:Q', axis=alt.Axis(title='GPA')),
            #     color=alt.Color('id:N', legend=None),
            #     tooltip=['id:N', 'term:N', alt.Tooltip('GPA:Q', title='GPA', format='.3')],
            # ).properties(
            #     width=900,
            #     height=600,
            #     title=alt.Title(f"{gpa_type} GPA Trend Analysis for {term} {year_start}-{year_end}",
            #                     subtitle="Students with improving GPA (positive slope of GPA change over all terms) and term 1 and term 2 GPAs between 2.0 and 3.0",
            #     )
            # )
            # st.altair_chart(c)


            # calculate slope of gpa change throughout students' academic careers, and filter to students with a negative slope (declining gpa)
            # murky_middle_dec_gpa = murky_middle.loc[murky_middle['gpa_slope'] < 0].set_index('id')
            # st.write(f"murky_middle_dec_gpa shape after filtering to students with a negative gpa slope: {murky_middle_dec_gpa.shape}")
            # st.dataframe(murky_middle_dec_gpa)  

            # # Plot chart of gpa vs term, with one line per student using altair
            # murky_middle_reset = murky_middle_dec_gpa.reset_index().drop(columns=['gpa_slope', 'num_terms'])
            # mm_long = murky_middle_reset.melt(id_vars='id', var_name='term', value_name='GPA')
            # # st.write(f"mm_long shape: {mm_long.shape}")
            # mm_long = mm_long.dropna(subset=['GPA'])
            # # st.write(f"mm_long shape: {mm_long.shape}")
            # # st.dataframe(mm_long)
            # c = alt.Chart(mm_long).mark_line().encode(
            #     x='term:N',
            #     y=alt.Y('GPA:Q', axis=alt.Axis(title='GPA')),
            #     color=alt.Color('id:N', legend=None),
            #     tooltip=['id:N', 'term:N', alt.Tooltip('GPA:Q', title='GPA', format='.3')],
            # ).properties(
            #     width=900,
            #     height=600,
            #     title=alt.Title(f"{gpa_type} GPA Trend Analysis for {term} {year_start}-{year_end}",
            #                     subtitle="Students with declining GPA (negative slope of GPA change over all terms) and term 1 and term 2 GPAs between 2.0 and 3.0",
            #     )
            # )
            # st.altair_chart(c)

            st.write("Count of 'Murky Middle' students by status and number of terms:")
            st.dataframe(murky_middle[['status', 'num_terms', 'id']].groupby(['status', 'num_terms'] ).count().rename(columns={'id': 'count'}))

            # using the murky_middle dataframe, grouping by num_terms, calculate the mean GPA for each term, and plot using altair sort the term columns in order of term number rather than alphabetically
            mm = murky_middle[['status','num_terms', ] + term_cols].copy()
            st.dataframe(mm)
            murky_middle_grouped = mm.groupby(['status', 'num_terms'] ).mean().reset_index()
            # Drop the gpa_slope columns for the altair plot
            # murky_middle_grouped = murky_middle_grouped.drop(columns=['gpa_slope'])
            # Sort the term columns in order of term number rather than alphabetically by extracting the term number and sorting by it
            term_cols = [col for col in murky_middle_grouped.columns if col.startswith('term')]
            murky_middle_grouped[term_cols] = murky_middle_grouped[term_cols].reindex(sorted(term_cols, key=lambda x: int(x.replace('term', ''))), axis=1)
            murky_middle_grouped = murky_middle_grouped.sort_values(['status', 'num_terms'])
            st.write(f"murky_middle_grouped shape: {murky_middle_grouped.shape}")
            st.dataframe(murky_middle_grouped)

            mmg_long = murky_middle_grouped.melt(id_vars=['status', 'num_terms'], var_name='term', value_name='GPA')
            mmg_long = mmg_long.dropna(subset=['GPA'])
            mmg_long = mmg_long.sort_values(['status', 'num_terms', 'term'])
            st.write(f"mmg_long shape: {mmg_long.shape}")
            st.dataframe(mmg_long)

            st.write(f"term columns: {term_cols}")

            # graduated only
            mmg_long_grad = mmg_long.loc[mmg_long['status'] == 'graduated']
            st.write(f"mmg_long_grad shape: {mmg_long_grad.shape}")
            st.dataframe(mmg_long_grad)
            
            c = alt.Chart(mmg_long_grad).mark_line().encode(
                            x=alt.X('term:N', sort=term_cols),
                            y=alt.Y('GPA:Q', axis=alt.Axis(title='mean GPA')),
                            color=alt.Color('num_terms:N', legend=alt.Legend(title='Status and Number of Terms')),
                            tooltip=['num_terms:N', 'term:N', alt.Tooltip('GPA:Q', title='mean GPA', format='.3')],
                        ).properties(
                            width=900,
                            height=600,
                            title=alt.Title(f"{gpa_type} GPA Trend Analysis for {term} {year_start}-{year_end}",
                                            subtitle="Graduated students with term 1 and term 2 GPAs between 2.0 and 3.0",
                            )
            )
            st.altair_chart(c)

            # dropped_out only
            mmg_long_dropped_out = mmg_long.loc[mmg_long['status'] == 'dropped_out']
            st.write(f"mmg_long_dropped_out shape: {mmg_long_dropped_out.shape}")
            st.dataframe(mmg_long_dropped_out)

            c = alt.Chart(mmg_long_dropped_out).mark_line().encode(
                            x=alt.X('term:N', sort=term_cols),
                            y=alt.Y('GPA:Q', axis=alt.Axis(title='mean GPA')),
                            color=alt.Color('num_terms:N', legend=alt.Legend(title='Status and Number of Terms')),
                            tooltip=['num_terms:N', 'term:N', alt.Tooltip('GPA:Q', title='mean GPA', format='.3')],
                        ).properties(
                            width=900,
                            height=600,
                            title=alt.Title(f"{gpa_type} GPA Trend Analysis for {term} {year_start}-{year_end}",
                                            subtitle="Dropped out students with term 1 and term 2 GPAs between 2.0 and 3.0",
                            )
            )
            st.altair_chart(c)



            # c = alt.Chart(mmg_long).transform_calculate(
            #     status_terms="datum.status + '-' + datum.num_terms"
            #             ).mark_line().encode(
            #                 x=alt.X('term:N', sort=term_cols),
            #                 y=alt.Y('GPA:Q', axis=alt.Axis(title='mean GPA')),
            #                 color=alt.Color('status_terms:N', legend=alt.Legend(title='Status and Number of Terms')),
            #                 tooltip=['status:N', 'num_terms:N', 'term:N', alt.Tooltip('GPA:Q', title='mean GPA', format='.3')],
            #             ).properties(
            #                 width=900,
            #                 height=600,
            #                 title=alt.Title(f"{gpa_type} GPA Trend Analysis for {term} {year_start}-{year_end}",
            #                                 subtitle="Students with declining GPA (negative slope of GPA change over all terms) and term 1 and term 2 GPAs between 2.0 and 3.0",
            #                 )
            # )
            # st.altair_chart(c)


            # # for murky_middle, calculate best-fit line for each student's gpa trend, and plot using altair
            # from sklearn.linear_model import LinearRegression
            # def best_fit_line(row):
            #     term_cols = [col for col in row.index if col.startswith('term')]
            #     x = [int(col.replace('term', '')) for col in term_cols if pd.notna(row[col])]
            #     y = [row[col] for col in term_cols if pd.notna(row[col])]
            #     if len(x) >= 2:
            #         model = LinearRegression().fit([[i] for i in x], y)
            #         return model.coef_[0], model.intercept_
            #     else:
            #         return None, None
            # murky_middle[['gpa_slope_best_fit', 'gpa_intercept_best_fit']] = murky_middle.apply(best_fit_line, axis=1, result_type='expand')
            # st.dataframe(murky_middle)

            # # create dataframe for best fit lines for each student, with columns for term and gpa, and plot using altair with one line per student showing the best fit line of their gpa trend over time, colored by whether their slope is positive or negative, and with tooltip showing the student's id, term, and gpa for that term
            # # limit line length by number of terms with gpa for each student
            # mm_best_fit = murky_middle.copy()
            # term_cols = [col for col in mm_best_fit.columns if col.startswith('term')]
            # for col in term_cols:
            #     mm_best_fit[col] = mm_best_fit.apply(lambda row: row['gpa_slope_best_fit'] * int(col.replace('term', '')) + row['gpa_intercept_best_fit'] if (pd.notna(row['gpa_slope_best_fit']) & pd.notna(row[col])) else None, axis=1)



            # st.write(f"mm_best_fit shape: {mm_best_fit.shape}")
            # st.dataframe(mm_best_fit)

            # # plot best fit lines for each student using altair
            # murky_middle_reset = mm_best_fit.reset_index().drop(columns=['gpa_slope', 'num_terms'])
            # mm_long = murky_middle_reset.melt(id_vars=['id', 'gpa_slope_best_fit', 'gpa_intercept_best_fit'], var_name='term', value_name='GPA')
            # mm_long = mm_long.dropna(subset=['GPA'])
            # st.write(f"mm_long shape: {mm_long.shape}")
            # st.dataframe(mm_long)

            # c = alt.Chart(mm_long).mark_line().encode(
            #     x='term:N',
            #     y=alt.Y('GPA:Q', axis=alt.Axis(title='GPA')),
            #     color=alt.Color('id:N', legend=None),
            #     tooltip=['id:N', 'term:N', alt.Tooltip('GPA:Q', title='GPA', format='.3')],
            # ).properties(
            #     width=900,
            #     height=600,
            #     title=alt.Title(f"{gpa_type} GPA Trend Analysis for {term} {year_start}-{year_end}",
            #                     subtitle="Students with term 1 and term 2 GPAs between 2.0 and 3.0, with best fit line for each student's GPA trend",
            #     )
            # )
            # st.altair_chart(c)


