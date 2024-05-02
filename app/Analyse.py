import pandas as pd
def cut_empty_intervals(df , threshold = 1200000) :
    '''
    in this function first i calculate the time diffrenece between two consecutive timestamps and the create mask and then put None
    where the long interval ends .
    important : the first point after long interval is missed in this function
    '''
    df['time_diff'] = df['x_data'].diff()
    mask = df['time_diff'] > threshold
    mask.fillna(False, inplace=True)
    df[mask] = None
    return df


def fixed_mean_calculation(df):
    '''
    function for calculatin mean for step and heart rate .
    '''
    df['x_data'] = pd.to_datetime(df['x_data'], unit='ms')   
    df = df.set_index('x_data')
    hr_quantile = df['y_data'].quantile(0.9)
    hr_min = df['y_data'].min()
    hr_mean_1= int(df['y_data'].loc[(df.index.hour>=23) | (df.index.hour< 8)].mean())
    hr_mean_2= int(df['y_data'].loc[(df.index.hour>=8) & (df.index.hour< 12)].mean())
    hr_mean_3= int(df['y_data'].loc[(df.index.hour>=12) & (df.index.hour< 16)].mean())
    hr_mean_4= int(df['y_data'].loc[(df.index.hour>=16) & (df.index.hour< 20)].mean())
    hr_mean_5= int(df['y_data'].loc[(df.index.hour>=20) & (df.index.hour< 23)].mean())
    step_quantile = df['step'].quantile(0.9)
    step_min = df['step'].min()
    step_mean_1 = int(df['step'].loc[(df.index.hour>=23) | (df.index.hour< 8)].mean())
    step_mean_2 = int(df['step'].loc[(df.index.hour>=8) & (df.index.hour< 12)].mean())
    step_mean_3 = int(df['step'].loc[(df.index.hour>=12) & (df.index.hour< 16)].mean())
    step_mean_4 = int(df['step'].loc[(df.index.hour>=16) & (df.index.hour< 20)].mean())
    step_mean_5 = int(df['step'].loc[(df.index.hour>=20) & (df.index.hour< 23)].mean())
    return hr_mean_1 , hr_mean_2 , hr_mean_3 , hr_mean_4 , hr_mean_5 , step_mean_1 , step_mean_2 , step_mean_3 , step_mean_4 , step_mean_5 , step_quantile , hr_quantile , step_min , hr_min


