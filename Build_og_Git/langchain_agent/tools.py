from langchain.tools import tool
from ml.predict import predict_next_day
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

@tool
def get_aqi_forecast(query: str) -> str:
    """
    Returns today's AQI forecast and explanation.
    """

    result = predict_next_day()

    message = result['transition_message'] or "No transition warning."

    return f"""
Today's AQI Prediction:

Date: {result['prediction_date']}

Predicted AQI: {result['predicted_aqi']}
Category: {result['category']}

PM2.5 Prediction: {result['predicted_pm25']} µg/m³

AQI Range: {result['aqi_low']} - {result['aqi_high']}

If the user asks for explanation or advice, analyze this data and provide insights.
"""