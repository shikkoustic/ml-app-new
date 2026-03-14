def pm25_to_aqi(pm25):
    if pm25 is None:
        return None

    return round(float(pm25), 2)


def aqi_category(aqi):

    if aqi is None:
        return "Unknown"

    if aqi <= 50:
        return "Good"
    elif aqi <= 100:
        return "Satisfactory"
    elif aqi <= 200:
        return "Moderate"
    elif aqi <= 300:
        return "Poor"
    elif aqi <= 400:
        return "Very Poor"
    else:
        return "Severe"


def aqi_transition_message(aqi, margin=15):
  
    boundaries = [
        (50, "Good", "Satisfactory"),
        (100, "Satisfactory", "Moderate"),
        (200, "Moderate", "Poor"),
        (300, "Poor", "Very Poor"),
        (400, "Very Poor", "Severe")
    ]

    for boundary, lower_cat, upper_cat in boundaries:

        if (boundary - margin) <= aqi <= (boundary - 1):
            return f"Air quality is in the {lower_cat} to {upper_cat} transition zone"

        if (boundary + 1) <= aqi <= (boundary + margin):
            return f"Air quality is in the {lower_cat} to {upper_cat} transition zone"

    return None