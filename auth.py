import requests
import streamlit as st

import config


def authenticate(credentials: tuple):
    username, password = credentials
    response = requests.get(
        f'{config.API_URL}/readings/?limit=10000',
        auth=(username, password)
    )
    if response.status_code != 200:
        st.error('User sau parola gresita')
        return False

    st.session_state['is_authenticated'] = True
    st.success('Autentificare reusita!')
    return True
