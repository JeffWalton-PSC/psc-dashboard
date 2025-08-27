import pandas as pd
import streamlit as st
import datetime as dt
import io
import src.pages.components

# PowerCampus utilities
import powercampus as pc

start_year = pc.START_ACADEMIC_YEAR

current_yt_df = pc.current_yearterm()
current_term = current_yt_df['term'].iloc[0]
current_year = current_yt_df['year'].iloc[0]
current_yt = current_yt_df['yearterm'].iloc[0]
current_yt_sort = current_yt_df['yearterm_sort'].iloc[0]


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


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Registrar - Course Scheduling ..."):
        src.pages.components.page_header()
        st.write(
            """
            ## Registrar - Course Scheduling
"""
        )

        today = dt.datetime.today()
        today_str = today.strftime("%Y%m%d_%H%M")
        st.write(f"{today.strftime('%Y-%m-%d %H:%M')}")
        # st.dataframe(current_yt_df)

        calendar = pc.select("ACADEMICCALENDAR",
            fields=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 
                'START_DATE', 'END_DATE', 'FINAL_END_DATE' ], 
            where=f"ACADEMIC_YEAR>='{start_year}' AND ACADEMIC_TERM IN ('FALL', 'SPRING', 'SUMMER')", 
            distinct=True
            )
        calendar = pc.add_col_yearterm(calendar)
        calendar = pc.add_col_yearterm_sort(calendar)
        term_df = ( calendar.drop_duplicates(['yearterm_sort', 'yearterm'])
                        .sort_values(['yearterm_sort'], ascending=False)
                        .loc[:,['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'yearterm_sort', 'yearterm']]
        )
        term_list = term_df['yearterm'].tolist()
        yearterm = st.selectbox(label="Selected term:", options=term_list, index=term_list.index(current_yt))

        term_df = term_df.set_index('yearterm')
        year = term_df.loc[[yearterm]]['ACADEMIC_YEAR'][0]
        term = term_df.loc[[yearterm]]['ACADEMIC_TERM'][0]

        if year and term:

            sections = pc.select("SECTIONS", 
                fields=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',
                    'EVENT_LONG_NAME', 'COLLEGE', 'EVENT_STATUS', 'CREDITS', 'MAX_PARTICIPANT', 'ADDS', 'WAIT_LIST', 
                    'START_DATE', 'END_DATE'],
                where=f"ACADEMIC_YEAR='{int(year)}' and ACADEMIC_TERM='{term}' and EVENT_STATUS='A' ", 
                )

            sectionper = pc.select("SECTIONPER", 
                fields=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',
                    'PERSON_CODE_ID'],
                where=f"ACADEMIC_YEAR='{int(year)}' and ACADEMIC_TERM='{term}' ",
                )

            people = pc.select('PEOPLE',
                fields=['PEOPLE_CODE_ID', 'FIRST_NAME', 'LAST_NAME', 'PrimaryEmailId', ],
                where="DECEASED_FLAG<>'Y' and BIRTH_DATE>'1899-01-01' and BIRTH_DATE<'2500-01-01'",
                )
            people['PrimaryEmailId'] = people['PrimaryEmailId'].astype('UInt32')

            email = pc.select('EmailAddress',
                fields=['EmailAddressId', 'PeopleOrgCodeId', 'EmailType', 'Email', 'IsActive', ],
                where="IsActive=1 and EmailType='MLBX'",
                )
            email['EmailAddressId'] = email['EmailAddressId'].astype('UInt32')

            instructors = people.merge(email,
                how='inner',
                left_on='PrimaryEmailId',
                right_on='EmailAddressId'
                )

            sectionper = sectionper.merge(instructors,
                how='left',
                left_on='PERSON_CODE_ID',
                right_on='PEOPLE_CODE_ID'
                )

            sectionschedule = pc.select("SECTIONSCHEDULE", 
                fields=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',
                    'DAY', 'START_TIME', 'END_TIME', 'BUILDING_CODE', 'ROOM_ID' ],
                where=f"ACADEMIC_YEAR='{int(year)}' and ACADEMIC_TERM='{term}' ",
                )

            sections = sections.merge(sectionper,
                how='left',
                on=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',]
                ).merge(sectionschedule,
                how='left',
                on=['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION',]
                )

            sections['START_DATE'] = pd.to_datetime(sections['START_DATE']).dt.date
            sections['END_DATE'] = pd.to_datetime(sections['END_DATE']).dt.date
            sections['START_TIME_txt'] = pd.to_datetime(sections['START_TIME']).dt.strftime('%H:%M')
            sections['END_TIME_txt'] = pd.to_datetime(sections['END_TIME']).dt.strftime('%H:%M')
            
            # remove REG, ADV sections
            # drop and order columns
            sections = sections.loc[(~sections['EVENT_ID'].str.startswith('REG')) & (~sections['EVENT_SUB_TYPE'].isin(['ACE', 'ADV', 'CELL', 'STAB'])), :]
            sections = sections.drop_duplicates(['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION', 'DAY', 'START_TIME'])
            sections = sections.sort_values(['EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION', 'DAY', 'START_TIME'])

            # course schedule
            keep_cols = ['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_LONG_NAME', 'EVENT_SUB_TYPE', 'SECTION',
                    'DAY', 'START_TIME_txt', 'END_TIME_txt', 'ADDS', 'MAX_PARTICIPANT', 'WAIT_LIST', 'START_DATE', 'END_DATE',
                    'LAST_NAME', 'FIRST_NAME', 'Email', 'BUILDING_CODE', 'ROOM_ID', 'COLLEGE', 'CREDITS',  
                    ]
            schedule = sections.loc[:,keep_cols]

            st.write(f"#### {yearterm} Course Schedule")
            st.dataframe(schedule)
            st.download_button(
                label=f"Download course schedule for {yearterm} as CSV",
                data=convert_df(schedule),
                file_name=f"{term}{year}_course_schedule_{today_str}.csv",
                mime='text/csv',
            )

            st.markdown("---")

            # no room assigned
            st.write(f"#### {yearterm} No Room Assigned (only courses with students enrolled)")
            # remove ONLINE and buildings with no rooms
            no_room_assigned = sections.loc[((~sections['BUILDING_CODE'].isin(['ONLINE', 'FORCC', 'LAMBERT', 'SAWMILL', 'SUGARB'])) &
                    (sections['ADDS'] > 0) & 
                    (sections['DAY'].notna()) & 
                    (sections['BUILDING_CODE'].isna() | (sections['BUILDING_CODE']=='')  | ~(sections['BUILDING_CODE'].str.isalnum().fillna(False)) | 
                        sections['ROOM_ID'].isna() | (sections['ROOM_ID']=='') | ~(sections['ROOM_ID'].str.isalnum().fillna(False)) )
                    ), :]
            no_room_assigned = no_room_assigned.sort_values(['EVENT_ID', 'EVENT_SUB_TYPE', 'SECTION', 'DAY', 'START_TIME'])
            st.dataframe(no_room_assigned)
            st.write(f"{no_room_assigned.shape}")
            st.download_button(
                label=f"Download courses with no room assigned for {yearterm} as CSV",
                data=convert_df(no_room_assigned),
                file_name=f"{term}{year}_courses_no_room_assigned_{today_str}.csv",
                mime='text/csv',
            )

            st.markdown("---")

            # room conflicts
            st.write(f"#### {yearterm} Room Conflicts (only courses with students enrolled)")
            sections['course_id'] = (
                sections["EVENT_ID"].str.rstrip().str.upper() + "." + 
                sections["EVENT_SUB_TYPE"].str.upper() + "."  + 
                sections["SECTION"].str.upper()
                )
            sections['building_room'] = (
                sections["BUILDING_CODE"].str.upper() + "_" + 
                sections["ROOM_ID"].str.upper()
                )
            keep_cols = ['ACADEMIC_YEAR', 'ACADEMIC_TERM', 'ACADEMIC_SESSION', 'EVENT_ID', 'EVENT_LONG_NAME', 'EVENT_SUB_TYPE', 'SECTION',
                    'START_DATE', 'END_DATE', 'DAY', 'START_TIME', 'END_TIME', 'ADDS', 
                    'BUILDING_CODE', 'ROOM_ID', 'course_id', 'building_room'
                    ]
            s = sections.loc[((~sections['BUILDING_CODE'].isin(['ONLINE', 'FORCC', 'LAMBERT', 'SAWMILL', 'SUGARB'])) &
                    (sections['ADDS'] > 0) & 
                    (sections['BUILDING_CODE'].notna()) & 
                    (sections['ROOM_ID'].notna()) &
                    (~sections['DAY'].isin(['CANC', 'ONLN', 'TBD']))
                    ), 
                    keep_cols
                    ]

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

            keep_cols = ['course_id', 'building_room', 'START_DATE', 'END_DATE', 'DAY', 'START_TIME', 'END_TIME', 'ADDS']
            s1 = ( s.merge(code_day,
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
            s1['building_room_day'] = (
                s1["building_room"] + "_" + 
                s1["DAY"].str.upper()
                )

            s2 = s1.copy()
            c = ( s1.merge( s2,
                    how='outer',
                    on='building_room_day',
                    suffixes=('_1', '_2')
                    )
                .rename( columns={
                        'building_room_1': 'building_room',
                        'DAY_1': 'DAY'
                        }
                    )
                .drop(
                        ['building_room_2', 'DAY_2', 'ADDS_1', 'ADDS_2'],
                        axis='columns',
                    )
            )
            
            #     conflict tests
            # import time
            # t0 = time.perf_counter()
            c['same_course'] = (c['course_id_1'] == c['course_id_2'])
            # c['date_start_overlap'] = (c['START_DATE_1'] >= c['START_DATE_2']) & (c['START_DATE_1'] < c['END_DATE_2'])
            # c['date_end_overlap'] = (c['END_DATE_1'] <= c['END_DATE_2']) & (c['END_DATE_1'] > c['START_DATE_2'])
            # c['date_tot_overlap'] = (c['START_DATE_1'] <= c['START_DATE_2']) & (c['END_DATE_1'] >= c['END_DATE_2'])
            # c['date_overlap'] = (c['date_start_overlap'] == True) | (c['date_end_overlap'] == True) | (c['date_tot_overlap'] == True)
            #         alternatively, test "not overlaping"
            # c['date_overlap'] = ~( (c['END_DATE_1'] < c['START_DATE_2']) | (c['END_DATE_2'] < c['START_DATE_1']) )
            #             apply DeMorgan's Law (distribute the ~)
            c['date_overlap'] = ( (c['END_DATE_1'] >= c['START_DATE_2']) & (c['END_DATE_2'] >= c['START_DATE_1']) )
            # c['time_start_overlap'] = (c['START_TIME_1'] >= c['START_TIME_2']) & (c['START_TIME_1'] < c['END_TIME_2'])
            # c['time_end_overlap'] = (c['END_TIME_1'] <= c['END_TIME_2']) & (c['END_TIME_1'] > c['START_TIME_2'])
            # c['time_tot_overlap'] = (c['START_TIME_1'] <= c['START_TIME_2']) & (c['END_TIME_1'] >= c['END_TIME_2'])
            # c['time_overlap'] = (c['time_start_overlap'] == True) | (c['time_end_overlap'] == True) | (c['time_tot_overlap'] == True)
            # c['time_overlap'] = ~( (c['END_TIME_1'] < c['START_TIME_2']) | (c['END_TIME_2'] < c['START_TIME_1']) )
            c['time_overlap'] = ( (c['END_TIME_1'] >= c['START_TIME_2']) & (c['END_TIME_2'] >= c['START_TIME_1']) )
            # t1 = time.perf_counter()
            # st.write(f"{t0=}, {t1=}, {t1-t0=}")

            keep_cols = ['building_room', 'DAY', 'course_id_1', 'START_TIME_1', 'END_TIME_1', 'course_id_2', 'START_TIME_2', 'END_TIME_2',  
                        'START_DATE_1', 'END_DATE_1', 'START_DATE_2', 'END_DATE_2',                        
                        ]
            c = c.loc[((c['same_course'] == False) & (c['date_overlap'] == True) & (c['time_overlap'] == True)), keep_cols]
            c = c.sort_values(['building_room', 'DAY', 'course_id_1', 'course_id_2', 'START_TIME_1', 'START_TIME_2'])

            st.dataframe(c)
            st.write(f"{c.shape}")
            st.download_button(
                label=f"Download room conflicts for {yearterm} as CSV",
                data=convert_df(c),
                file_name=f"{term}{year}_room_conflicts_{today_str}.csv",
                mime='text/csv',
            )

            st.markdown("---")

            # daily room schedule
            st.write(f"#### {yearterm} Daily Room Schedule")

            s1['day_sort'] = s1['DAY'].fillna(8)
            daily_room_schedule = ( s1.replace({ 'day_sort': {
                    'SUN': 1,
                    'MON': 2,
                    'TUE': 3,
                    'WED': 4,
                    'THU': 5,
                    'FRI': 6,
                    'SAT': 7,
                    } }
                )
                .loc[:,['building_room', 'DAY', 'day_sort', 'START_TIME', 'END_TIME', 'course_id', 'ADDS']]
                .sort_values(['building_room', 'day_sort', 'START_TIME', ])
            )

            st.dataframe(daily_room_schedule)
            st.write(f"{daily_room_schedule.shape}")
            st.download_button(
                label=f"Download daily room schedule for {yearterm} as CSV",
                data=convert_df(daily_room_schedule),
                file_name=f"{term}{year}_daily_room_schedule_{today_str}.csv",
                mime='text/csv',
            )

            st.markdown("---")

            # teaching faculty
            st.write(f"#### {yearterm} Teaching Faculty")
            sections['course_section_id'] = (
                sections["EVENT_ID"].str.rstrip().str.upper() + "." + 
                sections["EVENT_SUB_TYPE"].str.upper() + "."  + 
                sections["ACADEMIC_YEAR"] + "."  + 
                sections["ACADEMIC_TERM"].str.title()  + "."  + 
                sections["SECTION"].str.upper()
                )
            teaching_faculty = (sections.drop_duplicates(['LAST_NAME', 'FIRST_NAME', 'course_section_id' ])
                                    .loc[:,[
                                        'LAST_NAME', 'FIRST_NAME', 'Email', 'course_section_id'
                                    ]]
            )
            teaching_faculty_gb = ( teaching_faculty.groupby(['LAST_NAME', 'FIRST_NAME', 'Email']).count()
                                        .rename(columns={
                                            'course_section_id': 'sections',
                                            }
                                        )
            )
            st.dataframe(teaching_faculty_gb)
            st.write(f"{teaching_faculty_gb.shape}")
            st.download_button(
                label=f"Download teaching faculty for {yearterm} as CSV",
                data=convert_df(teaching_faculty_gb.reset_index()),
                file_name=f"{term}{year}_teaching_faculty_{today_str}.csv",
                mime='text/csv',
            )

            st.markdown("---")

            # Export to Excel
            st.write(f"#### {yearterm} Excel workbook with all course scheduling tables")

            df_to_add = [
                    [schedule, 'course_schedule'],
                    [no_room_assigned, 'no_room_assigned'],
                    [c, 'room_conflicts'],
                    [daily_room_schedule, 'daily_room_schedule'],
                    [teaching_faculty_gb.reset_index(), 'teaching_faculty'],
            ]

            st.download_button(
                label=f"Download Excel workbook for {yearterm} as .xlsx",
                data=convert_df_xlsx(df_to_add),
                file_name=f"{term}{year}_course_scheduling_{today_str}.xlsx",
                mime='application/vnd.ms-excel',
            )
            

