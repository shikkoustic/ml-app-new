import pickle
import numpy as np
import pandas as pd
from ml.aqi import aqi_transition_message
from ml.preprocess import load_dataset, create_features
from ml.aqi import pm25_to_aqi, aqi_category


MODEL_PATH = "/Users/shikkoustic/Desktop/ML Project/Build-og/saved_models/pm25_model.pkl"
FEATURE_PATH = "/Users/shikkoustic/Desktop/ML Project/Build-og/saved_models/feature_columns.pkl"
METRICS_PATH = "/Users/shikkoustic/Desktop/ML Project/Build-og/saved_models/model_metrics.pkl"


def aqi_color(aqi):

    if aqi <= 50:
        return "#00e400"     # Good
    elif aqi <= 100:
        return "#9cff00"     # Satisfactory
    elif aqi <= 200:
        return "#ffff00"     # Moderate
    elif aqi <= 300:
        return "#ff7e00"     # Poor
    elif aqi <= 400:
        return "#ff0000"     # Very Poor
    else:
        return "#7e0023"     # Severe


def load_model():

    with open(MODEL_PATH, "rb") as f:
        model = pickle.load(f)

    with open(FEATURE_PATH, "rb") as f:
        feature_columns = pickle.load(f)

    with open(METRICS_PATH, "rb") as f:
        metrics = pickle.load(f)

    mae = metrics["mae"]

    return model, feature_columns, mae


def predict_next_day():

    model, feature_columns, mae = load_model()

    raw_df = load_dataset()
    last_data_date = pd.to_datetime(raw_df["date"].iloc[-1])

    prediction_date = last_data_date + pd.Timedelta(days=1)

    df = create_features(raw_df)
    df = df.dropna(subset=feature_columns).reset_index(drop=True)

    last_row = df.iloc[-1]

    X_input = last_row[feature_columns].values.reshape(1, -1)
    log_prediction = model.predict(X_input)[0]

    predicted_pm25 = float(np.expm1(log_prediction))

    lower_pm25 = max(predicted_pm25 - mae, 0)
    upper_pm25 = predicted_pm25 + mae
    predicted_aqi = pm25_to_aqi(predicted_pm25)
    lower_aqi = pm25_to_aqi(lower_pm25)
    upper_aqi = pm25_to_aqi(upper_pm25)

    # Round AQI values
    predicted_aqi = round(predicted_aqi)
    lower_aqi = round(lower_aqi)
    upper_aqi = round(upper_aqi)

    category = aqi_category(predicted_aqi)
    message = aqi_transition_message(predicted_aqi)

    color = aqi_color(predicted_aqi)

    return {

        "prediction_date": prediction_date.strftime("%Y-%m-%d"),
        "last_data_date": last_data_date.strftime("%Y-%m-%d"),

        "predicted_pm25": round(predicted_pm25, 2),
        "pm25_low": round(lower_pm25, 2),
        "pm25_high": round(upper_pm25, 2),

        "predicted_aqi": predicted_aqi,
        "aqi_low": lower_aqi,
        "aqi_high": upper_aqi,

        "category": category,
        "color": color,
        "transition_message": message
    }


if __name__ == "__main__":
    result = predict_next_day()
    print(result)