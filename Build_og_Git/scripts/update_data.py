import pandas as pd
from datetime import datetime, timedelta
import requests
import ee
import math

DATA_PATH = "/Users/shikkoustic/Desktop/ML Project/Build-og/data/Delhi_Daily_Final_Clean.csv"
TOKEN = "f22c501a3abdfbd251318e357186b59ddb52c894"

LAT, LON = 28.6139, 77.2090

ee.Initialize(project="aqi-shikkoustic")

today = datetime.now().date()
yesterday = today - timedelta(days=1)

start_date = yesterday - timedelta(days=6)
end_date = yesterday + timedelta(days=1)


def fetch_pm25():

    stations = [
        "delhi/anand-vihar",
        "delhi/major-dhyan-chand-national-stadium",
        "delhi/punjabi-bagh",
        "delhi/lodhi-road",
        "delhi/okhla-phase-2"
    ]

    vals = []

    for s in stations:

        try:
            url = f"https://api.waqi.info/feed/{s}/?token={TOKEN}"
            data = requests.get(url,timeout=10).json()

            pm = data["data"]["iaqi"].get("pm25",{}).get("v")

            if pm:
                vals.append(pm)

        except:
            pass

    if len(vals)==0:
        return None

    return sum(vals)/len(vals)


def fetch_aod_range():

    india = ee.FeatureCollection("FAO/GAUL/2015/level2")

    delhi = india.filter(
        ee.Filter.And(
            ee.Filter.eq('ADM0_NAME','India'),
            ee.Filter.eq('ADM1_NAME','Delhi')
        )
    )

    modis = (
        ee.ImageCollection("MODIS/061/MCD19A2_GRANULES")
        .filterDate(str(start_date),str(end_date))
        .select("Optical_Depth_055")
    )

    start = ee.Date(str(start_date))
    end = ee.Date(str(end_date))

    nDays = end.difference(start,'day')

    daily = ee.ImageCollection(
        ee.List.sequence(0,nDays.subtract(1)).map(
            lambda d: modis
            .filterDate(start.advance(d,'day'),start.advance(d,'day').advance(1,'day'))
            .mean()
            .set('system:time_start',start.advance(d,'day').millis())
        )
    )

    def extract(img):

        stats = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=delhi.geometry(),
            scale=1000,
            maxPixels=1e13
        )

        value = ee.Algorithms.If(
            stats.contains("Optical_Depth_055"),
            stats.get("Optical_Depth_055"),
            None
        )

        return ee.Feature(None,{
            "date":ee.Date(img.get("system:time_start")).format("YYYY-MM-dd"),
            "AOD_055":value
        })

    feats = daily.map(extract).getInfo()["features"]

    out={}

    for f in feats:

        d=f["properties"]["date"]
        v = f["properties"].get("AOD_055")

        if v is not None:
            out[d]=v

    return out

def fetch_weather_range():

    india = ee.FeatureCollection("FAO/GAUL/2015/level2")

    delhi = india.filter(
        ee.Filter.And(
            ee.Filter.eq('ADM0_NAME','India'),
            ee.Filter.eq('ADM1_NAME','Delhi')
        )
    )

    collection = (
        ee.ImageCollection("ECMWF/ERA5_LAND/DAILY_AGGR")
        .filterDate(str(start_date),str(end_date))
        .select([
            'temperature_2m',
            'dewpoint_temperature_2m',
            'u_component_of_wind_10m',
            'v_component_of_wind_10m',
            'surface_pressure',
            'total_precipitation_sum',
            'surface_solar_radiation_downwards_sum'
        ])
    )

    def extract(img):

        stats = img.reduceRegion(
            reducer=ee.Reducer.mean(),
            geometry=delhi.geometry(),
            scale=10000,
            maxPixels=1e13
        )

        u=ee.Number(stats.get('u_component_of_wind_10m'))
        v=ee.Number(stats.get('v_component_of_wind_10m'))

        wind=u.pow(2).add(v.pow(2)).sqrt()

        return ee.Feature(None,{
            "date":ee.Date(img.get("system:time_start")).format("YYYY-MM-dd"),
            "temp_2m_K":stats.get('temperature_2m'),
            "dewpoint_K":stats.get('dewpoint_temperature_2m'),
            "surface_pressure_Pa":stats.get('surface_pressure'),
            "precipitation_m":stats.get('total_precipitation_sum'),
            "solar_radiation_Jm2":stats.get('surface_solar_radiation_downwards_sum'),
            "wind_speed_10m":wind
        })

    feats=collection.map(extract).getInfo()["features"]

    out={}

    for f in feats:

        d=f["properties"]["date"]
        out[d]=f["properties"]

    return out


def openmeteo(date):

    url="https://archive-api.open-meteo.com/v1/archive"

    params={
        "latitude":LAT,
        "longitude":LON,
        "start_date":date,
        "end_date":date,
        "daily":"temperature_2m_mean,dewpoint_2m_mean,precipitation_sum,shortwave_radiation_sum,surface_pressure_mean,wind_speed_10m_mean",
        "timezone":"Asia/Kolkata"
    }

    try:

        r=requests.get(url,params=params).json()
        d=r["daily"]

        return{
        "temp_2m_K":d["temperature_2m_mean"][0]+273.15,
        "dewpoint_K":d["dewpoint_2m_mean"][0]+273.15,
        "precipitation_m":d["precipitation_sum"][0]/1000,
        "solar_radiation_Jm2":d["shortwave_radiation_sum"][0]*1e6,
        "surface_pressure_Pa":d["surface_pressure_mean"][0]*100,
        "wind_speed_10m":d["wind_speed_10m_mean"][0]
        }

    except:
        return None


df=pd.read_csv(DATA_PATH)
df["date"]=pd.to_datetime(df["date"])
df["AOD_055"]=df["AOD_055"].interpolate(limit_direction="both")


aod_data=fetch_aod_range()
weather_data=fetch_weather_range()
pm25=fetch_pm25()

for i in range(7):

    d=(start_date+timedelta(days=i)).strftime("%Y-%m-%d")
    print("\nProcessing:",d)

    row={"date":pd.to_datetime(d)}

    # AOD
    if d in aod_data:

        row["AOD_055"]=aod_data[d]
        print("AOD_055 → GEE:",round(row["AOD_055"],3))

    else:

        interp=df["AOD_055"].iloc[-1]
        row["AOD_055"]=interp
        print("AOD_055 → Interpolated:",round(interp,3))

    
    if d in weather_data:

        w=weather_data[d]

        for k,v in w.items():

            if k!="date":

                row[k]=v
                print(k,"→ GEE:",round(v,3))

    else:

        om=openmeteo(d)

        if om:

            for k,v in om.items():

                row[k]=v
                print(k,"→ OpenMeteo:",round(v,3))

    existing=df[df["date"]==pd.to_datetime(d)]

    if len(existing)>0:

        print("Overwriting row for",d)
        df.loc[df["date"]==pd.to_datetime(d),list(row.keys())]=list(row.values())

    else:

        print("Appending row for",d)
        df=pd.concat([df,pd.DataFrame([row])],ignore_index=True)

if pm25:

    print("\nPM2.5 → WAQI API:",round(pm25,2))
    df.loc[df["date"]==pd.to_datetime(yesterday),"PM2.5"]=pm25


df=df.sort_values("date")
df.to_csv(DATA_PATH,index=False)

print("\nDataset updated successfully.")