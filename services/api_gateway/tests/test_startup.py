from pathlib import Path

from services.api_gateway import main
from services.api_gateway.schemas import VehicleTelemetryInput


def test_gateway_imports_with_authoritative_telemetry_schema():
    predict_route = next(
        route for route in main.app.routes if getattr(route, "path", None) == "/predict"
    )

    assert predict_route.endpoint.__annotations__["telemetry"] is VehicleTelemetryInput


def test_container_manifests_match_gateway_service_ports():
    project_root = Path(__file__).resolve().parents[3]
    gateway_manifest = (project_root / "k8s" / "api-gateway.yaml").read_text(
        encoding="utf-8"
    )
    gateway_dockerfile = (
        project_root / "services" / "api_gateway" / "Dockerfile"
    ).read_text(encoding="utf-8")

    assert "containerPort: 8000" in gateway_manifest
    assert "- port: 8000" in gateway_manifest
    assert "targetPort: 8000" in gateway_manifest
    assert 'value: "http://ai-inference-service:8001"' in gateway_manifest
    assert 'value: "http://database-service:8000"' in gateway_manifest
    assert "EXPOSE 8000" in gateway_dockerfile
