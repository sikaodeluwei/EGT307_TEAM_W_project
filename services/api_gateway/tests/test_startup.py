from services.api_gateway import main
from services.api_gateway.schemas import VehicleTelemetryInput


def test_gateway_imports_with_authoritative_telemetry_schema():
    predict_route = next(
        route for route in main.app.routes if getattr(route, "path", None) == "/predict"
    )

    assert predict_route.endpoint.__annotations__["telemetry"] is VehicleTelemetryInput
