from pathlib import Path
from typing import List

import joblib
import pandas as pd
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field


class VehicleTelemetryInput(BaseModel):
    Car_Model: str = Field(..., example="Honda Fit")
    Vehicle_Age_Years: float = Field(..., ge=0.0, le=30.0)
    Total_Mileage_KM: int = Field(..., ge=0, le=1000000)
    Tire_Pressure_PSI: float = Field(..., ge=10.0, le=60.0)
    Engine_RPM: int = Field(..., ge=0, le=10000)
    Battery_Voltage_V: float = Field(..., ge=8.0, le=18.0)
    Fuel_Level_Percent: float = Field(..., ge=0.0, le=100.0)
    Coolant_Temperature_C: float = Field(..., ge=0.0, le=150.0)
    Brake_Pad_Thickness_mm: float = Field(..., ge=0.0, le=20.0)
    O2_Sensor_Voltage_V: float = Field(..., ge=0.0, le=2.0)


class PredictionResponse(BaseModel):
    maintenance_decision: str
    confidence_score: float
    identified_issues: List[str]
    status: str = "success"


app = FastAPI(
    title="AutoCare AI Inference Service",
    description="Loads the trained Random Forest pipeline and predicts vehicle maintenance condition.",
    version="1.0.0",
)


current_file = Path(__file__).resolve()
model_path = current_file.parent / "vehicle_maintenance_model.pkl"

if not model_path.exists():
    raise FileNotFoundError(
        f"Trained model not found at: {model_path}"
    )

model = joblib.load(model_path)


def identify_issues(data: dict) -> List[str]:
    issues = []

    if data["Tire_Pressure_PSI"] < 28:
        issues.append("Low tire pressure detected")

    if data["Battery_Voltage_V"] < 12.0:
        issues.append("Low battery voltage detected")

    if data["Coolant_Temperature_C"] > 105:
        issues.append("High coolant temperature detected")

    if data["Brake_Pad_Thickness_mm"] < 3.0:
        issues.append("Brake pad thickness is critically low")

    if data["O2_Sensor_Voltage_V"] < 0.1 or data["O2_Sensor_Voltage_V"] > 0.9:
        issues.append("O2 sensor reading is outside the normal range")

    if data["Engine_RPM"] > 5000:
        issues.append("Engine RPM is unusually high")

    if not issues:
        issues.append(
            "No major telemetry issues detected from the submitted values"
        )

    return issues


@app.get("/")
def root():
    return {
        "service": "AI Inference Service",
        "status": "online",
        "docs_url": "/docs",
    }


@app.get("/health")
def health_check():
    return {
        "status": "healthy",
        "service": "ai_inference_service",
        "model_loaded": True,
    }


@app.post("/predict", response_model=PredictionResponse)
def predict_maintenance(telemetry: VehicleTelemetryInput):
    try:
        input_data = telemetry.model_dump()

        input_dataframe = pd.DataFrame([input_data])

        prediction = model.predict(input_dataframe)[0]

        prediction_probabilities = model.predict_proba(
            input_dataframe
        )[0]

        confidence_score = round(
            float(max(prediction_probabilities)) * 100,
            2,
        )

        identified_issues = identify_issues(input_data)

        return PredictionResponse(
            maintenance_decision=str(prediction),
            confidence_score=confidence_score,
            identified_issues=identified_issues,
            status="success",
        )

    except Exception as error:
        raise HTTPException(
            status_code=500,
            detail=f"AI Inference Service Error: {str(error)}",
        )
