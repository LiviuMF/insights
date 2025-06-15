import pandas as pd
import requests
import streamlit as st

from datetime import datetime, timedelta

from auth import authenticate
import config
import data_processor as dp


if 'is_authenticated' not in st.session_state:
    st.session_state['is_authenticated'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''
if 'password' not in st.session_state:
    st.session_state['password'] = ''


if not st.session_state['is_authenticated']:
    username = st.text_input('Username')
    password = st.text_input('Password', type='password')

    if username and password:
        st.session_state['username'] = username
        st.session_state['password'] = password
        authenticate((username, password))

    if st.session_state['is_authenticated']:
        st.rerun()


if st.session_state['is_authenticated']:
    devices = requests.get(
        f'{config.API_URL}/devices/',
        auth=(
            st.session_state['username'],
            st.session_state['password']
        )).json()['results']

    DEV_MAPPING = {}
    for device in devices:
        DEV_MAPPING[device['id']] = {k: v for k, v in device.items()}

    readings = requests.get(
        f'{config.API_URL}/readings/?limit=1000',
        auth=(st.session_state['username'], st.session_state['password'])
    ).json()['results']

    df = pd.DataFrame(readings)
    if 'df' not in st.session_state:
        st.session_state.df = df

    min_date = st.session_state.df['timestamp'].astype('datetime64[ns]').dt.date.min()

    st.subheader('Device Health')

    if start_date := st.sidebar.date_input(
            label='Start date',
            value=datetime.today() - timedelta(days=5),
            max_value=datetime.today() - timedelta(days=1),
            min_value=min_date,
            key='start_date',
    ):
        end_date = st.sidebar.date_input(
            label='End date',
            value=datetime.today() - timedelta(days=1),
            max_value=datetime.today() - timedelta(days=1),
            min_value=min_date,
            key='end_date'
        )

        dev_health = dp.calculate_device_health(
            df=st.session_state.df,
            start_date=st.session_state.start_date,
            end_date=st.session_state.end_date
        )
        df_mapping = {k: v['dev_name'] for k, v in DEV_MAPPING.items()}
        dev_health['dev_eui'].replace(df_mapping, inplace=True)
        dev_health.loc[dev_health['device_health'] > 100, 'device_health'] = 100

        st.table(
            data=dev_health.style.applymap(
                lambda x: "background-color: #fcb2a2"
                if x < 80.0
                else "background-color: white",
                subset=['device_health']),
        )

        dev_health.replace(df_mapping, inplace=True)
        st.line_chart(dev_health, x='dev_eui')
        st.download_button('Download', dev_health.to_csv(), file_name='device_health.csv', key='dev_health')

        dev_names = list(v['dev_name'] for k, v in DEV_MAPPING.items())
        if selected_names := st.sidebar.multiselect('Select device', dev_names, default=dev_names[:1]):
            dev_euis = [k for k, v in DEV_MAPPING.items() if v['dev_name'] in selected_names]
            results, probe, sensor, humidity = dp.fetch_mean_readings(
                df=st.session_state.df,
                start_date=st.session_state.start_date,
                end_date=st.session_state.end_date,
                dev_euis=dev_euis,
                name_mapping=DEV_MAPPING
            )

            st.subheader('Probe average')
            st.line_chart(probe, x='day')
            st.download_button('Download', probe.to_csv(), file_name='probe.csv', key='probe')

            st.subheader('Sensor average')
            st.line_chart(sensor, x='day')
            st.download_button('Download', sensor.to_csv(), file_name='sensor.csv', key='sensor')

            st.subheader('Humidity average')
            st.line_chart(humidity, x='day')
            st.download_button('Download', humidity.to_csv(), file_name='humidity.csv', key='humidity')

            st.subheader('Probe vs sensor')
            if selected_name := st.selectbox('Select dev_eui', selected_names):
                dev_eui = [k for k, v in DEV_MAPPING.items() if v['dev_name'] == selected_name][0]
                probe_vs_sensor = results.loc[results['dev_eui'] == dev_eui]
                probe_vs_sensor = probe_vs_sensor[['tempc_ds', 'tempc_sht', 'day']]
                st.line_chart(probe_vs_sensor, x='day')
                st.download_button('Download', probe_vs_sensor.to_csv(), file_name='probe_vs_sensor.csv', key='probe_vs_sensor')
