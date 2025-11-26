from datetime import datetime, timedelta

import streamlit as st



def get_today():
    return datetime.today()


def save_to_session_state(**kwargs):
    for k, v in kwargs.items():
        st.session_state[k] = v


def load_device_data() -> None:
    mapping = st.session_state['dev_name_mapping']
    device_name = st.session_state['selected_device']
    save_to_session_state(device_data=mapping[device_name])


def days_ago(nr_of_days: int) -> datetime:
    return get_today() - timedelta(nr_of_days)
