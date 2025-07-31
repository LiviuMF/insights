import pandas as pd
import requests
import streamlit as st

from datetime import datetime, timedelta

from auth import authenticate
import config
import data_processor as dp


st.write('''<style>
    .stAppDeployButton, #MainMenu{
        display: None;
    }
    </style>''', unsafe_allow_html=True)


if 'is_authenticated' not in st.session_state:
    st.session_state['is_authenticated'] = False
if 'username' not in st.session_state:
    st.session_state['username'] = ''
if 'password' not in st.session_state:
    st.session_state['password'] = ''


if not st.session_state['is_authenticated']:
    username = st.text_input('Utilizator')
    password = st.text_input('Parola', type='password')
    if st.button('Login'):
        st.session_state['username'] = username
        st.session_state['password'] = password
        authenticate((username, password))

    if st.session_state['is_authenticated']:
        st.rerun()


if st.session_state['is_authenticated']:
    devices = requests.get(
        f'{config.API_URL}/api/devices/',
        auth=(
            st.session_state['username'],
            st.session_state['password']
        )).json()['results']

    DEV_MAPPING = {}
    for device in devices:
        DEV_MAPPING[device['id']] = {k: v for k, v in device.items()}

    if 'min_value' not in st.session_state:
        st.session_state['min_value'] = datetime.today() - timedelta(days=7)

    if start_date := st.sidebar.date_input(
            label='Data inceput',
            value=datetime.today() - timedelta(days=7),
            max_value=datetime.today() - timedelta(days=1),
            key='start_date',
    ):
        end_date = st.sidebar.date_input(
            label='Data sfarsit',
            value=datetime.today() - timedelta(days=1),
            max_value=datetime.today() - timedelta(days=1),
            key='end_date'
        )

        all_readings = dp.fetch_all_readings(
            start_date,
            end_date,
            st.session_state['username'],
            st.session_state['password'],
            1000
        )

        if 'df' not in st.session_state:
            df = pd.DataFrame(all_readings)
            st.session_state['df'] = df
            st.session_state.min_value = df.timestamp.min()

        dev_names = list(v['dev_name'] for k, v in DEV_MAPPING.items())
        if selected_names := st.sidebar.multiselect('Selecteaza dispozitiv', dev_names, default=dev_names[:1]):
            unique_key=0
            new_temp_limits = {}
            if checkbox := st.sidebar.checkbox('Modificare limite'):
                if not st.session_state.get('pressed'):
                    st.session_state['pressed'] = True
            if not checkbox:
                    st.session_state['pressed'] = False
            if st.session_state.get('pressed'):
                for key, dev_data in DEV_MAPPING.items():
                    st.sidebar.text(f'Modificati limita pentru {dev_data["dev_name"]}')
                    temp_limit = st.sidebar.text_input(f'Limita curenta: {dev_data["dev_max_accepted_temp"]}', key=unique_key)
                    unique_key+=1
                    new_temp_limits[key] = temp_limit
                if st.sidebar.button('Salveaza modificari'):
                    for dev_id, temp_limit  in new_temp_limits.items():
                        if temp_limit:
                            dp.update_device_by_id(
                                device_data={
                                    'dev_max_accepted_temp': temp_limit
                                },
                                device_id=dev_id,
                                username=st.session_state['username'],
                                password=st.session_state['password']
                            )
                    st.sidebar.success('Modificari salvate cu succes!')
                    st.session_state['pressed'] = False

            dev_euis = [k for k, v in DEV_MAPPING.items() if v['dev_name'] in selected_names]
            results, probe, sensor, humidity = dp.fetch_mean_readings(
                df=st.session_state.df,
                start_date=st.session_state.start_date,
                end_date=st.session_state.end_date,
                dev_euis=dev_euis,
                name_mapping=DEV_MAPPING
            )

            st.subheader('Temperatura medie sonda')
            st.line_chart(probe, x='day')
            st.download_button('Descarca', dp.to_excel_bytes(probe, 'sonda'), file_name='sonda.xlsx', key='probe')

            st.subheader('Temperatura medie senzor')
            st.line_chart(sensor, x='day')
            st.download_button('Descarca', dp.to_excel_bytes(sensor, 'senzor'), file_name='senzor.xlsx', key='sensor')
            #
            st.subheader('Umiditate medie senzor')
            st.line_chart(humidity, x='day')
            st.download_button('Descarca', dp.to_excel_bytes(humidity, 'umiditate'), file_name='umiditate.xlsx', key='humidity')

            st.subheader('Sonda vs Senzor')
            if selected_name := st.selectbox('Select dev_eui', selected_names):
                dev_eui = [k for k, v in DEV_MAPPING.items() if v['dev_name'] == selected_name][0]
                probe_vs_sensor = results.loc[results['dev_eui'] == dev_eui]
                probe_vs_sensor = probe_vs_sensor[['tempc_ds', 'tempc_sht', 'day']]
                st.line_chart(probe_vs_sensor, x='day')
                st.download_button('Descarca', dp.to_excel_bytes(probe_vs_sensor, 'sonda_vs_senzor'), file_name='sonda_vs_senzor.xlsx', key='probe_vs_sensor')

            st.subheader('Sanatate dispozitiv')

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
