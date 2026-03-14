import pandas as pd
import numpy as np


DATA_PATH = "/Users/shikkoustic/Desktop/ML Project/Build-og/data/Delhi_Daily_Final_Clean.csv"


def load_dataset():

    df = pd.read_csv(DATA_PATH)
    # Convert mixed date formats safely
    df["date"] = pd.to_datetime(df["date"], format="mixed")
    df = df.sort_values("date").reset_index(drop=True)
    return df


def create_features(df):

    df["pm25_lag1"] = df["PM2.5"].shift(1)
    df["pm25_lag2"] = df["PM2.5"].shift(2)
    df["pm25_lag3"] = df["PM2.5"].shift(3)
    df["pm25_lag4"] = df["PM2.5"].shift(4)
    df["pm25_lag5"] = df["PM2.5"].shift(5)
    df["pm25_lag6"] = df["PM2.5"].shift(6)
    df["pm25_lag7"] = df["PM2.5"].shift(7)

    df["aod_lag1"] = df["AOD_055"].shift(1)
    df["aod_lag2"] = df["AOD_055"].shift(2)

    df["pm25_roll3"] = df["PM2.5"].rolling(3).mean()
    df["pm25_roll7"] = df["PM2.5"].rolling(7).mean()
    df["pm25_trend"] = df["pm25_lag1"] - df["pm25_lag3"]

    df["month"] = df["date"].dt.month
    df["day_of_year"] = df["date"].dt.dayofyear
    df["day_of_week"] = df["date"].dt.dayofweek

    # Seasonal indicators
    df["is_winter"] = df["month"].isin([11, 12, 1, 2]).astype(int)
    df["is_monsoon"] = df["month"].isin([7, 8, 9]).astype(int)
    df["is_post_monsoon"] = df["month"].isin([10, 11]).astype(int)
    df["target"] = np.log1p(df["PM2.5"].shift(-1))

    return df


def get_training_data():

    df = load_dataset()
    df = create_features(df)

    # Drop NaNs from shifting
    df = df.dropna().reset_index(drop=True)

    feature_columns = [

        # Weather
        "temp_2m_K",
        "dewpoint_K",
        "precipitation_m",
        "solar_radiation_Jm2",
        "surface_pressure_Pa",
        "wind_speed_10m",

        # AOD
        "AOD_055",
        "aod_lag1",
        "aod_lag2",

        # PM2.5 history (1 week memory)
        "pm25_lag1",
        "pm25_lag2",
        "pm25_lag3",
        "pm25_lag4",
        "pm25_lag5",
        "pm25_lag6",
        "pm25_lag7",

        # Rolling pollution
        "pm25_roll3",
        "pm25_roll7",

        # Pollution trend
        "pm25_trend",

        # Time
        "month",
        "day_of_year",
        "day_of_week",

        # Seasonal flags
        "is_winter",
        "is_monsoon",
        "is_post_monsoon",
    ]

    X = df[feature_columns]
    y = df["target"]

    return X, y, feature_columns