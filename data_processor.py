import pandas as pd


def fetch_mean_readings(
        df,
        dev_euis: list,
        name_mapping: dict,
        start_date=None,
        end_date=None,
):
    df_mean = df[['dev_eui', 'tempc_ds', 'timestamp', 'tempc_sht', 'hum_sht']]
    df_mean['timestamp'] = df_mean['timestamp'].astype('datetime64[ns]')
    df_mean['day'] = df_mean['timestamp'].dt.strftime('%Y-%m-%d')

    # filter dataframe since date if filter available
    df_mean = df_mean.loc[
        (df_mean['timestamp'].dt.date >= start_date) & (df_mean['timestamp'].dt.date <= end_date)
        ]
    df_mean = df_mean.loc[df_mean['dev_eui'].isin(dev_euis)]

    df_mean['tempc_ds'] = df_mean['tempc_ds'].astype('float')
    df_mean['tempc_sht'] = df_mean['tempc_sht'].astype('float')
    df_mean['hum_sht'] = df_mean['hum_sht'].astype('float')

    df_mean = remove_outliers_from_df_col(
        df=df_mean,
        col_name='tempc_ds',
        dev_euis=dev_euis,
        name_mapping=name_mapping
    )

    df_mean['probe_mean'] = df_mean.groupby(['dev_eui', 'day'])['tempc_ds'].transform('mean')
    df_mean['mean_of_probe_mean'] = df_mean.groupby('dev_eui')['probe_mean'].transform('mean')

    df_mean['sensor_mean'] = df_mean.groupby(['dev_eui', 'day'])['tempc_sht'].transform('mean')
    df_mean['mean_of_sensor_mean'] = df_mean.groupby('dev_eui')['sensor_mean'].transform('mean')

    df_mean['humidity_mean'] = df_mean.groupby(['dev_eui', 'day'])['hum_sht'].transform('mean')
    df_mean['mean_of_humidity_mean'] = df_mean.groupby('dev_eui')['humidity_mean'].transform('mean')

    df_mean.drop_duplicates(subset=['day', 'dev_eui'], keep='first', inplace=True)
    probe = transform_df_rows_to_cols(
        df=df_mean[['dev_eui', 'probe_mean', 'day']],
        split_on='dev_eui',
        use_values_from_col='probe_mean'
    )
    sensor = transform_df_rows_to_cols(
        df=df_mean[['dev_eui', 'sensor_mean', 'day']],
        split_on='dev_eui',
        use_values_from_col='sensor_mean'
    )
    humidity = transform_df_rows_to_cols(
        df=df_mean[['dev_eui', 'humidity_mean', 'day']],
        split_on='dev_eui',
        use_values_from_col='humidity_mean'
    )

    df_mapping = {k: v['dev_name'] for k, v in name_mapping.items()}
    for df in [df_mean, probe, sensor, humidity]:
        df_columns = list(df.columns)
        for index, col in enumerate(df.columns, start=0):
            if col in df_mapping.keys():
                df_columns[index] = df_mapping[col]
        df.columns = df_columns
    return df_mean, probe, sensor, humidity


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


def calculate_device_health(df, start_date=None, end_date=None):
    df_dh = df[['dev_eui', 'timestamp']]
    df_dh['timestamp'] = df_dh['timestamp'].astype('datetime64[ns]')

    # filter dataframe since date if filter available
    df_dh = df_dh.loc[
        (df_dh['timestamp'].dt.date >= start_date) & (df_dh['timestamp'].dt.date <= end_date)
    ]

    # get the number of possible readings (24 per day) since start_date
    possible_readings = (end_date - start_date).days * 25

    # Actual readings
    # 1. only accept 1 reading / hour
    df_dh['unique_id'] = df_dh['timestamp'].dt.strftime('%Y%m%d%H')
    df_dh.drop_duplicates(subset=['unique_id', 'dev_eui'], keep='first', inplace=True)

    # 2. get the actual number of readings
    df_dh['reading_count'] = df_dh.groupby('dev_eui')['dev_eui'].transform('count')

    # calculate device health
    df_dh['device_health'] = df_dh['reading_count'] / possible_readings * 100
    df_dh.drop_duplicates(subset=['dev_eui'], keep='first', inplace=True)
    df_dh.sort_values(by='device_health', inplace=True)
    df_dh['limit (80%)'] = 80
    return df_dh[['dev_eui', 'device_health', 'limit (80%)']]
