import config
from datetime import datetime

import requests
import streamlit as st

import utils


def load_general_css() -> None:
    st.write('''<style>
        .stAppDeployButton, #MainMenu{
            display: None;
        }
        .noReports{
          # border: solid 3px red;
          color: red;
        }
        .stImage {
          position: fixed;
          bottom: 40px;
          right: 40px;
          z-index: 999999 !important;
        }
        .stColumn {
          max-height: 16px;
          margin-top:10px;
        }
        .stColumn label{
          min-height:0;
        }
        .stText{
          margin-top: 10px;
        }
        .stSelectbox label{
         display: none;
        }
        @media (max-width: 800px) {
          .stHorizontalBlock {
            width: 25vw;
            flex-wrap: no-wrap;
          }
        }
        </style>''', unsafe_allow_html=True)
    load_calendar_css()


def format_date_verbose(date_str) -> str:
    date = datetime.strptime(date_str, "%Y-%m-%d")
    day = date.day
    suffix = get_day_suffix(day)
    formatted = date.strftime(f"%A, %B {day}{suffix} %Y")
    return formatted


def get_day_suffix(day):
    if 11 <= day <= 13:
        return 'th'
    last_digit = day % 10
    if last_digit == 1:
        return 'st'
    elif last_digit == 2:
        return 'nd'
    elif last_digit == 3:
        return 'rd'
    else:
        return 'th'


def load_calendar_css() -> None:
    device = st.session_state['selected_device']
    dev_id = st.session_state['dev_name_mapping'][device]['id']

    report_response = requests.get(
        f'{config.API_URL}/api/reports/',
        auth=(st.session_state['username'], st.session_state['password']),
        params={
            'dev_eui': dev_id
        }
    )
    report_days = [r['date'] for r in report_response.json()['results']]
    utils.save_to_session_state(reports=report_days)
    all_style = ''
    for r_day in report_days:
        verbose_date = format_date_verbose(r_day)
        current_css = f"""
        [aria-label="Choose {verbose_date}. It's available."] {{
            color: black !important;
            border: solid 2px green !important;
            border-radius: 16px !important;
        }}
        [aria-label="Selected. {verbose_date}. It's available."]::after {{
            background-color: green !important;
        }}
        """
        all_style = all_style + current_css

    st.write("<style>" + all_style + "</style>", unsafe_allow_html=True)