from concurrent.futures import ThreadPoolExecutor, as_completed
from functools import lru_cache
from xmlrpc.client import ResponseError

import config
from utils import save_to_session_state

import pandas as pd
import requests
import streamlit as st


def fetch_devices():
    if st.session_state['is_authenticated']:
        response = requests.get(
            f'{config.API_URL}/api/devices/',
            auth=(
                st.session_state['username'],
                st.session_state['password']
            ))
        devices = response.json()['results']
        DEV_ID_MAPPING = {}
        DEV_NAME_MAPPING = {}
        for device in devices:
            DEV_ID_MAPPING[device['id']] = {k: v for k, v in device.items()}
            DEV_NAME_MAPPING[device['dev_name']] = {k: v for k, v in device.items()}

        save_to_session_state(
            dev_id_mapping=DEV_ID_MAPPING,
            dev_name_mapping=DEV_NAME_MAPPING,
            devices=DEV_NAME_MAPPING.keys(),
        )


def fetch_owner_data() -> None:
    response = requests.get(
        f'{config.API_URL}/api/owners/',
        auth=(
            st.session_state['username'],
            st.session_state['password']
        ))

    save_to_session_state(owners=response.json()['results'])


@lru_cache
def fetch_readings_for_offset(
        offset: str,
        start_date: str,
        end_date: str,
        username: str,
        password: str
) -> requests.Response:
    return requests.get(
        url=f'{config.API_URL}/api/readings/',
        params={
            'limit': 1000,
            'offset': offset,
            'start_date': start_date,
            'end_date': end_date
        },
        auth=(username, password)
    )


def load_readings_for_date() -> None:
    mapping = st.session_state['dev_name_mapping']
    device = st.session_state['selected_device']
    date = st.session_state['selected_date']
    dev_eui = mapping[device]['id']

    response = requests.get(
        url=f'{config.API_URL}/api/readings/',
        params={
            'date': date,
            'dev_eui': dev_eui
        },
        auth=(
            st.session_state['username'],
            st.session_state['password']
        )
    )
    if response.status_code == 200:
        results = response.json()['results']
        user_data = {}
        if results:
            user_data = results[0]['user_data']
        save_to_session_state(user_data=user_data)
        save_to_session_state(readings=pd.DataFrame(results))
    else:
        raise ResponseError(
            f'Could not retrieve readings for {date=} with response: {response.status_code}')
