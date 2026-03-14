import pandas as pd
import requests
from datetime import datetime

DATA_PATH = "data/Delhi_Daily_Final_Clean.csv"

LAT, LON = 28.6139, 77.2090


def fetch_weather_correct(date_str):

    url = "https://archive-api.open-meteo.com/v1/archive"

    params = {
        "latitude": LAT,
        "longitude": LON,
        "start_date": date_str,
        "end_date": date_str,
        "daily": ",".join([
            "temperature_2m_mean",
            "dewpoint_2m_mean",
            "precipitation_sum",
            "shortwave_radiation_sum",
            "surface_pressure_mean",
            "wind_speed_10m_mean"
        ]),
        "timezone": "Asia/Kolkata"
    }

    response = requests.get(url, params=params)
    data = response.json()

    daily = data["daily"]

    return {
        "temp_2m_K": daily["temperature_2m_mean"][0] + 273.15,
        "dewpoint_K": daily["dewpoint_2m_mean"][0] + 273.15,
        "precipitation_m": daily["precipitation_sum"][0] / 1000,
        "solar_radiation_Jm2": daily["shortwave_radiation_sum"][0] * 1_000_000,
        "surface_pressure_Pa": daily["surface_pressure_mean"][0] * 100,
        "wind_speed_10m": daily["wind_speed_10m_mean"][0] * .1
    }


df = pd.read_csv(DATA_PATH, parse_dates=["date"])

repair_start = pd.to_datetime("2026-02-24")

rows_to_fix = df[df["date"] >= repair_start]

print(f"Repairing {len(rows_to_fix)} rows...")

for index, row in rows_to_fix.iterrows():

    date_str = row["date"].strftime("%Y-%m-%d")
    print("Fixing:", date_str)

    weather = fetch_weather_correct(date_str)

    for col in weather:
        df.loc[index, col] = weather[col]

df.to_csv(DATA_PATH, index=False)

print("Weather repair complete.")