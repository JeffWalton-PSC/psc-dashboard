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

    curriculum = pc.select("CODE_CURRICULUM", 
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
    curriculum = ( curriculum.loc[:, keep_flds]
        .sort_values(keep_flds)
        .drop_duplicates(keep_flds, keep="last", )
        .rename(columns={"CODE_VALUE_KEY": "academic_program_code",
                         })
    )

    return curriculum


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
        df = (
            df.reset_index()
            # add CIP codes
        )
        st.dataframe(df)
        st.download_button(
            label="Download data as CSV",
            data=convert_df(df),
            file_name=f"academic_program_codes_{today_str}.csv",
            mime='text/csv',
        )




