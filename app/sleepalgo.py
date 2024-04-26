import pandas as pd
import numpy as np

def sleepstaging(df, hr_weight=3, movement_weight=5, sd_weight=0.5, resting_hr_weight=2, window_size=5):
    """
    Function for detecting sleep and wake based on heart rate.
    The function uses a score-based system to score each pair of heart rate and timestamp with percent.
    Values have been normalized.
    """
    # Calculate rolling standard deviation
    df['RollingSD'] = df['y_data'].rolling(window=window_size, center=True).std()

    total_weight = hr_weight + movement_weight + sd_weight + resting_hr_weight
    resting_hr = 60  # change this for sure

    # Calculate min, max, and range for each window
    rolling_min = df[['y_data', 'step', 'RollingSD']].rolling(window=window_size, center=True).min()
    rolling_max = df[['y_data', 'step', 'RollingSD']].rolling(window=window_size, center=True).max()
    rolling_range = rolling_max - rolling_min

    # Handle division by zero
    rolling_range[rolling_range == 0] = 1

    # Normalize the features
    normalized_movement = 1 - (df['step'] - rolling_min['step']) / rolling_range['step']
    normalized_hr = (df['y_data'] - rolling_min['y_data']) / rolling_range['y_data']
    normalized_sd = (df['RollingSD'] - rolling_min['RollingSD']) / rolling_range['RollingSD']
    resting_hr_distance = (resting_hr - df['y_data']) / rolling_range['y_data']
    resting_hr_distance = np.clip(resting_hr_distance, 0, 1)  # Clamping to [0, 1] range

    # Sleep Score
    sleep_score = movement_weight * normalized_movement + hr_weight * (1 - normalized_hr) + sd_weight * (1 - normalized_sd) + resting_hr_weight * resting_hr_distance

    # Scores to percentages
    df['SleepProbability'] = sleep_score / total_weight
    df['WakeProbability'] = 100 - df['SleepProbability']

    return df



def binarysleep_with_denoise(df, threshold=0.15, window_size=10):
    df['BinarySleep'] = 0
    df.loc[df['SleepProbability'] >= threshold, 'BinarySleep'] = 1
    df['BinarySleep'] = df['BinarySleep'].rolling(window=window_size, center=True, min_periods=1).mean()
    df['BinarySleep'] = (df['BinarySleep'] >= 0.5).astype(int)
    return df['BinarySleep']