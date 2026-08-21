import json
import shutil
import subprocess
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[3]


def _published_port(service: dict, target: int) -> int | None:
    for port in service.get("ports", []):
        if int(port["target"]) == target:
            return int(port["published"])
    return None


def test_compose_config_wires_the_complete_application():
    compose_path = PROJECT_ROOT / "compose.yaml"
    assert compose_path.exists(), "compose.yaml must exist at the repository root"

    docker = shutil.which("docker")
    if docker is None:
        pytest.skip("Docker CLI is required to validate compose.yaml")

    result = subprocess.run(
        [
            docker,
            "compose",
            "-f",
            str(compose_path),
            "config",
            "--no-path-resolution",
            "--format",
            "json",
        ],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr

    config = json.loads(result.stdout)
    services = config["services"]
    assert set(services) == {"database", "ai-inference", "api-gateway", "dashboard"}

    assert services["database"]["environment"]["DATABASE_PATH"] == "/data/autocare.db"
    assert _published_port(services["database"], 8000) == 8001
    assert any(volume["target"] == "/data" for volume in services["database"]["volumes"])

    assert _published_port(services["ai-inference"], 8001) == 8002
    assert services["api-gateway"]["environment"] == {
        "AI_SERVICE_URL": "http://ai-inference:8001",
        "DATABASE_SERVICE_URL": "http://database:8000",
    }
    assert _published_port(services["api-gateway"], 8000) == 8000

    assert services["dashboard"]["environment"]["API_GATEWAY_URL"] == (
        "http://api-gateway:8000"
    )
    assert _published_port(services["dashboard"], 8501) == 8501
