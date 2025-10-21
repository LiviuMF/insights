from functools import partial

import config
from frontend import css
from data_processor import data_processor as dp
import utils


import requests
import streamlit as st



def load_sidebar():
    if st.session_state['is_authenticated']:
        dev_names = st.session_state['devices']
        if selected_device := st.sidebar.selectbox(
                'Selecteaza dispozitiv',
                dev_names,
        ):
            utils.save_to_session_state(selected_device=selected_device)

        if selected_date := st.sidebar.date_input(
                'Selecteaza data',
                max_value=utils.TODAY
        ):
            utils.save_to_session_state(selected_date=selected_date)
        css.load_calendar_css()


def load_haccp_report() -> None:
    report_date_value = st.session_state['selected_date'].isoformat()
    device_data = st.session_state['device_data']
    dev_eui = device_data['id']
    dev_max_limit = device_data['dev_max_accepted_temp']
    dev_min_limit = device_data['dev_min_accepted_temp']

    report_response = requests.get(
        f'{config.API_URL}/api/reports/',
        auth=(st.session_state['username'], st.session_state['password']),
        params={
            'dev_eui': dev_eui,
            'report_date': report_date_value
        }
    )
    reports = report_response.json()['results']
    col_widths = [2.5, 4, 6, 6]

    st.subheader('Generare raport HACCP')
    report_summary = ''
    if reports:
        report_summary = dp.build_report_summary(reports)
        st.text(report_summary)

        archived_report = dp.load_archived_report(col_widths, reports)
        data_for_download = reports[0]['report_data']
        report_type = 'raport'
        if st.button('Modifica raport', key='modify_report'):
            response = requests.patch(
                f'{config.API_URL}/api/reports/{reports[0]["id"]}/',
                auth=(st.session_state['username'], st.session_state['password']),
                json={
                    'report_data': archived_report,
                }
            )
            if response.status_code == 200:
                st.success('Raport modificat cu succes')
    else:
        readings_df = st.session_state['readings']
        if readings_df.empty:
            st.warning('Nu sunt citiri pentru aceasta data')
            return

        new_report_data = dp.build_new_report(col_widths, readings_df)
        data_for_download = new_report_data
        report_type = 'citiri'
        if st.button("Salveaza raport", key='save_report'):
            user_data = st.session_state["user_data"]
            st.text(f'Raport intocmit de {user_data["first_name"]} {user_data["last_name"]}')

            response = requests.post(
                f'{config.API_URL}/api/reports/',
                auth=(st.session_state['username'], st.session_state['password']),
                json={
                    'report_data': new_report_data,
                    'device': dev_eui,
                    'date': report_date_value,
                }
            )
            if response.status_code == 200:
                st.success('Raport salvat cu succes')

    generate_pdf_partial = partial(
        dp.generate_pdf,
        data_for_download,
        st.session_state['owners'][0],
        st.session_state['user_data'],
        report_date_value,
        report_summary,
        [dev_min_limit, dev_max_limit]
    )
    st.download_button(
        f'Descarca {report_type}',
        data=generate_pdf_partial(),
        file_name=f'{report_date_value}_raport_temperatura.pdf'
    )



def load_temp_interval_change() -> None:
    dev_name_mapping = st.session_state['dev_name_mapping']
    device = st.session_state['selected_device']
    if st.sidebar.checkbox('Modifica tipul de incadrare'):
        cooling_type = st.sidebar.selectbox(
            label='hidden cooling type',
            label_visibility='collapsed',
            key='modify_cooling_type',
            options=(
                'refrigerare (carne / organe)',
                'refrigerare (mezeluri / lactate)',
                'refrigerare (fructe / legume)',
                'congelare'
            )
        )
        if st.sidebar.button('Salveaza modificari'):
            if cooling_type:
                try:
                    dp.update_device_by_id(
                        device_data={
                            'temp_interval': config.COOLING_MAPPER[cooling_type]
                        },
                        device_id=dev_name_mapping[device]['id'],
                        username=st.session_state['username'],
                        password=st.session_state['password']
                    )
                    st.sidebar.success('Modificari salvate cu succes!')
                except:
                    st.sidebar.error(f'A aparut o eroare la salvare')


