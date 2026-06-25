import pandas as pd
import pymupdf
import requests
import streamlit as st

from dateutil.parser import parse
from io import BytesIO
import itertools

import config


def remove_duplicates_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    df['hour'] = df['timestamp'].apply(lambda x: parse(x).hour)
    df.drop_duplicates(subset='hour', inplace=True, keep='first')
    return df


def update_device_by_id(
        device_data: dict,
        device_id: str,
) -> None:
    try:
        username = st.session_state['username']
        password = st.session_state['password']
        requests.patch(
            url=f'{config.API_URL}/api/devices/{device_id}/',
            auth=(username, password),
            data=device_data
        )
    except Exception as e:
        raise e


def build_report_summary(
        report: list[dict]
) -> str:
    report_data = report[0]['report_data']
    previous_hour_data = report_data[0]
    consecutive_segment = []
    all_hours = []
    for index, data in enumerate(report_data[1:]):
        temp, time, deviation, action = data
        previous_hour = int(previous_hour_data[1].split(':')[0])
        previous_deviation = previous_hour_data[2]
        current_hour = int(time.split(':')[0])
        if (
                previous_hour - current_hour == 1 and
                deviation != 'fara abatere' and
                previous_deviation != 'fara abatere'
        ):
            consecutive_segment.extend([previous_hour_data, data])
        else:
            if consecutive_segment:
                unique = list(k for k, _ in itertools.groupby(consecutive_segment))
                all_hours.append(unique)
                consecutive_segment = []
        previous_hour_data = data


    deviation_intervals = [
        f"{d[0][1].split(':')[0]} <-> {d[-1][1].split(':')[0]}"
        for d in all_hours
    ]
    deviation_group_sizes = [str(len(d)) for d in all_hours]
    if not deviation_intervals:
        return "Nu exista suficiente citiri"
    if not all_hours:
        all_hours = list(k for k, _ in itertools.groupby(consecutive_segment))
        deviation_intervals = [x[1].split(':')[0] for x in all_hours]
        deviation_intervals = [f'{deviation_intervals[-1]} <-> {deviation_intervals[0]}']
        deviation_group_sizes = [str(len(all_hours))]

    report_date = report[0]['date']
    nr_of_deviations = len([x for x in report_data if x[2] != 'fara abatere'])
    deviation_message = (
        f's-au constatat {nr_of_deviations} abateri'
        if nr_of_deviations > 1
        else 's-a constatat o abatere'
    )
    all_reasons = set(x[2] for x in report_data if x[2] != 'fara abatere')
    all_actions = set(x[3] for x in report_data if x[2] != 'fara actiune')

    return (
        f"In data de {report_date}, {deviation_message}, dintre care {','.join(deviation_group_sizes)} consecutive in intervalele orare {', '.join(deviation_intervals)}"
        f"\nS-au inregistrat urmatoarele cauze si actiuni corective:\n-cauze: {', '.join(all_reasons)}\n-actiuni corective: {', '.join(all_actions)}"
    )


def generate_pdf(
        report_data: list[list],
        owner_data: dict,
        user_data: dict,
        report_date: str,
        report_summary: str,
        dev_limits: list,
        cooling_type: str,
):
    first_last_name = f'{user_data["first_name"]} {user_data["last_name"]}'
    template_pdf = pymupdf.open("media/pdf_template_haccp.pdf")

    color = (0, 0, 0) # black
    font_size = 12
    left_margin = 84
    page = template_pdf[0]

    if report_summary:
        page.insert_text(
            (left_margin - 65, 130),
            report_summary,
            fontsize=font_size,
            color=color
        )
    page.insert_text(
        (left_margin + 94, 63),
        f"{owner_data['name']} {owner_data['owner_legal_id']} / {owner_data['ansvsa']}",
        fontsize=font_size,
        color=color
    )
    page.insert_text(
        (left_margin, 77),
        owner_data['address'],
        fontsize=font_size,
        color=color
    )
    min_temp, max_temp = dev_limits
    temp_limits_text = f'{min_temp}..{max_temp}'
    page.insert_text((left_margin + 23, 94), f'{temp_limits_text}', fontsize=font_size, color=color)
    page.insert_text((left_margin + 300, 94), cooling_type, fontsize=font_size, color=color)
    page.insert_text((left_margin + 355, 745), first_last_name, fontsize=font_size, color=color)
    page.insert_text((left_margin + 355, 764), report_date, fontsize=font_size, color=color)

    row_height = 20.18
    for index, row in enumerate(report_data):
        temp, time, deviation, action = row
        vertical = 242 + (index * row_height)
        temp_horizontal = 97
        time_horizontal = 42
        deviation_horizontal = 200
        action_horizontal = 430

        color = color if float(temp) < max_temp else (0.8, 0, 0)

        for x_point, text in [
            (temp_horizontal, temp),
            (time_horizontal, time),
            (deviation_horizontal, deviation),
            (action_horizontal, action)
        ]:
            page.insert_text(
                (x_point, vertical),
                str(text),
                fontsize=12,
                color=color,
            )

    report_buffer = BytesIO()
    template_pdf.save(report_buffer)
    template_pdf.close()
    return report_buffer


