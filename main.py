import pandas as pd
import requests
import streamlit as st

from datetime import datetime, timedelta
from io import BytesIO

import config
import data_processor as dp


readings = requests.get(
    f'{config.API_URL}/readings/?limit=10000',
    auth=(config.API_USERNAME, config.API_PASSWORD)
).json()['results']

df = pd.DataFrame(readings)
if 'df' not in st.session_state:
    st.session_state.df = df


st.subheader('Device Health')

if start_date := st.sidebar.date_input(
        label='Start date',
        value=datetime.today() - timedelta(days=1),
        max_value=datetime.today() - timedelta(days=1),
        min_value=st.session_state.df['timestamp'].astype('datetime64[ns]').dt.date.min(),
        key='start_date',
):
    end_date = st.sidebar.date_input(
        label='End date',
        value=datetime.today() - timedelta(days=1),
        max_value=datetime.today() - timedelta(days=1),
        min_value=st.session_state.start_date,
        key='end_date'
    )

    dev_health = dp.calculate_device_health(
        df=st.session_state.df,
        start_date=st.session_state.start_date,
        end_date=st.session_state.end_date
    )
    st.table(
        data=dev_health.style.applymap(
            lambda x: "background-color: #fcb2a2"
            if x < 80.0
            else "background-color: white",
            subset=['device_health']),
    )
    df_mapping = {k:v['dev_name'] for k, v in dp.DEV_MAPPING.items()}
    dev_health.replace(df_mapping, inplace=True)
    st.line_chart(dev_health, x='dev_eui')

    if dev_euis := st.sidebar.multiselect('Select device', dp.DEV_MAPPING.keys(), default=(9, 11)):
        results, probe, sensor, humidity = dp.fetch_mean_readings(
            df=st.session_state.df,
            start_date=st.session_state.start_date,
            end_date=st.session_state.end_date,
            dev_euis=dev_euis,
        )

        st.subheader('Probe average')
        st.line_chart(probe, x='day')

        st.subheader('Sensor average')
        st.line_chart(sensor, x='day')

        st.subheader('Humidity average')
        st.line_chart(humidity, x='day')

        st.subheader('Probe vs sensor')
        filter_on_dev_eui = st.selectbox('Select dev_eui', dev_euis)
        if filter_on_dev_eui:
            probe_vs_sensor = results.loc[results['dev_eui'] == filter_on_dev_eui]
            probe_vs_sensor = probe_vs_sensor[['tempc_ds', 'tempc_sht', 'day']]
            st.line_chart(probe_vs_sensor, x='day')

        buffered_file = BytesIO()
        results.to_csv(buffered_file, index=False)
        st.download_button(label='Download Results', data=buffered_file, file_name='results.csv')
