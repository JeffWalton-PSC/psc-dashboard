import numpy as np
import pandas as pd
import streamlit as st
import datetime as dt
from pathlib import Path
import src.pages.components
from bokeh.plotting import figure
from bokeh.palettes import Set1_9


start_term = "2014.Spring"

def date_diff_weeks(start, end):
    """
    returns the difference between two dates in integer weeks
    """
    diff = (pd.to_datetime(end) - pd.to_datetime(start))
    return int( diff / np.timedelta64(1,'W'))


def adm_week(d):
    """
    returns calendar week number and Admissions Week Number for a given date, d
    """
    year = d.year
    week_number = d.isocalendar()[1]

    if d >= dt.date(year, 9, 1):
        adm_start = dt.date(year, 9, 1)
    else:
        adm_start = dt.date(year - 1, 9, 1)

    adm_week_number = min(date_diff_weeks(adm_start, d), 53)

    return week_number, adm_week_number


def write():
    """Used to write the page in the app.py file"""
    with st.spinner("Loading Admissions - Historic Data By Stage ..."):
        src.pages.components.logo()
        st.write(
            """
            ## Admissions - Historic Data By Stage
            ### Current deposits by admissions stage from PowerCampus
            Data for this chart updates nightly.
"""
        )

    today = dt.date.today()
    today_str = today.strftime("%Y%m%d")

    data_path = Path(r"F:\Applications\Admissions\funnel\data")
    data_file = data_path / "stage_data"
    df = pd.read_hdf(data_file, key="weekly")
    df = df[(df["year_term"] > start_term)]

    summ = df.groupby(["year_term", "stage"]).sum()
    summ_t = summ.transpose()

    week_number, adm_week_number = adm_week(today)

    # widgets
    stage_list = ["Applied", "Accepted", "Deposited"]
    stage = st.radio(label="Stage:", options=stage_list, index=2)

    all_terms = sorted(list(df["year_term"].dropna().unique()), reverse=True)
    all_terms = [l for l in all_terms if "Fall" in l]
    term = st.selectbox(label="Selected primary term:", options=all_terms, index=0)

    terms_opt = all_terms.copy()
    terms_opt.remove(term)
    terms = st.multiselect(
        'Select other term(s) to display:',
        options=terms_opt,
        default=terms_opt,
        )
    # order terms
    terms = [t for t in terms_opt if t in terms]

    if stage and term and terms:

        title = (
            f"{stage} - Admissions Weekly Summary - Week {adm_week_number:d} ({today_str})"
        )

        # term_list.reverse()
        
        y_max = summ_t[(term, stage)].max()
        for t in terms:
            ym = summ_t[(t, stage)].max()
            if ym > y_max:
                y_max = ym

        TOOLS = "pan,wheel_zoom,box_zoom,save,reset"
        # TOOLS="crosshair,pan,wheel_zoom,box_zoom,save,reset"

        p = figure(
            plot_width=800,
            plot_height=600,
            title=title,
            x_axis_label="Admissions Week Number (year starts Sept 1)",
            y_axis_label=stage,
            tools=TOOLS,
            x_range=(0, 54),
            y_range=(0, y_max * 1.05),
        )

        p.line(summ_t.index, summ_t[(term, stage)], color="red", line_width=2, legend_label=term)

        c = 1
        for t in terms:
            p.line(summ_t.index, summ_t[(t, stage)], color=Set1_9[c], legend_label=t)
            if c <= 8:
                c += 1
            else:
                c = 1

        # week_number line
        p.line(
            (adm_week_number, adm_week_number),
            (-1000, 5000),
            color="green",
            line_width=0.8,
            line_dash="dashed",
            legend_label=f"Week {adm_week_number:d}",
            alpha=0.8,
        )

        p.legend.location = "top_left"

        st.bokeh_chart(p, use_container_width=True)
