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
def class_df(start_year):
    sections = pc.select("SECTIONS", 
        fields=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',
            'EVENT_MED_NAME', 'EVENT_LONG_NAME', 'EVENT_TYPE', 
            'START_DATE', 'END_DATE',
            ],
        where=f"ACADEMIC_YEAR>='{start_year}' AND ACADEMIC_TERM IN ('FALL', 'SPRING') " +
            "and ADDS>0 and EVENT_STATUS='A' " +
            "and EVENT_SUB_TYPE NOT IN ('ONLN') ", 
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
    sections = sections.loc[(~sections['SECTION'].str.contains('ON'))]

    sectionschedule = pc.select("SECTIONSCHEDULE", 
        fields=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',
            'DAY', 'START_TIME', 'END_TIME', 'BUILDING_CODE', 'ROOM_ID' ],
        where=f"ACADEMIC_YEAR>='{start_year}' AND ACADEMIC_TERM IN ('FALL', 'SPRING') ",
        )

    sections = sections.merge(sectionschedule,
        how='left',
        on=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',]
        )
    sections['building_room'] = (
        sections["BUILDING_CODE"].str.upper() + "_" + 
        sections["ROOM_ID"].str.upper()
        )
    sections = sections.loc[(sections['DAY'].notna())]

    transcriptdetail = pc.select("TRANSCRIPTDETAIL",
        fields=['PEOPLE_CODE_ID', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION',
            'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION', 'EVENT_TYPE',
            'CREDIT', 'MID_GRADE', 'FINAL_GRADE', 'ADD_DROP_WAIT',
            ],
        where=f"ACADEMIC_YEAR>='{start_year}' AND ACADEMIC_TERM IN ('FALL', 'SPRING') " +
            "and ADD_DROP_WAIT='A' ", 
    )

    std = sections.merge(transcriptdetail,
        how='left',
        on=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',]
        )
    std = std.loc[~(std['DAY'].isin(['CANC', 'ONLN', 'TBD']))]

    code_day = pc.select('CODE_DAY',
        fields=['CODE_VALUE_KEY', 'DAY_SUNDAY', 'DAY_MONDAY', 'DAY_TUESDAY', 'DAY_WEDNESDAY', 'DAY_THURSDAY', 'DAY_FRIDAY', 'DAY_SATURDAY', ],
        )
    code_day = ( pd.melt(code_day, id_vars=['CODE_VALUE_KEY'], value_vars=['DAY_SUNDAY', 'DAY_MONDAY', 'DAY_TUESDAY', 'DAY_WEDNESDAY', 'DAY_THURSDAY', 'DAY_FRIDAY', 'DAY_SATURDAY', ],
                        var_name='DAY', value_name='DAY_BOOL'    
        )
        .replace({ 'DAY': {
            'DAY_SUNDAY': 'SUN',
            'DAY_MONDAY': 'MON',
            'DAY_TUESDAY': 'TUE',
            'DAY_WEDNESDAY': 'WED',
            'DAY_THURSDAY': 'THU',
            'DAY_FRIDAY': 'FRI',
            'DAY_SATURDAY': 'SAT',
            } }
        )
    )
    code_day = code_day.loc[(code_day['DAY_BOOL']=='Y'),:]

    keep_cols = ['yearterm', 'ACADEMIC_YEAR', 'ACADEMIC_TERM', 'section_id', 'EVENT_SUB_TYPE', 'PEOPLE_CODE_ID', 'building_room', 'DAY', 'START_TIME', 'END_TIME']
    std = ( std.merge(code_day,
            how='left',
            left_on='DAY',
            right_on='CODE_VALUE_KEY'
            )
        .rename( columns={
                'DAY_y': 'DAY'
                }
            )
        .loc[:,keep_cols]
    )
    std['building_room_day'] = (
        std["building_room"] + "_" + 
        std["DAY"].str.upper()
        )
    std = std.loc[(std['DAY'].notna())]
    std = std.drop_duplicates(['yearterm', 'section_id', 'EVENT_SUB_TYPE', 'PEOPLE_CODE_ID', 'DAY', 'START_TIME', 'END_TIME' ])
    std['join'] = 1

    sample_time = pd.DataFrame(pd.date_range(start='1900-01-01 06:00:0.0', end='1900-01-01 22:00:0.0', freq='15min'),
        columns=['t'])
    sample_time['join'] = 1
    sample_time['time'] = sample_time['t'].dt.strftime('%H:%M')

    std = std.merge(sample_time,
            how='left',
            on='join',
            )
    std['in_class'] = ((std['t'] >= std['START_TIME']) & (std['t'] <= std['END_TIME']))
    std = std.loc[(std['in_class'])]

    return std