def load_archived_report(col_widths, report_data):
    header_time, header_temp, header_reason, header_action = st.columns(col_widths)
    header_time.text('Ora')
    header_temp.text('Temperatura')
    header_reason.text('Abatere')
    header_action.text('Actiune')

    mapping = st.session_state['dev_name_mapping']
    device = st.session_state['selected_device']
    dev_max_limit = mapping[device]['dev_max_accepted_temp']
    dev_id = mapping[device]['id']

    prepared_report = []
    for index, report_data in enumerate(report_data[0]['report_data']):
        timestamp_col, temp_col, reason_col, action_col = st.columns(col_widths)
        temperature, timestamp, reason, action = report_data
        timestamp = parse(timestamp).strftime('%H:%M')

        reason_options = [reason]
        action_options = [action]
        if float(temperature) > dev_max_limit:
            markdown_temp = f':red[{temperature}]'
            reason_options.extend(
                [r for r in config.TEMP_REASONS if r != reason and r != 'fara abatere']
            )
            action_options.extend(
                [r for r in config.TEMP_ACTIONS if r != action and r != 'fara actiune']
            )
        else:
            markdown_temp = temperature

        temp_col.markdown(
            markdown_temp
        )
        timestamp_col.markdown(timestamp)

        report_data_id = f'report_data_{dev_id}_{index}'
        report_reason = reason_col.selectbox(
            label='reason',
            label_visibility='hidden',
            options=reason_options,
            key=f'{report_data_id}',
            placeholder=reason
        )
        action_taken = action_col.selectbox(
            label='reason',
            label_visibility='hidden',
            options=action_options,
            key=f'actiune_{report_data_id}',
        )
        prepared_report.append(
            [temperature, timestamp, report_reason, action_taken]
        )
    return prepared_report


def build_new_report(col_widths: list, df: pd.DataFrame) -> list:
    header_time, header_temp, header_reason, header_action = st.columns(col_widths)
    header_time.text('Ora')
    header_temp.text('Temperatura')
    header_reason.text('Abatere')
    header_action.text('Actiune')

    device_data = st.session_state['device_data']
    dev_max_limit = device_data['dev_max_accepted_temp']
    dev_id = device_data['id']

    readings_df = remove_duplicates_by_hour(df)
    haccp_report = readings_df[['tempc_ds', 'timestamp']]
    report_data = []
    for index, row in haccp_report.iterrows():
        time_col, temp_col, reason_col, action_col = st.columns(col_widths)

        data_id = f'{dev_id}_{index}'
        if float(row.tempc_ds) > dev_max_limit:
            reason_options = ['usa deschisa', 'frigider defect', 'pana curent']
            action_options = ['usa inchsa', 'defectiune remediata', 'platit factura']
            markdown_temp = f":red[{row.tempc_ds} ℃]"
        else:
            markdown_temp = f"{row.tempc_ds} ℃"
            reason_options = ['fara abatere']
            action_options = ['fara actiune']

        report_reason = reason_col.selectbox(
            label='reason label',
            label_visibility='hidden',
            options=reason_options,
            key=f'reason_{data_id}',
        )
        action_taken = action_col.selectbox(
            label='action label',
            label_visibility='hidden',
            options=action_options,
            key=f'action_{data_id}',
        )

        timestamp = parse(row.timestamp).strftime('%H:%M')
        report_data.append(
            [row.tempc_ds, timestamp, report_reason, action_taken]
        )
        temp_col.markdown(
            markdown_temp
        )
        time_col.markdown(timestamp)

    return report_data
