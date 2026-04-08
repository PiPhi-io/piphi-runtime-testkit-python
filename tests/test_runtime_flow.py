from __future__ import annotations

import json
from urllib import request

from piphi_runtime_testkit_python import (
    assert_event_sent,
    assert_telemetry_sent,
    build_config_payload,
    build_runtime_headers,
)
from piphi_runtime_testkit_python.mock_core import EVENT_PATH, TELEMETRY_PATH


def _post(url: str, payload: dict, headers: dict[str, str] | None = None) -> tuple[int, dict]:
    encoded = json.dumps(payload).encode("utf-8")
    req = request.Request(  # noqa: S310
        url,
        data=encoded,
        headers={"Content-Type": "application/json", **(headers or {})},
        method="POST",
    )
    with request.urlopen(req) as response:  # noqa: S310
        return response.status, json.loads(response.read().decode("utf-8"))


def _lower_headers(headers: dict[str, str]) -> dict[str, str]:
    return {key.lower(): value for key, value in headers.items()}


def test_runtime_like_flow_with_builders_and_assertions(mock_core):
    headers = build_runtime_headers(container_id="runtime-123", internal_token="secret-token")
    config = build_config_payload(
        config_id="sensor-1",
        extra={"host": "127.0.0.1"},
    )

    telemetry_status, telemetry_body = _post(
        f"{mock_core.base_url}{TELEMETRY_PATH}",
        {
            "device_id": config["device_id"],
            "config_id": config["config_id"],
            "container_id": config["container_id"],
            "temperature_c": 21.4,
        },
        headers=headers,
    )
    event_status, event_body = _post(
        f"{mock_core.base_url}{EVENT_PATH}",
        {
            "event_type": "device.configured",
            "device_id": config["device_id"],
            "config_id": config["config_id"],
            "container_id": config["container_id"],
            "integration_id": config["integration_id"],
        },
        headers=headers,
    )

    assert telemetry_status == 200
    assert telemetry_body["ok"] is True
    assert event_status == 200
    assert event_body["ok"] is True

    telemetry_request = assert_telemetry_sent(mock_core, device_id="sensor-1")
    event_request = assert_event_sent(
        mock_core,
        device_id="sensor-1",
        config_id="sensor-1",
        event_type="device.configured",
    )

    telemetry_headers = _lower_headers(telemetry_request.headers)
    event_headers = _lower_headers(event_request.headers)

    assert telemetry_headers["x-container-id"] == "runtime-123"
    assert telemetry_headers["x-piphi-integration-token"] == "secret-token"
    assert event_headers["x-container-id"] == "runtime-123"