start_year = pc.START_ACADEMIC_YEAR

current_yt_df = pc.current_yearterm()
current_term = current_yt_df['term'].iloc[0]
current_year = current_yt_df['year'].iloc[0]
current_yt = current_yt_df['yearterm'].iloc[0]
current_yt_sort = current_yt_df['yearterm_sort'].iloc[0]

day_list = ['MON', 'TUE', 'WED', 'THU', 'FRI', 'SAT', 'SUN']


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Registrar - Class Times ..."):
        src.pages.components.page_header()
        st.write(
            """
            ## Registrar - Class Times
"""
        )

        today = dt.datetime.today()
        today_str = today.strftime("%Y%m%d_%H%M")

        calendar = pc.select("ACADEMICCALENDAR",
            fields=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 
                'START_DATE', 'END_DATE', 'FINAL_END_DATE' ], 
            where=f"ACADEMIC_YEAR>='{start_year}' AND ACADEMIC_TERM IN ('FALL', 'SPRING') ", 
            distinct=True
            )
        calendar = pc.add_col_yearterm(calendar)
        calendar = pc.add_col_yearterm_sort(calendar)
        term_df = ( calendar.drop_duplicates(['yearterm_sort', 'yearterm'])
                        .sort_values(['yearterm_sort'], ascending=False)
                        .loc[:,['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'yearterm_sort', 'yearterm']]
        )
        term_list = term_df['yearterm'].tolist()

        st.write(f"### One Term")

        if current_yt in term_list:
            ind = term_list.index(current_yt)
        else:
            ind = 0
        yearterm = st.selectbox(label="Selected term:", options=term_list, index=ind)

        term_df = term_df.set_index('yearterm')
        year = term_df.loc[[yearterm]]['ACADEMIC_YEAR'][0]
        term = term_df.loc[[yearterm]]['ACADEMIC_TERM'][0]

        section_types = ['COMB', 'HYBD', 'LEC', 'PRAC', 'LAB', 'SI']
        include_section_types = st.multiselect("Include section types:", options=section_types, default=['COMB', 'HYBD', 'LEC', 'PRAC', 'LAB', 'SI'])

        df = class_df(start_year)

        if yearterm and include_section_types:

            df_yt = df.loc[(df['yearterm']==yearterm) & (df['EVENT_SUB_TYPE'].isin(include_section_types))]

            day_order = [d for d in day_list if d in df_yt['DAY'].unique()]

            st.write(f"#### Number of Students In-Class ({yearterm})")
            stu = ( df_yt.loc[:,['PEOPLE_CODE_ID', 'DAY', 'time' ]]
                    .drop_duplicates(['PEOPLE_CODE_ID', 'DAY', 'time' ])
                    .groupby(['DAY', 'time'])['PEOPLE_CODE_ID'].count()
                    .fillna(0)
                    .reset_index()
                    .rename(
                        columns={
                            'PEOPLE_CODE_ID': 'students'
                        }
                    )
            )
            c1 = alt.Chart(stu).mark_line().encode(
                x='time:N',
                y=alt.Y('students:Q', axis=alt.Axis(title='Student Count'), impute=alt.ImputeParams(value=0)),
                color=alt.Color('DAY:N', sort=day_order),
                tooltip=['DAY:N', 'time:N', alt.Tooltip('students:Q', title='student count'), ],
            )
            st.altair_chart(c1)
            stu = ( stu.pivot(
                        index='time', 
                        columns='DAY',
                        values='students'
                    )
                    .reset_index()
                    .fillna(0)
            )
            stu = stu.loc[:,['time'] + day_order]
            stu[day_order] = stu[day_order].astype(int)
            st.dataframe(stu)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(stu),
                file_name=f"{term}{year}_students_by_classtime.csv",
                mime='text/csv',
            )

            st.write(f"#### Number of Sections ({yearterm})")
            sect = ( df_yt.loc[:,['DAY', 'time', 'section_id' ]]
                    .drop_duplicates(['DAY', 'time', 'section_id' ])
                    .groupby(['DAY', 'time'])['section_id'].count()
                    .fillna(0)
                    .reset_index()
                    .rename(
                        columns={
                            'section_id': 'sections'
                        }
                    )
            )
            c2 = alt.Chart(sect).mark_line().encode(
                x='time:N',
                y=alt.Y('sections:Q', axis=alt.Axis(title='Section Count'), impute=alt.ImputeParams(value=0)),
                color=alt.Color('DAY:N', sort=day_order),
                tooltip=['DAY:N', 'time:N', alt.Tooltip('sections:Q', title='sections count'), ],
            )
            st.altair_chart(c2)
            sect = ( sect.pivot(
                        index='time', 
                        columns='DAY',
                        values='sections'
                    )
                    .reset_index()
                    .fillna(0)
            )
            sect = sect.loc[:,['time'] + day_order]
            sect[day_order] = sect[day_order].astype(int)
            st.dataframe(sect)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(sect),
                file_name=f"{term}{year}_sections_by_classtime.csv",
                mime='text/csv',
            )
        
        st.markdown("---")

        st.write(f"### Multiple Terms")

        year_list = reversed(term_df['ACADEMIC_YEAR'].unique().tolist())
        year_start, year_end = st.select_slider(
            "Select range of years:",
            options=year_list,
            value=('2012', current_year),
            key='Class Times Multiple Terms Slider'
        )

        term = st.selectbox(label="Select term:", options=['Fall', 'Spring'])

        day = st.selectbox(
            "Select day:",
            day_list,
        )

        include_section_types_2 = st.multiselect("Include section types:", options=section_types, default=include_section_types, key='Class Times Multiple Terms MultiSelect')

        if year_start and year_end and term and day and include_section_types_2:

            df_day = df.loc[(df['DAY']==day) & 
                (df['EVENT_SUB_TYPE'].isin(include_section_types_2) &
                (df['ACADEMIC_YEAR']>=year_start) &
                (df['ACADEMIC_YEAR']<=year_end) &
                (df['ACADEMIC_TERM']==term.upper())
                )]
            
            st.write(f"#### Number of Students In-Class ({term} {year_start}-{year_end}) Day={day}")
            stu = ( df_day.loc[:,['PEOPLE_CODE_ID', 'yearterm', 'time' ]]
                    .drop_duplicates(['PEOPLE_CODE_ID', 'yearterm', 'time' ])
                    .groupby(['yearterm', 'time'])['PEOPLE_CODE_ID'].count()
                    .fillna(0)
                    .reset_index()
                    .rename(
                        columns={
                            'PEOPLE_CODE_ID': 'students'
                        }
                    )
            )
            yearterm_list = stu['yearterm'].unique().tolist()
            c1m = alt.Chart(stu).mark_line().encode(
                x='time:N',
                y=alt.Y('students:Q', axis=alt.Axis(title='Student Count'), impute=alt.ImputeParams(value=0)),
                color=alt.Color('yearterm:N', sort=day_order),
                tooltip=['yearterm:N', 'time:N', alt.Tooltip('students:Q', title='student count'), ],
            )
            st.altair_chart(c1m)
            stu = ( stu.pivot(
                        index='time', 
                        columns='yearterm',
                        values='students'
                    )
                    .reset_index()
                    .fillna(0)
            )
            stu = stu.loc[:,['time'] + yearterm_list]
            stu[yearterm_list] = stu[yearterm_list].astype(int)
            st.dataframe(stu)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(stu),
                file_name=f"{term}{year_start}-{year_end}_{day}_students_by_classtime.csv",
                mime='text/csv',
            )

            st.write(f"#### Number of Sections ({term} {year_start}-{year_end}) Day={day}")
            sect = ( df_day.loc[:,['yearterm', 'time', 'section_id' ]]
                    .drop_duplicates(['yearterm', 'time', 'section_id' ])
                    .groupby(['yearterm', 'time'])['section_id'].count()
                    .fillna(0)
                    .reset_index()
                    .rename(
                        columns={
                            'section_id': 'sections'
                        }
                    )
            )
            yearterm_list = sect['yearterm'].unique().tolist()
            c2m = alt.Chart(sect).mark_line().encode(
                x='time:N',
                y=alt.Y('sections:Q', axis=alt.Axis(title='Section Count'), impute=alt.ImputeParams(value=0)),
                color=alt.Color('yearterm:N', sort=day_order),
                tooltip=['yearterm:N', 'time:N', alt.Tooltip('sections:Q', title='sections count'), ],
            )
            st.altair_chart(c2m)
            sect = ( sect.pivot(
                        index='time', 
                        columns='yearterm',
                        values='sections'
                    )
                    .reset_index()
                    .fillna(0)
            )
            sect = sect.loc[:,['time'] + yearterm_list]
            sect[yearterm_list] = sect[yearterm_list].astype(int)
            st.dataframe(sect)
            st.download_button(
                label="Download data as CSV",
                data=convert_df(sect),
                file_name=f"{term}{year_start}-{year_end}_{day}_sections_by_classtime.csv",
                mime='text/csv',
            )

