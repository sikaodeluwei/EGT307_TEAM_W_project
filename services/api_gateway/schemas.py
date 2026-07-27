from typing import List, Optional
from pydantic import BaseModel, Field


class VehicleTelemetryInput(BaseModel):
    Car_Model: str = Field(
        ..., example="Honda Fit", description="Vehicle model name"
    )
    Vehicle_Age_Years: float = Field(
        ...,
        ge=0.0,
        le=30.0,
        example=3.5,
        description="Vehicle age in years",
    )
    Total_Mileage_KM: int = Field(
        ...,
        ge=0,
        le=1000000,
        example=47912,
        description="Total mileage in km",
    )
    Tire_Pressure_PSI: float = Field(
        ...,
        ge=10.0,
        le=60.0,
        example=32.3,
        description="Tire pressure in PSI",
    )
    Engine_RPM: int = Field(
        ..., ge=0, le=10000, example=3607, description="Engine RPM"
    )
    Battery_Voltage_V: float = Field(
        ...,
        ge=8.0,
        le=18.0,
        example=12.7,
        description="Battery voltage in Volts",
    )
    Fuel_Level_Percent: float = Field(
        ...,
        ge=0.0,
        le=100.0,
        example=13.1,
        description="Fuel level percentage",
    )
    Coolant_Temperature_C: float = Field(
        ...,
        ge=0.0,
        le=150.0,
        example=96.0,
        description="Coolant temperature in °C",
    )
    Brake_Pad_Thickness_mm: float = Field(
        ...,
        ge=0.0,
        le=20.0,
        example=7.4,
        description="Brake pad thickness in mm",
    )
    O2_Sensor_Voltage_V: float = Field(
        ...,
        ge=0.0,
        le=2.0,
        example=0.86,
        description="O2 sensor reading in Volts",
    )


class PredictionResponse(BaseModel):
    maintenance_decision: str
    confidence_score: float
    identified_issues: List[str]
    status: str = "success"
