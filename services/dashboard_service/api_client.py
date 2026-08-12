from collections.abc import Mapping
from typing import Any

import requests


TELEMETRY_FIELDS = (
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
)

REQUIRED_PREDICTION_FIELDS = {
    "maintenance_decision",
    "confidence_score",
    "identified_issues",
}


class ApiClientError(RuntimeError):
    """Raised when the API Gateway cannot provide a usable response."""


class HistoryUnavailableError(ApiClientError):
    """Raised when the API Gateway does not yet expose prediction history."""


def build_telemetry_payload(values: Mapping[str, Any]) -> dict[str, Any]:
    if set(values) != set(TELEMETRY_FIELDS):
        raise ValueError("Telemetry fields do not match the API Gateway schema")
    return {field: values[field] for field in TELEMETRY_FIELDS}


def _request_json(request_method, unavailable_message: str | None = None):
    try:
        response = request_method()
        if response.status_code == 404 and unavailable_message:
            raise HistoryUnavailableError(unavailable_message)
        response.raise_for_status()
        return response.json()
    except HistoryUnavailableError:
        raise
    except requests.Timeout as error:
        raise ApiClientError("The API Gateway timed out. Please try again.") from error
    except requests.ConnectionError as error:
        raise ApiClientError("The API Gateway is unavailable. Check that it is running.") from error
    except requests.HTTPError as error:
        status_code = error.response.status_code if error.response is not None else "unknown"
        raise ApiClientError(f"The API Gateway returned HTTP {status_code}.") from error
    except (requests.exceptions.JSONDecodeError, ValueError) as error:
        raise ApiClientError("The API Gateway did not return valid JSON.") from error
    except requests.RequestException as error:
        raise ApiClientError("The API Gateway request failed.") from error


def predict_vehicle(
    telemetry: Mapping[str, Any],
    api_gateway_url: str,
    session=requests,
) -> dict[str, Any]:
    payload = build_telemetry_payload(telemetry)
    url = f"{api_gateway_url.rstrip('/')}/predict"
    result = _request_json(lambda: session.post(url, json=payload, timeout=10.0))

    if not isinstance(result, dict) or not REQUIRED_PREDICTION_FIELDS.issubset(result):
        raise ApiClientError("The prediction response is missing required fields.")
    decision = result["maintenance_decision"]
    confidence = result["confidence_score"]
    issues = result["identified_issues"]
    invalid_fields = (
        not isinstance(decision, str)
        or not decision.strip()
        or isinstance(confidence, bool)
        or not isinstance(confidence, (int, float))
        or not 0 <= confidence <= 100
        or not isinstance(issues, list)
        or not all(isinstance(issue, str) for issue in issues)
    )
    if invalid_fields:
        raise ApiClientError("The prediction response contains invalid field values.")

    return result


def fetch_history(api_gateway_url: str, session=requests) -> list[dict[str, Any]]:
    url = f"{api_gateway_url.rstrip('/')}/history"
    result = _request_json(
        lambda: session.get(url, timeout=10.0),
        unavailable_message="Prediction history is not implemented by the API Gateway yet.",
    )

    if isinstance(result, list):
        records = result
    elif isinstance(result, dict) and isinstance(result.get("records"), list):
        records = result["records"]
    else:
        raise ApiClientError("The API Gateway returned an invalid history response.")

    if not all(isinstance(record, dict) for record in records):
        raise ApiClientError("The API Gateway returned an invalid history response.")
    return records


def get_display_level(maintenance_decision: str) -> str:
    return {
        "Safe for Driving": "success",
        "At Risk": "warning",
        "Needs Immediate Maintenance": "error",
    }.get(maintenance_decision, "info")
