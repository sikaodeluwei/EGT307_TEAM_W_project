import json
import os

import pandas as pd
import streamlit as st

try:
    from .api_client import (
        ApiClientError,
        HistoryUnavailableError,
        fetch_history,
        get_display_level,
        predict_vehicle,
    )
except ImportError:
    from api_client import (
        ApiClientError,
        HistoryUnavailableError,
        fetch_history,
        get_display_level,
        predict_vehicle,
    )


API_GATEWAY_URL = os.getenv("API_GATEWAY_URL", "http://127.0.0.1:8000")


def display_prediction(result: dict) -> None:
    decision = str(result["maintenance_decision"])
    confidence = result["confidence_score"]
    level = get_display_level(decision)
    message = f"Maintenance decision: {decision}"
    getattr(st, level)(message)

    first, second = st.columns(2)
    first.metric("Maintenance decision", decision)
    second.metric("Confidence score", f"{confidence:.2f}%")

    st.subheader("Identified issues")
    issues = result.get("identified_issues", [])
    if issues:
        for issue in issues:
            st.write(f"- {issue}")
    else:
        st.write("No issues were returned by the API.")

    if result.get("status"):
        st.caption(f"API status: {result['status']}")


def history_table(records: list[dict]) -> pd.DataFrame:
    rows = []
    for record in records:
        row = dict(record)
        if isinstance(row.get("input_data"), dict):
            row["input_data"] = json.dumps(row["input_data"], ensure_ascii=False)
        if isinstance(row.get("identified_issues"), list):
            row["identified_issues"] = "; ".join(map(str, row["identified_issues"]))
        rows.append(row)
    return pd.DataFrame(rows)


st.set_page_config(page_title="AutoCare AI", page_icon="🚗", layout="wide")
st.title("AutoCare AI")
st.caption("Smart Vehicle Maintenance Prediction System")
st.info(f"Connected through API Gateway: {API_GATEWAY_URL}")

st.header("Vehicle Input")
with st.form("vehicle_input_form"):
    left, right = st.columns(2)
    with left:
        car_model = st.text_input("Car Model", value="Honda Fit")
        vehicle_age = st.number_input(
            "Vehicle Age (years)", min_value=0.0, max_value=30.0, value=3.5, step=0.5
        )
        mileage = st.number_input(
            "Total Mileage (km)", min_value=0, max_value=1_000_000, value=47_912, step=1
        )
        tire_pressure = st.number_input(
            "Tire Pressure (PSI)", min_value=10.0, max_value=60.0, value=32.3, step=0.1
        )
        engine_rpm = st.number_input(
            "Engine RPM", min_value=0, max_value=10_000, value=3_607, step=1
        )
    with right:
        battery_voltage = st.number_input(
            "Battery Voltage (V)", min_value=8.0, max_value=18.0, value=12.7, step=0.1
        )
        fuel_level = st.number_input(
            "Fuel Level (%)", min_value=0.0, max_value=100.0, value=13.1, step=0.1
        )
        coolant_temperature = st.number_input(
            "Coolant Temperature (°C)", min_value=0.0, max_value=150.0, value=96.0, step=0.1
        )
        brake_pad_thickness = st.number_input(
            "Brake Pad Thickness (mm)", min_value=0.0, max_value=20.0, value=7.4, step=0.1
        )
        o2_sensor_voltage = st.number_input(
            "O2 Sensor Voltage (V)", min_value=0.0, max_value=2.0, value=0.86, step=0.01
        )

    submitted = st.form_submit_button("Predict Maintenance", type="primary")

if submitted:
    telemetry = {
        "Car_Model": car_model,
        "Vehicle_Age_Years": vehicle_age,
        "Total_Mileage_KM": mileage,
        "Tire_Pressure_PSI": tire_pressure,
        "Engine_RPM": engine_rpm,
        "Battery_Voltage_V": battery_voltage,
        "Fuel_Level_Percent": fuel_level,
        "Coolant_Temperature_C": coolant_temperature,
        "Brake_Pad_Thickness_mm": brake_pad_thickness,
        "O2_Sensor_Voltage_V": o2_sensor_voltage,
    }
    try:
        with st.spinner("Requesting prediction..."):
            prediction = predict_vehicle(telemetry, API_GATEWAY_URL)
        display_prediction(prediction)
    except (ApiClientError, ValueError) as error:
        st.error(str(error))

st.divider()
st.header("Prediction History")
if st.button("Refresh History"):
    try:
        with st.spinner("Loading prediction history..."):
            prediction_history = fetch_history(API_GATEWAY_URL)
        if prediction_history:
            st.dataframe(history_table(prediction_history), use_container_width=True, hide_index=True)
        else:
            st.info("No prediction records are available yet.")
    except HistoryUnavailableError as error:
        st.warning(str(error))
    except ApiClientError as error:
        st.error(str(error))
