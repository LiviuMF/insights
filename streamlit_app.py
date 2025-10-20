from auth import load_authentication_module
import api
from frontend.css import load_general_css
from frontend import widgets as fe
import utils

import streamlit as st


load_authentication_module()

if st.session_state['is_authenticated']:
    api.fetch_devices()
    fe.load_sidebar()
    utils.load_device_data()
    api.load_readings_for_date()
    api.fetch_owner_data()
    load_general_css()
    fe.load_haccp_report()
    fe.load_temp_interval_change()
