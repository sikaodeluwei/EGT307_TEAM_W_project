from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _deployment_image(manifest_name: str) -> str:
    manifest = (PROJECT_ROOT / "k8s" / manifest_name).read_text(encoding="utf-8")
    image_lines = [
        line.strip() for line in manifest.splitlines() if line.strip().startswith("image:")
    ]
    assert len(image_lines) == 1
    return image_lines[0].split(":", 1)[1].strip()


@pytest.mark.parametrize(
    ("manifest_name", "expected_image"),
    [
        ("dashboard.yaml", "caozhenyu33/autocare-dashboard:v1"),
        ("database.yaml", "caozhenyu33/autocare-database:v1"),
    ],
)
def test_owned_deployments_use_public_versioned_images(
    manifest_name: str, expected_image: str
):
    assert _deployment_image(manifest_name) == expected_image
