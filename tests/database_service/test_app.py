from datetime import datetime

import pytest
from fastapi.testclient import TestClient

from services.database_service import app as database_app


@pytest.fixture
def client(tmp_path, monkeypatch):
    database_path = tmp_path / "autocare-test.db"
    monkeypatch.setenv("DATABASE_PATH", str(database_path))
    database_app.initialize_database()

    with TestClient(database_app.app) as test_client:
        yield test_client


@pytest.fixture
def record_payload():
    return {
        "input_data": {
            "Car_Model": "Honda Fit",
            "Vehicle_Age_Years": 3.5,
            "Total_Mileage_KM": 47912,
            "Tire_Pressure_PSI": 32.3,
            "Engine_RPM": 3607,
            "Battery_Voltage_V": 12.7,
            "Fuel_Level_Percent": 13.1,
            "Coolant_Temperature_C": 96.0,
            "Brake_Pad_Thickness_mm": 7.4,
            "O2_Sensor_Voltage_V": 0.86,
        },
        "maintenance_decision": "Unexpected Future Label",
        "confidence_score": 88.25,
        "identified_issues": ["Example issue returned by AI"],
        "recommendation": None,
        "model_version": None,
    }


def test_health_confirms_database_connection(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.json() == {
        "status": "healthy",
        "service": "database_service",
        "database": "connected",
    }


def test_create_list_and_get_preserve_complete_record(client, record_payload):
    created_response = client.post("/records", json=record_payload)

    assert created_response.status_code == 201
    created = created_response.json()
    assert created["id"] == 1
    assert created["input_data"] == record_payload["input_data"]
    assert created["maintenance_decision"] == "Unexpected Future Label"
    assert created["confidence_score"] == 88.25
    assert created["identified_issues"] == ["Example issue returned by AI"]
    assert created["recommendation"] is None
    assert created["model_version"] is None
    assert datetime.fromisoformat(created["timestamp"])

    list_response = client.get("/records")
    assert list_response.status_code == 200
    assert list_response.json() == [created]

    get_response = client.get("/records/1")
    assert get_response.status_code == 200
    assert get_response.json() == created


def test_records_are_returned_newest_first(client, record_payload):
    first = client.post("/records", json=record_payload).json()
    second_payload = {
        **record_payload,
        "maintenance_decision": "Safe for Driving",
        "identified_issues": [],
    }
    second = client.post("/records", json=second_payload).json()

    records = client.get("/records").json()

    assert [record["id"] for record in records] == [second["id"], first["id"]]


def test_invalid_telemetry_is_rejected(client, record_payload):
    invalid_payload = {
        **record_payload,
        "input_data": {
            **record_payload["input_data"],
            "Tire_Pressure_PSI": 9.9,
        },
    }

    response = client.post("/records", json=invalid_payload)

    assert response.status_code == 422


def test_car_model_validation_matches_gateway_schema(client, record_payload):
    payload = {
        **record_payload,
        "input_data": {**record_payload["input_data"], "Car_Model": ""},
    }

    response = client.post("/records", json=payload)

    assert response.status_code == 201
    assert response.json()["input_data"]["Car_Model"] == ""


def test_empty_decision_is_rejected(client, record_payload):
    response = client.post(
        "/records",
        json={**record_payload, "maintenance_decision": ""},
    )

    assert response.status_code == 422


def test_missing_record_returns_404(client):
    response = client.get("/records/999")

    assert response.status_code == 404
    assert response.json() == {"detail": "Prediction record not found"}
