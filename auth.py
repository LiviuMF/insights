import requests
import streamlit as st

import config


def authenticate(credentials: tuple):
    username, password = credentials
    response = requests.post(
        f'{config.API_URL}/login/',
        auth=(username, password)
    )
    if response.status_code != 200:
        st.error('User sau parola gresita')
        return False

    st.session_state['is_authenticated'] = True
    st.success('Autentificare reusita!')
    return True


def load_authentication_module() -> None:
    if 'is_authenticated' not in st.session_state:
        st.session_state['is_authenticated'] = False
    if 'username' not in st.session_state:
        st.session_state['username'] = ''
    if 'password' not in st.session_state:
        st.session_state['password'] = ''


    if not st.session_state['is_authenticated']:
        username = st.text_input('Utilizator').lower()
        password = st.text_input('Parola', type='password')
        if st.button('Login'):
            st.session_state['username'] = username
            st.session_state['password'] = password
            authenticate((username, password))

        if st.session_state['is_authenticated']:
            st.rerun()
