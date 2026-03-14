import pandas as pd
from datetime import datetime, timedelta
import requests
import ee
from datetime import datetime
import os
import sys

RUN_LOG_PATH = "/Users/shikkoustic/Desktop/ML Project/Build-og/data/last_run.txt"

now = datetime.now()
today_str = now.strftime("%Y-%m-%d")

# Only allow execution after 3 PM
if now.hour < 15:
    print("Before 3 PM. Skipping execution.")
    sys.exit()

# Prevent multiple runs per day
if os.path.exists(RUN_LOG_PATH):
    with open(RUN_LOG_PATH, "r") as f:
        last_run_date = f.read().strip()

    if last_run_date == today_str:
        print("Already ran today. Skipping.")
        sys.exit()

print("Run conditions satisfied. Executing updater...")
# ======================================================
# CONFIGURATION
# ======================================================

TOKEN = "f22c501a3abdfbd251318e357186b59ddb52c894"
PROJECT_ID = "aqi-shikkoustic"   # Your Google Cloud Project ID
DATA_PATH = "/Users/shikkoustic/Desktop/ML Project/Build-og/data/Delhi_Daily_Final_Clean.csv"

LAT, LON = 28.6139, 77.2090  # New Delhi coordinates

# ======================================================
# INITIALIZE EARTH ENGINE (ONLY ONCE)
# ======================================================

ee.Initialize(project=PROJECT_ID)

# ======================================================
# PM2.5 FROM WAQI
# ======================================================

def fetch_pm25_new_delhi():

    url = f"https://api.waqi.info/feed/new-delhi/?token={TOKEN}"
    response = requests.get(url, timeout=15)
    data = response.json()

    if data["status"] != "ok":
        raise Exception("WAQI API Error")

    # Get hourly PM2.5 forecast data
    hourly_data = data["data"].get("forecast", {}).get("hourly", {}).get("pm25")

    if not hourly_data:
        raise Exception("Hourly PM2.5 data not available from WAQI")

    # Take last 24 entries (most recent hours)
    last_24 = hourly_data[-24:]

    values = []
    for entry in last_24:
        if "v" in entry:
            values.append(entry["v"])

    if len(values) == 0:
        raise Exception("No valid hourly PM2.5 values found")

    mean_pm25 = sum(values) / len(values)

    print(f"24-hour mean PM2.5 used: {mean_pm25}")

    return float(mean_pm25)

# ======================================================
# WEATHER FROM OPEN-METEO (ERA STYLE CONVERSION)
# ======================================================

def fetch_weather_era_style(date_str):

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

    response = requests.get(url, params=params, timeout=20)
    data = response.json()

    if "daily" not in data:
        raise Exception("Weather data unavailable")

    daily = data["daily"]

    return {
        "temp_2m_K": daily["temperature_2m_mean"][0] + 273.15,
        "dewpoint_K": daily["dewpoint_2m_mean"][0] + 273.15,
        "precipitation_m": daily["precipitation_sum"][0] / 1000,
        "solar_radiation_Jm2": daily["shortwave_radiation_sum"][0] * 1_000_000,
        "surface_pressure_Pa": daily["surface_pressure_mean"][0] * 100,
        "wind_speed_10m": daily["wind_speed_10m_mean"][0] * .1
    }

# ======================================================
# AOD FROM GOOGLE EARTH ENGINE
# ======================================================

def fetch_aod(date_str):

    # Load Delhi administrative boundary
    india = ee.FeatureCollection("FAO/GAUL/2015/level2")

    delhi = india.filter(
        ee.Filter.And(
            ee.Filter.eq('ADM0_NAME', 'India'),
            ee.Filter.eq('ADM1_NAME', 'Delhi')
        )
    )

    start = ee.Date(date_str)
    end = start.advance(1, 'day')

    # Load MAIAC AOD collection
    collection = (
        ee.ImageCollection("MODIS/061/MCD19A2_GRANULES")
        .filterDate(start, end)
        .select("Optical_Depth_055")
    )

    daily_mean = collection.mean()

    stats = daily_mean.reduceRegion(
        reducer=ee.Reducer.mean(),
        geometry=delhi.geometry(),
        scale=1000,
        maxPixels=1e13
    )

    result = stats.getInfo()

    # Safety check
    if result is None:
        aod_value = None
    else:
        aod_value = result.get("Optical_Depth_055")

    # -------------------------
    # Fallback if missing
    # -------------------------
    if aod_value is None:
        print("AOD missing. Using 3-day rolling mean fallback.")

        df = pd.read_csv(DATA_PATH)

        last_valid_values = df["AOD_055"].dropna().tail(3)

        if len(last_valid_values) == 0:
            raise Exception("No historical AOD available for fallback")

        rolling_mean = last_valid_values.mean()

        print(f"Fallback AOD used: {rolling_mean}")

        return float(rolling_mean)

    return float(aod_value)

# ======================================================
# FETCH COMPLETE ROW DATA
# ======================================================

def fetch_full_row(date_obj):

    date_str = date_obj.strftime("%Y-%m-%d")
    print(f"Fetching full data for {date_str}")

    pm25 = fetch_pm25_new_delhi()
    weather = fetch_weather_era_style(date_str)
    aod = fetch_aod(date_str)

    return {
        "date": date_obj,
        "AOD_055": aod,
        "PM2.5": pm25,
        **weather
    }

# ======================================================
# MAIN UPDATE FUNCTION
# ======================================================

def update_dataset():

    df = pd.read_csv(DATA_PATH, parse_dates=["date"])
    df = df.sort_values("date").reset_index(drop=True)

    last_index = df.index[-1]
    last_date = df.loc[last_index, "date"]

    print("Last date in dataset:", last_date.date())

    # --------------------------------------------------
    # 1️⃣ FIX PARTIAL LAST ROW
    # --------------------------------------------------
    if df.loc[last_index].isnull().any():
        print("Last row has missing values. Repairing...")

        full_row = fetch_full_row(last_date)

        for col in full_row:
            df.loc[last_index, col] = full_row[col]

        print("Last row repaired.")

    # --------------------------------------------------
    # 2️⃣ APPEND NEW DAY IF NEEDED
    # --------------------------------------------------
    yesterday = datetime.today().date() - timedelta(days=1)
    yesterday = pd.to_datetime(yesterday)

    if yesterday > last_date:

        print("Appending new date:", yesterday.date())

        new_row = fetch_full_row(yesterday)

        new_row_df = pd.DataFrame(columns=df.columns)

        for col in new_row:
            new_row_df.loc[0, col] = new_row[col]

        df = pd.concat([df, new_row_df], ignore_index=True)
        df = df.sort_values("date").reset_index(drop=True)

        print("New row appended.")
    else:
        print("No new date to append.")

    # --------------------------------------------------
    # SAVE
    # --------------------------------------------------
    df.to_csv(DATA_PATH, index=False)
    print("Dataset update complete.")

if __name__ == "__main__":
    try:
        update_dataset()

        # Save today's run date only if update succeeds
        with open(RUN_LOG_PATH, "w") as f:
            f.write(today_str)

        print("Run logged successfully.")

    except Exception as e:
        print("Update failed:", e)
        sys.exit(1)