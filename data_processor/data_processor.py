import pandas as pd
import pymupdf
import requests
import streamlit as st

from dateutil.parser import parse
from io import BytesIO

import config


def remove_duplicates_by_hour(df: pd.DataFrame) -> pd.DataFrame:
    df['hour'] = df['timestamp'].apply(lambda x: parse(x).hour)
    df.drop_duplicates(subset='hour', inplace=True, keep='first')
    return df


def transform_df_rows_to_cols(
        df: pd.DataFrame,
        split_on: str,
        use_values_from_col: str
) -> pd.DataFrame:

    df_sections = []
    for dev_eui in sorted(df[split_on].unique(), key=lambda x: x):
        current_df = df.loc[df[split_on] == dev_eui]
        current_df[dev_eui] = current_df[use_values_from_col]
        current_df = current_df[['day', dev_eui]]
        df_sections.append(current_df)

    master_df = df_sections[0]
    for df_section in df_sections[1:]:
        master_df = master_df.merge(df_section, left_on='day', right_on='day')

    return master_df


def remove_outliers_from_df_col(
        df: pd.DataFrame,
        col_name: str,
        dev_euis: list[str],
        name_mapping: dict,
):
    all_dfs = []
    for dev_eui in dev_euis:
        temp_limit = name_mapping[dev_eui]['dev_max_accepted_temp']

        current_df = df.loc[df['dev_eui'] == dev_eui]

        # filter outliers based on the given temperature limit
        outlier_df = current_df.loc[current_df[col_name] > temp_limit]
        if outlier_df.empty:
            mean = outlier_df[col_name].mean()

            # replace outliers with mean
            current_df.loc[
                current_df[col_name] > temp_limit,
                col_name] = mean

        all_dfs.append(current_df)

    return pd.concat(all_dfs)


def update_device_by_id(
        device_data: dict,
        device_id: str,
        username: str,
        password: str
) -> None:
    try:
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
    report_date = report[0]['date']
    nr_of_deviations = 0
    reasons = []
    actions = []
    consecutive_counter = 0
    all_counters = []
    hours = []
    hour_interval = []
    save_flag = False
    for index, data in enumerate(report_data):
        temp, time, deviation, action = data
        if deviation != 'fara abatere':
            nr_of_deviations += 1
            reasons.append(deviation)
            hour_interval.append(1)
        if action != 'fara actiune':
            actions.append(action)
            hour_interval.append(0)

        if index < len(report_data) - 1:
            next_reason = report_data[index + 1][2]

            if deviation != 'fara abatere' and next_reason != 'fara abatere':
                consecutive_counter += 1
                hours.append(time)
            elif deviation != 'fara abatere' and next_reason == 'fara abatere':
                hours.append(time)
                consecutive_counter += 1
                save_flag = True
            elif deviation == 'fara abatere' and next_reason == 'fara abatere':
                consecutive_counter = 0
                all_counters.append(0)
                hours.append('0')
                save_flag = False
            elif deviation == 'fara abatere' and next_reason != 'fara abatere':
                consecutive_counter = 0
                all_counters.append(0)
                hours.append('0')
                save_flag = False
        if index == len(report_data) - 1:
            if deviation == 'fara abatere':
                all_counters.append(0)
                hours.append('0')
            else:
                hours.append(time)
                consecutive_counter += 1
                all_counters.append(consecutive_counter)

        if save_flag and index != len(report_data) - 1:
            all_counters.append(consecutive_counter)
        elif save_flag and index == len(report_data):
            all_counters.append(1)

    all_reasons = ', '.join(set(reasons))
    all_actions = ', '.join(set(actions))

    consecutive_deviations = [str(dev) for dev in all_counters if dev > 1]
    consecutive_deviations.sort()

    deviation_interval = []
    for index, hour in enumerate(hour_interval):
        if index < len(all_counters):
            counter_value = all_counters[index]
            if hour == 1 and counter_value > 1:
                interval_hours = hours[index:index + counter_value]
                if '0' in interval_hours:
                    interval_hours.remove('0')
                end_interval = interval_hours[0].split(':')[0]
                start_interval = interval_hours[-1].split(':')[0]
                deviation_interval.append(f'{start_interval} <-> {end_interval}')

    return (
        f"În data de {report_date}, s-au constatat {nr_of_deviations} abateri, "
        f"dintre care {','.join(consecutive_deviations)} consecutive în intervalele orare {', '.join(deviation_interval)}"
        f" cu următoarele cauze: {all_reasons}, pentru care s-au aplicat "
        f"următoarele acțiuni corective: {all_actions}"
    )


def generate_pdf(
        report_data: list[list],
        owner_data: dict,
        user_data: dict,
        report_date: str,
        dev_limits: list
):
    first_last_name = f'{user_data["first_name"]} {user_data["last_name"]}'
    template_pdf = pymupdf.open("media/pdf_template_haccp.pdf")
    cooling_type = [
        cool_type
        for cool_type, temp_limits in config.COOLING_MAPPER.items()
        if temp_limits == dev_limits
    ]
    if cooling_type:
        cooling_type = cooling_type[0]
    else:
        cooling_type = list(config.COOLING_MAPPER.keys())[0]

    color = (0, 0, 0) # black
    font_size = 12
    left_margin = 84
    page = template_pdf[0]
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
    temp_limits_text = f'{min_temp}..{max_temp}' if not cooling_type == 'congelare' else min_temp
    page.insert_text((left_margin + 23, 94), f'{temp_limits_text}', fontsize=font_size, color=color)
    page.insert_text((left_margin + 300, 94), cooling_type, fontsize=font_size, color=color)
    page.insert_text((left_margin + 355, 745), first_last_name, fontsize=font_size, color=color)
    page.insert_text((left_margin + 355, 764), report_date, fontsize=font_size, color=color)

    row_height = 20.18
    for index, row in enumerate(report_data):
        temp, time, deviation, action = row
        vertical = 242 + (index * row_height)
        temp_horizontal = 42
        time_horizontal = 97
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

        reason_options = [reason] if reason != 'fara abatere' else []
        action_options = [action] if action != 'fara actiune' else []
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
