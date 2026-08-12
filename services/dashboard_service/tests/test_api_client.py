import pytest
import requests

from services.dashboard_service.api_client import (
    ApiClientError,
    HistoryUnavailableError,
    build_telemetry_payload,
    fetch_history,
    get_display_level,
    predict_vehicle,
)


VALID_TELEMETRY = {
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
}


class FakeResponse:
    def __init__(self, status_code=200, payload=None, json_error=None):
        self.status_code = status_code
        self._payload = payload
        self._json_error = json_error

    def raise_for_status(self):
        if self.status_code >= 400:
            raise requests.HTTPError(f"HTTP {self.status_code}", response=self)

    def json(self):
        if self._json_error:
            raise self._json_error
        return self._payload


class FakeSession:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def post(self, url, json, timeout):
        self.calls.append(("POST", url, json, timeout))
        if self.error:
            raise self.error
        return self.response

    def get(self, url, timeout):
        self.calls.append(("GET", url, None, timeout))
        if self.error:
            raise self.error
        return self.response


def prediction_payload(decision="At Risk"):
    return {
        "maintenance_decision": decision,
        "confidence_score": 82.4,
        "identified_issues": ["Low battery voltage detected"],
        "status": "success",
    }


def test_build_telemetry_payload_keeps_exact_schema_names():
    payload = build_telemetry_payload(VALID_TELEMETRY)

    assert payload == VALID_TELEMETRY
    assert list(payload) == [
        "Car_Model",
        "Vehicle_Age_Years",
        "Total_Mileage_KM",
        "Tire_Pressure_PSI",
        "Engine_RPM",
        "Battery_Voltage_V",
        "Fuel_Level_Percent",
        "Coolant_Temperature_C",
        "Brake_Pad_Thickness_mm",
        "O2_Sensor_Voltage_V",
    ]


def test_build_telemetry_payload_rejects_missing_or_extra_fields():
    with pytest.raises(ValueError, match="Telemetry fields do not match"):
        build_telemetry_payload({"Car_Model": "Honda Fit"})

    with pytest.raises(ValueError, match="Telemetry fields do not match"):
        build_telemetry_payload({**VALID_TELEMETRY, "Renamed_Field": 1})


def test_predict_vehicle_sends_exact_payload_and_preserves_response():
    response_payload = prediction_payload("Unexpected Future Label")
    session = FakeSession(FakeResponse(payload=response_payload))

    result = predict_vehicle(
        VALID_TELEMETRY,
        "http://api-gateway:8000/",
        session=session,
    )

    assert result == response_payload
    assert session.calls == [
        (
            "POST",
            "http://api-gateway:8000/predict",
            VALID_TELEMETRY,
            10.0,
        )
    ]


@pytest.mark.parametrize(
    ("decision", "expected"),
    [
        ("Safe for Driving", "success"),
        ("At Risk", "warning"),
        ("Needs Immediate Maintenance", "error"),
        ("Unexpected Future Label", "info"),
    ],
)
def test_display_level_uses_actual_model_classes(decision, expected):
    assert get_display_level(decision) == expected


@pytest.mark.parametrize(
    ("payload", "expected"),
    [
        ([{"id": 1}], [{"id": 1}]),
        ({"records": [{"id": 2}]}, [{"id": 2}]),
    ],
)
def test_fetch_history_accepts_supported_response_shapes(payload, expected):
    session = FakeSession(FakeResponse(payload=payload))

    result = fetch_history("http://api-gateway:8000", session=session)

    assert result == expected
    assert session.calls == [
        ("GET", "http://api-gateway:8000/history", None, 10.0)
    ]


def test_missing_history_endpoint_has_specific_error():
    session = FakeSession(FakeResponse(status_code=404, payload={"detail": "Not Found"}))

    with pytest.raises(HistoryUnavailableError, match="not implemented"):
        fetch_history("http://api-gateway:8000", session=session)


@pytest.mark.parametrize(
    "error",
    [
        requests.Timeout("timed out"),
        requests.ConnectionError("connection refused"),
    ],
)
def test_network_failures_become_readable_api_errors(error):
    session = FakeSession(error=error)

    with pytest.raises(ApiClientError, match="API Gateway"):
        predict_vehicle(VALID_TELEMETRY, "http://api-gateway:8000", session=session)


def test_http_failure_becomes_readable_api_error():
    session = FakeSession(FakeResponse(status_code=503, payload={"detail": "Unavailable"}))

    with pytest.raises(ApiClientError, match="503"):
        predict_vehicle(VALID_TELEMETRY, "http://api-gateway:8000", session=session)


def test_invalid_json_becomes_readable_api_error():
    session = FakeSession(
        FakeResponse(json_error=requests.exceptions.JSONDecodeError("bad", "x", 0))
    )

    with pytest.raises(ApiClientError, match="valid JSON"):
        predict_vehicle(VALID_TELEMETRY, "http://api-gateway:8000", session=session)


def test_incomplete_prediction_response_is_rejected():
    session = FakeSession(FakeResponse(payload={"maintenance_decision": "At Risk"}))

    with pytest.raises(ApiClientError, match="missing required fields"):
        predict_vehicle(VALID_TELEMETRY, "http://api-gateway:8000", session=session)


@pytest.mark.parametrize(
    "payload",
    [
        prediction_payload(""),
        {**prediction_payload(), "confidence_score": "high"},
        {**prediction_payload(), "identified_issues": "Low voltage"},
    ],
)
def test_invalid_prediction_field_types_are_rejected(payload):
    session = FakeSession(FakeResponse(payload=payload))

    with pytest.raises(ApiClientError, match="invalid field values"):
        predict_vehicle(VALID_TELEMETRY, "http://api-gateway:8000", session=session)


def test_invalid_history_shape_is_rejected():
    session = FakeSession(FakeResponse(payload={"items": []}))

    with pytest.raises(ApiClientError, match="history response"):
        fetch_history("http://api-gateway:8000", session=session)
