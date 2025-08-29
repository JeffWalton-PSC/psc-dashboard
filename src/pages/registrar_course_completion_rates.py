import altair as alt
import pandas as pd
import streamlit as st
import datetime as dt
import io
import src.pages.components

# PowerCampus utilities
import powercampus as pc

@st.cache_data
def convert_df(df):
    return df.to_csv(index=False).encode('utf-8')

@st.cache_data
def convert_df_xlsx(df_list):
    xl_buffer = io.BytesIO()
    with pd.ExcelWriter(
        xl_buffer,
        date_format="YYYY-MM-DD",
        datetime_format="YYYY-MM-DD HH:MM:SS"
    ) as writer:
        for d in df_list:
            df = d[0]
            sheet = d[1]
            df.to_excel( writer,
                sheet_name=sheet,
                index=False
                )
    return xl_buffer.getvalue()


start_year = pc.START_ACADEMIC_YEAR

current_yt_df = pc.current_yearterm()
current_term = current_yt_df['term'].iloc[0]
current_year = current_yt_df['year'].iloc[0]
current_yt = current_yt_df['yearterm'].iloc[0]
current_yt_sort = current_yt_df['yearterm_sort'].iloc[0]


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Registrar - Course Completion Rates ..."):
        src.pages.components.page_header()
        st.write(
            """
            ## Registrar - Course Completion Rates
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

        section_types = ['COMB', 'HYBD', 'LEC', 'ONLN', 'PRAC', 'LAB', 'SI']
        include_section_types = st.multiselect("Include section types:", options=section_types, default=['COMB', 'HYBD', 'LEC', 'ONLN', 'PRAC'])


        if year_start and year_end and include_section_types:

            academic = pc.select("ACADEMIC",
                fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION',
                    'PROGRAM', 'DEGREE', 'CURRICULUM', 'COLLEGE', 'DEPARTMENT', 'CLASS_LEVEL', 'POPULATION',
                    'FULL_PART', 'ACADEMIC_STANDING', 'ENROLL_SEPARATION', 'SEPARATION_DATE', 'CREDITS',  
                    'COLLEGE_ATTEND', 'STATUS', 'PRIMARY_FLAG',
                    ],
                where=f"ACADEMIC_YEAR>='{int(year_start)}' and ACADEMIC_YEAR<='{int(year_end)}' and ACADEMIC_TERM IN ('FALL', 'SPRING') " +
                    "and ACADEMIC_SESSION='' and CREDITS>0 and CURRICULUM<>'ADVST' ", 
                distinct=True,
            )

            transcriptdetail = pc.select("TRANSCRIPTDETAIL",
                fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION',
                    'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION', 'EVENT_TYPE', 'EVENT_MED_NAME', 'EVENT_LONG_NAME',
                    'CREDIT', 'FINAL_GRADE', 'ADD_DROP_WAIT',
                    ],
                where=f"ACADEMIC_YEAR>='{int(year_start)}' and ACADEMIC_YEAR<='{int(year_end)}' and ACADEMIC_TERM IN ('FALL', 'SPRING') " +
                    "and ADD_DROP_WAIT='A' and CREDIT>0 ", 
            )
            transcriptdetail = transcriptdetail.loc[(transcriptdetail['EVENT_SUB_TYPE'].isin(include_section_types))]

            atd = academic.merge(transcriptdetail,
                how='left',
                on=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', ]
                )
            atd = pc.add_col_yearterm(atd)
            atd = pc.add_col_yearterm_sort(atd)
            atd = atd.loc[atd['yearterm_sort'] < current_yt_sort, ]
            atd["EVENT_ID"] = atd["EVENT_ID"].str.rstrip().str.upper()
            atd['course_section_id'] = (
                atd["ACADEMIC_YEAR"] + "."  + 
                atd["ACADEMIC_TERM"].str.title()  + "."  + 
                atd["EVENT_ID"].str.rstrip().str.upper() + "." + 
                atd["EVENT_SUB_TYPE"].str.upper() + "."  + 
                atd["SECTION"].str.upper()
                )
            atd['student_course_id'] = atd['PEOPLE_CODE_ID'] + "." + atd['course_section_id']
            atd = atd.rename(columns={'EVENT_ID': 'course', }) 
            keep_cols = [
                'PEOPLE_CODE_ID', 'yearterm', 'yearterm_sort', 'course', 'course_section_id', 'student_course_id', 'FINAL_GRADE',
            ]
            atd = atd.loc[~atd['FINAL_GRADE'].isin(['TR', 'AU']), keep_cols]
            atd = atd.drop_duplicates(['student_course_id', ])

            # st.dataframe(atd.loc[(atd['course'] == 'ENG 101') & (atd['yearterm'] == '2025.Spring'), ])

            grade_mapping = [
                ["A+",   "A+", 1, 0],
                ["A+*",  "A+", 1, 0],
                ["A",    "A", 1, 0],
                ["A*",   "A", 1, 0 ],
                ["B+",   "B+", 1, 0],
                ["B+*",  "B+", 1, 0],
                ["B",    "B", 1, 0],
                ["B*",   "B", 1, 0],
                ["C+",   "C+", 1, 0],
                ["C+*",  "C+", 1, 0],
                ["C",    "C", 1, 0],
                ["C*",   "C", 1, 0],
                ["D+",   "D+", 1, 0],
                ["D+*",  "D+", 1, 0],
                ["D",    "D", 1, 1],
                ["D*",   "D", 1, 1],
                ["F",    "F", 0, 1],
                ["F*",   "F", 0, 1],
                ["P",    "P", 1, 0],
                ["P*",   "P", 1, 0],
                ["DEF",  "INC", 0, 0],
                ["INC",  "INC", 0, 0],
                ["INC*", "INC", 0, 0],
                ["W",    "W", 0, 1],
                ["W*",   "W", 0, 1],
                ["WF",   "W", 0, 1],
                ["WF*",  "W", 0, 1],
                ["WP",   "W", 0, 1],
                ["WP*",  "W", 0, 1],
            ]
            grades = pd.DataFrame(
                grade_mapping,
                columns=['pc_grade', 'grade', 'pass', 'dfw',]
            )
            atd = atd.merge(grades,
                how='left',
                left_on='FINAL_GRADE',
                right_on='pc_grade'
                )
            
            term_df = ( atd.drop_duplicates(['yearterm_sort', 'yearterm'])
                .sort_values(['yearterm_sort'], ascending=True)
                .loc[:,['yearterm_sort', 'yearterm']]
                )
            terms = term_df['yearterm'].unique()

            # st.dataframe(atd.loc[(atd['course'] == 'ENG 101') & (atd['yearterm'] == '2025.Spring'), ])
            # st.dataframe(atd.loc[(atd['course'] == 'CPT 100'), ])


            st.write(f"#### Course Completion Rates by Year.Term ({year_start}-{year_end})")

            g = ( atd[['yearterm', 'yearterm_sort', 'course', 'PEOPLE_CODE_ID', 'pass', 'dfw']].groupby(['yearterm', 'course', ]).agg(
                    {'yearterm_sort': 'first', 'PEOPLE_CODE_ID': 'count', 'pass': 'sum', 'dfw': 'sum' }
                )
                .rename(columns={'PEOPLE_CODE_ID': 'count', 'pass': 'pass_count', 'dfw': 'dfw_count' })
            )
            g['pass_rate'] = g['pass_count'] / g['count']
            g['dfw_rate'] = g['dfw_count'] / g['count']
            g = g.sort_values(['yearterm_sort', 'course'], ascending=True)
            gs = g.drop(columns=['yearterm_sort', ])
            g = g.reset_index()
            st.dataframe(gs)
            gs = gs.reset_index()
            st.download_button(
                label="Download data as CSV",
                data=convert_df(gs),
                file_name=f"{year_start}-{year_end}_course_completion_rates_{today_str}.csv",
                mime='text/csv',
            )


            st.markdown("---")
            st.write(f"#### Course Pass Rates by Term ({year_start}-{year_end})")
            pass_rate = ( gs.pivot(
                    index='course', 
                    columns='yearterm',
                    values='pass_rate'
                    )
            )
            pass_rate = pass_rate.loc[:,terms]
            st.dataframe(pass_rate)
            pass_rate = pass_rate.reset_index()
            st.download_button(
                label="Download data as CSV",
                data=convert_df(pass_rate),
                file_name=f"{year_start}-{year_end}_course_pass_rates_{today_str}.csv",
                mime='text/csv',
            )


            st.markdown("---")
            st.write(f"#### Course DFW Rates by Term ({year_start}-{year_end})")
            dfw_rate = ( gs.pivot(
                    index='course', 
                    columns='yearterm',
                    values='dfw_rate'
                    )
            )
            dfw_rate = dfw_rate.loc[:,terms]
            st.dataframe(dfw_rate)
            dfw_rate = dfw_rate.reset_index()
            st.download_button(
                label="Download data as CSV",
                data=convert_df(dfw_rate),
                file_name=f"{year_start}-{year_end}_course_dfw_rates_{today_str}.csv",
                mime='text/csv',
            )


            # Overall Pass/DFW rates
            st.markdown("---")
            st.write(f"#### Overall (for all courses) course completion rate table by term for period {year_start}-{year_end}")

            overall = ( atd[['yearterm', 'yearterm_sort', 'student_course_id', 'pass', 'dfw']].groupby(['yearterm' ]).agg(
                    {'yearterm_sort': 'first', 'student_course_id': 'count', 'pass': 'sum', 'dfw': 'sum' }
                )
                .rename(columns={'student_course_id': 'count', 'pass': 'pass_count', 'dfw': 'dfw_count' })
            )
            overall['pass_rate'] = overall['pass_count'] / overall['count']
            overall['dfw_rate'] = overall['dfw_count'] / overall['count']
            overall = overall.sort_values(['yearterm_sort'], ascending=True).drop(columns=['yearterm_sort', ])
            overall = overall.loc[(overall['pass_count']!=0)&(overall['dfw_count']!=0), ]
            st.dataframe(overall)
            overall = overall.reset_index()
            st.download_button(
                label="Download data as CSV",
                data=convert_df(overall),
                file_name=f"{year_start}-{year_end}_overall_course_completion_rates_{today_str}.csv",
                mime='text/csv',
            )
            st.write(" ")
            c = alt.Chart(overall, title=alt.TitleParams(
                    text='Overall Course Pass Rates by Term',
                    subtitle=f'{year_start}-{year_end}',
                    )).mark_line().encode(
                        x=alt.X('yearterm:N', sort=terms, axis=alt.Axis(title='Year.Term'), ),
                        y=alt.Y('pass_rate:Q', axis=alt.Axis(title='Pass Rate', format='.0%'), scale=alt.Scale(zero=False)),
                        tooltip=['yearterm', alt.Tooltip('pass_rate:Q', title='pass_rate', format='.2%')],
                    )
            max_pass_rate = overall['pass_rate'].max()
            c = c + alt.Chart(pd.DataFrame({'y_max': [max_pass_rate]})).mark_rule(strokeDash=[5,5], color='red').encode(y='y_max')
            # max_pass_rate_yearterm = overall.loc[overall['pass_rate']==max_pass_rate, 'yearterm'].iloc[0]
            # c = c + alt.Chart(pd.DataFrame({'y_max': [max_pass_rate], 'x_max': [max_pass_rate_yearterm]})).mark_text(
            #     align='left',
            #     baseline='bottom',
            #     dx=3,
            #     dy=-3,
            #     color='red',
            #     ).encode(
            #         y='y_max:Q',
            #         x='x_max:N',
            #         text=alt.value(f'Highest pass rate: {max_pass_rate:.1%} in {max_pass_rate_yearterm}'),
            #     )
            min_pass_rate = overall['pass_rate'].min()
            c = c + alt.Chart(pd.DataFrame({'y_min': [min_pass_rate]})).mark_rule(strokeDash=[5,5], color='blue').encode(y='y_min')
            # min_pass_rate_yearterm = overall.loc[overall['pass_rate']==min_pass_rate, 'yearterm'].iloc[0]
            # c = c + alt.Chart(pd.DataFrame({'y_min': [min_pass_rate], 'x_min': [min_pass_rate_yearterm]})).mark_text(
            #     align='left',
            #     baseline='top',
            #     dx=3,
            #     dy=3,
            #     color='blue',
            #     ).encode(
            #         y='y_min:Q',
            #         x='x_min:N',
            #         text=alt.value(f'Lowest pass rate: {min_pass_rate:.1%} in {min_pass_rate_yearterm}'),
            #     )
            st.altair_chart(c)
            st.write(" ")
            c = alt.Chart(overall, title=alt.TitleParams(
                    text='Overall Course DFW Rates by Term',
                    subtitle=f'{year_start}-{year_end}',
                    )).mark_line().encode(
                        x=alt.X('yearterm:N', sort=terms, axis=alt.Axis(title='Year.Term'), ),
                        y=alt.Y('dfw_rate:Q', axis=alt.Axis(title='DFW Rate', format='.0%'), scale=alt.Scale(zero=False)),
                        tooltip=['yearterm', alt.Tooltip('dfw_rate:Q', title='DFW_rate', format='.2%')],
                    )
            max_dfw_rate = overall['dfw_rate'].max()
            c = c + alt.Chart(pd.DataFrame({'y_max': [max_dfw_rate]})).mark_rule(strokeDash=[5,5], color='red').encode(y='y_max')
            # max_dfw_rate_yearterm = overall.loc[overall['dfw_rate']==max_dfw_rate, 'yearterm'].iloc[0]
            # c = c + alt.Chart(pd.DataFrame({'y_max': [max_dfw_rate], 'x_max': [max_dfw_rate_yearterm]})).mark_text(
            #     align='left',
            #     baseline='bottom',
            #     dx=3,
            #     dy=-3,
            #     color='red',
            #     ).encode(
            #         y='y_max:Q',
            #         x='x_max:N',
            #         text=alt.value(f'Highest DFW rate: {max_dfw_rate:.1%} in {max_dfw_rate_yearterm}'),
            #     )
            min_dfw_rate = overall['dfw_rate'].min()
            c = c + alt.Chart(pd.DataFrame({'y_min': [min_dfw_rate]})).mark_rule(strokeDash=[5,5], color='blue').encode(y='y_min')
            # min_dfw_rate_yearterm = overall.loc[overall['dfw_rate']==min_dfw_rate, 'yearterm'].iloc[0]
            # c = c + alt.Chart(pd.DataFrame({'y_min': [min_dfw_rate], 'x_min': [min_dfw_rate_yearterm]})).mark_text(
            #     align='left',
            #     baseline='top',
            #     dx=3,
            #     dy=3,
            #     color='blue',
            #     ).encode(
            #         y='y_min:Q',
            #         x='x_min:N',
            #         text=alt.value(f'Lowest DFW rate: {min_dfw_rate:.1%} in {min_dfw_rate_yearterm}'),
            #     )
            st.altair_chart(c)


            # Get top 10 courses by lowest pass_rate in each term
            st.markdown("---")
            st.write(f"#### Bottom 10 courses (with at least 8 students) by lowest Pass rate in each term {year_start}-{year_end} ")
            bottom10_list = []
            for t in terms:
                d = g.loc[(g['yearterm']==t)&(g['count']>=8), ['yearterm', 'yearterm_sort', 'course', 'count', 'pass_count', 'pass_rate',] ]
                d = d.sort_values(['pass_rate', 'count'], ascending=[True, False]).head(10)
                bottom10_list.append(d)
            bottom10 = pd.concat(bottom10_list, axis=0)
            bottom10 = bottom10.sort_values(['yearterm_sort', 'pass_rate', 'count'], ascending=[True, True, False]).drop(columns=['yearterm_sort', ])
            st.dataframe(bottom10)
            bottom10 = bottom10.reset_index(drop=True)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(bottom10),
                file_name=f"{year_start}-{year_end}_bottom10_course_pass_rates_{today_str}.csv",
                mime='text/csv',
            )


            # Get top 10 courses by highest dfw_rate in each term
            st.markdown("---")
            st.write(f"#### Top 10 courses (with at least 8 students) by highest DFW rate in each term {year_start}-{year_end} ")
            top10_list = []
            for t in terms:
                d = g.loc[(g['yearterm']==t)&(g['count']>=8), ['yearterm', 'yearterm_sort', 'course', 'count', 'dfw_count', 'dfw_rate',] ]
                d = d.sort_values(['dfw_rate', 'count'], ascending=[False, False]).head(10)
                top10_list.append(d)
            top10 = pd.concat(top10_list, axis=0)
            top10 = top10.sort_values(['yearterm_sort', 'dfw_rate', 'count'], ascending=[True, False, False]).drop(columns=['yearterm_sort', ])
            st.dataframe(top10)
            top10 = top10.reset_index(drop=True)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(top10),
                file_name=f"{year_start}-{year_end}_top10_course_dfw_rates_{today_str}.csv",
                mime='text/csv',
            )


            # find course with lowest pass rate with at least 10 students over the entire period
            st.markdown("---")
            st.write(f"#### Course with lowest pass rate (for courses with at least 10 students) for the period {year_start}-{year_end}")
            course_overall = ( atd[['course', 'student_course_id', 'pass', 'dfw']].groupby(['course' ]).agg(
                    {'student_course_id': 'count', 'pass': 'sum', 'dfw': 'sum' }
                )
                .rename(columns={'student_course_id': 'count', 'pass': 'pass_count', 'dfw': 'dfw_count' })
            )
            course_overall['pass_rate'] = course_overall['pass_count'] / course_overall['count']
            course_overall['dfw_rate'] = course_overall['dfw_count'] / course_overall['count']
            course_overall = course_overall.sort_values(['pass_rate', 'count'], ascending=[True, False])
            course_overall = course_overall.loc[(course_overall['count']>=10)&(course_overall['pass_count']>0)&(course_overall['dfw_count']>0), ]
            if not course_overall.empty:
                lowest_pass_course = course_overall.iloc[0]
                lowest_pass_course_name = lowest_pass_course.name
                lowest_pass_rate = lowest_pass_course['pass_rate']
                lowest_pass_count = lowest_pass_course['pass_count']
                lowest_total_count = lowest_pass_course['count']
                st.write(f"The course with the lowest pass rate from {year_start} to {year_end} is **{lowest_pass_course_name}** with a pass rate of **{lowest_pass_rate:.1%}** " +
                    f"({lowest_pass_count:0} passes out of {lowest_total_count:0} students).")
            else:
                st.write("No courses with at least 10 students found.")
            if not course_overall.empty:
                c = alt.Chart(course_overall.head(20).reset_index(), title=alt.TitleParams(
                        text='Courses with Lowest Pass Rates',
                        subtitle=f'{year_start}-{year_end} (for courses with at least 10 students)',
                        )).mark_bar().encode(
                            y=alt.Y('course:N', sort='-x', axis=alt.Axis(title='Course'), ),
                            x=alt.X('pass_rate:Q', axis=alt.Axis(title='Pass Rate', format='.0%'), scale=alt.Scale(domain=[0, 1])),
                            tooltip=['course', 'count', 'pass_count', alt.Tooltip('pass_rate:Q', title='pass_rate', format='.2%')],
                        )
                # max_pass_rate = course_overall['pass_rate'].max()
                # c = c + alt.Chart(pd.DataFrame({'x_max': [max_pass_rate]})).mark_rule(strokeDash=[5,5], color='red').encode(x='x_max')
                # min_pass_rate = course_overall['pass_rate'].min()
                # c = c + alt.Chart(pd.DataFrame({'x_min': [min_pass_rate]})).mark_rule(strokeDash=[5,5], color='blue').encode(x='x_min')
                st.altair_chart(c)
            course_overall = course_overall.reset_index()
            st.download_button(
                label="Download data as CSV",
                data=convert_df(course_overall),
                file_name=f"{year_start}-{year_end}_course_overall_pass_rates_{today_str}.csv",
                mime='text/csv',
            )

            # Export to Excel
            st.markdown("---")
            st.write(f"#### {year_start}-{year_end} Excel workbook with all course completion rate tables")

            df_to_add = [
                    [pass_rate, 'pass_rate'],
                    [dfw_rate, 'dfw_rate'],
                    [g, 'all data'],
                    [overall, 'overall'],
                    [top10, 'top10_dfw' ],
                    [bottom10, 'bottom10_pass' ],
                    [course_overall, 'course_overall'],
            ]
            st.download_button(
                label=f"Download Excel workbook for {year_start}-{year_end} as .xlsx",
                data=convert_df_xlsx(df_to_add),
                file_name=f"{year_start}-{year_end}_course_completion_rates_{today_str}.xlsx",
                mime='application/vnd.ms-excel',
            )


