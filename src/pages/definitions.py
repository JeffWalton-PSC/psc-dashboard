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
def curriculum_df() -> pd.DataFrame:

    df = pc.select("CODE_CURRICULUM", 
        fields=['CODE_VALUE_KEY', 'CODE_VALUE', 'SHORT_DESC', 'MEDIUM_DESC', 'LONG_DESC', 'FORMAL_TITLE'
            ],
        where=f"STATUS='A' " 
        )

    keep_flds = [
        "CODE_VALUE_KEY",
        "SHORT_DESC",
        "MEDIUM_DESC",
        "LONG_DESC",
        "FORMAL_TITLE",
    ]
    df = ( df.loc[:, keep_flds]
        .sort_values(keep_flds)
        .drop_duplicates(keep_flds, keep="last", )
        .rename(columns={'CODE_VALUE_KEY': 'academic_program_code',
                         })
        .reset_index()
        .drop('index', axis=1)
    )

    return df


@st.cache_data
def degree_mapping_df() -> pd.DataFrame:

    df = pc.select("DegreeMappingNsc", 
        fields=['AcademicYear','AcademicTerm','AcademicSession','Program','Degree','Curriculum','CipCode','CipYear',
                'ProgramCredentialLevel','PublishedProgramLength','ProgramLengthMeasurement','SpecialProgramIndicator',
                'WeeksInTitleIVAcademicYear','DefaultProgramBeginDate','IsGainfulEmployment'
            ],
        )

    keep_flds1 = [
        'AcademicYear','AcademicTerm','AcademicSession','Program','Degree','Curriculum','CipCode','CipYear',
        'ProgramCredentialLevel','PublishedProgramLength','ProgramLengthMeasurement','SpecialProgramIndicator',
        'WeeksInTitleIVAcademicYear','DefaultProgramBeginDate',
        ]
    sort_fields1 = [
        'Curriculum','Program','Degree','AcademicYear','CipYear',
    ]
    keep_flds2 = [
        'academic_program_code','Program','Degree','CipCode','CipYear',
        'ProgramCredentialLevel','PublishedProgramLength','ProgramLengthMeasurement','SpecialProgramIndicator',
        'WeeksInTitleIVAcademicYear','DefaultProgramBeginDate',
        ]
    sort_fields2 = [
        'Program','Degree','academic_program_code',
    ]
    df = ( df.loc[:, keep_flds1]
        .sort_values(sort_fields1)
        .rename(columns={'Curriculum': 'academic_program_code',
                         })
        .drop_duplicates(sort_fields2, keep="last", )
        .loc[:, keep_flds2]
        .sort_values(sort_fields2)
        .reset_index()
        .drop('index', axis=1)
    )

    return df


@st.cache_data
def ethnicity_df() -> pd.DataFrame:

    df = pc.select("CODE_ETHNICITY", 
        fields=['CODE_VALUE_KEY', 'CODE_VALUE', 'SHORT_DESC', 'MEDIUM_DESC', 'LONG_DESC',
            ],
        where=f"STATUS='A' " 
        )

    keep_flds = [
        "CODE_VALUE_KEY",
        "SHORT_DESC",
        "MEDIUM_DESC",
        "LONG_DESC",
    ]
    df = ( df.loc[:, keep_flds]
        .sort_values(keep_flds)
        .drop_duplicates(keep_flds, keep="last", )
        .rename(columns={'CODE_VALUE_KEY': 'ethnicity_code',
                         })
        .reset_index()
        .drop('index', axis=1)
    )

    return df


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Definitions ..."):
        src.pages.components.page_header()
        st.write(
            """
            ## Definitions
"""
        )

        today = dt.datetime.today()
        today_str = today.strftime("%Y%m%d_%H%M")

        st.write(f"#### Academic Program Codes  ")
        df = curriculum_df() 
        cip_df = degree_mapping_df()

        df = pd.merge(
            df,
            cip_df,
            on=['academic_program_code'],
            how="left",
        )

        st.dataframe(df)
        st.download_button(
            label="Download data as CSV",
            data=convert_df(df),
            file_name=f"academic_program_codes_{today_str}.csv",
            mime='text/csv',
        )

        st.write(f"#### Race/Ethnicity Codes  ")
        df = ethnicity_df() 

        st.dataframe(df)
        st.download_button(
            label="Download data as CSV",
            data=convert_df(df),
            file_name=f"race-ethnicity_codes_{today_str}.csv",
            mime='text/csv',
        )

