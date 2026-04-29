from __future__ import annotations

import json
from urllib import error
from urllib import request

from piphi_runtime_testkit_python import build_core_config_row, build_runtime_headers
from piphi_runtime_testkit_python.mock_core import (
    EVENT_PATH,
    RUNTIME_CONFIG_FETCH_PATH,
    TELEMETRY_PATH,
    MockCoreServer,
)


def _post_json(url: str, payload: dict) -> tuple[int, dict]:
    encoded = json.dumps(payload).encode("utf-8")
    req = request.Request(
        url,
        data=encoded,
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req) as response:  # noqa: S310
        return response.status, json.loads(response.read().decode("utf-8"))


def _get_json(url: str, headers: dict[str, str] | None = None) -> tuple[int, list]:
    req = request.Request(
        url,
        headers=headers or {},
        method="GET",
    )
    with request.urlopen(req) as response:  # noqa: S310
        return response.status, json.loads(response.read().decode("utf-8"))


def test_mock_core_captures_telemetry_and_events():
    mock_core = MockCoreServer()
    try:
        telemetry_status, telemetry_body = _post_json(
            f"{mock_core.base_url}{TELEMETRY_PATH}",
            {"device_id": "plug-1", "metric": "power"},
        )
        event_status, event_body = _post_json(
            f"{mock_core.base_url}{EVENT_PATH}",
            {"event_type": "device.configured", "config_id": "config-1"},
        )

        assert telemetry_status == 200
        assert telemetry_body["ok"] is True
        assert event_status == 200
        assert event_body["ok"] is True
        assert len(mock_core.telemetry_requests) == 1
        assert len(mock_core.event_requests) == 1
        assert mock_core.telemetry_requests[0].json_body["device_id"] == "plug-1"
        assert mock_core.event_requests[0].json_body["event_type"] == "device.configured"
    finally:
        mock_core.shutdown()


def test_mock_core_custom_responses():
    mock_core = MockCoreServer()
    try:
        mock_core.set_telemetry_response(status_code=500, json_body={"ok": False, "detail": "boom"})
        mock_core.set_event_response(status_code=404, json_body={"ok": False, "detail": "missing"})

        telemetry_req = request.Request(  # noqa: S310
            f"{mock_core.base_url}{TELEMETRY_PATH}",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        event_req = request.Request(  # noqa: S310
            f"{mock_core.base_url}{EVENT_PATH}",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            request.urlopen(telemetry_req)  # noqa: S310
        except Exception:
            pass

        try:
            request.urlopen(event_req)  # noqa: S310
        except Exception:
            pass

        assert mock_core.telemetry_requests
        assert mock_core.event_requests
    finally:
        mock_core.shutdown()


def test_mock_core_reset_clears_requests_and_restores_defaults():
    mock_core = MockCoreServer()
    try:
        _post_json(
            f"{mock_core.base_url}{TELEMETRY_PATH}",
            {"device_id": "plug-1", "metric": "power"},
        )
        _post_json(
            f"{mock_core.base_url}{EVENT_PATH}",
            {"event_type": "device.configured", "config_id": "config-1"},
        )
        mock_core.set_telemetry_response(status_code=500, json_body={"ok": False})
        mock_core.set_event_response(status_code=404, json_body={"ok": False})

        mock_core.reset()

        assert mock_core.telemetry_requests == []
        assert mock_core.event_requests == []
        telemetry_status, telemetry_body = _post_json(
            f"{mock_core.base_url}{TELEMETRY_PATH}",
            {"device_id": "plug-2"},
        )
        event_status, event_body = _post_json(
            f"{mock_core.base_url}{EVENT_PATH}",
            {"event_type": "device.removed", "config_id": "config-2"},
        )
        assert telemetry_status == 200
        assert telemetry_body["ok"] is True
        assert event_status == 200
        assert event_body["ok"] is True
    finally:
        mock_core.shutdown()


def test_mock_core_captured_telemetry_device_ids():
    mock_core = MockCoreServer()
    try:
        _post_json(
            f"{mock_core.base_url}{TELEMETRY_PATH}",
            {"device_id": "plug-1"},
        )
        _post_json(
            f"{mock_core.base_url}{TELEMETRY_PATH}",
            {"device_id": "plug-2"},
        )

        assert mock_core.captured_telemetry_device_ids() == ["plug-1", "plug-2"]
    finally:
        mock_core.shutdown()


def test_mock_core_unknown_path_returns_404_and_is_not_captured():
    mock_core = MockCoreServer()
    try:
        req = request.Request(  # noqa: S310
            f"{mock_core.base_url}/api/v2/unknown",
            data=b"{}",
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            request.urlopen(req)  # noqa: S310
        except error.HTTPError as exc:
            assert exc.code == 404
            assert json.loads(exc.read().decode("utf-8"))["detail"] == "unknown path"
        else:
            raise AssertionError("Expected 404 for unknown path")

        assert mock_core.telemetry_requests == []
        assert mock_core.event_requests == []
    finally:
        mock_core.shutdown()


def test_mock_core_invalid_json_is_captured_with_none_json_body():
    mock_core = MockCoreServer()
    try:
        req = request.Request(  # noqa: S310
            f"{mock_core.base_url}{TELEMETRY_PATH}",
            data=b"{invalid-json",
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with request.urlopen(req) as response:  # noqa: S310
            assert response.status == 200

        assert len(mock_core.telemetry_requests) == 1
        assert mock_core.telemetry_requests[0].json_body is None
        assert mock_core.telemetry_requests[0].body == b"{invalid-json"
    finally:
        mock_core.shutdown()


def test_mock_core_serves_runtime_config_rows_and_captures_auth_headers():
    mock_core = MockCoreServer()
    try:
        mock_core.set_runtime_config_rows(
            [
                build_core_config_row(
                    config_id="config-1",
                    container_id="runtime-123",
                    integration_id="test-integration",
                    config_data={"host": "10.0.0.10"},
                )
            ]
        )
        headers = build_runtime_headers(
            container_id="runtime-123",
            internal_token="secret-token",
        )

        status, rows = _get_json(
            f"{mock_core.base_url}{RUNTIME_CONFIG_FETCH_PATH}?container_id=runtime-123",
            headers=headers,
        )

        assert status == 200
        assert rows[0]["config_data"]["id"] == "config-1"
        assert rows[0]["config_data"]["host"] == "10.0.0.10"
        assert len(mock_core.runtime_config_requests) == 1
        captured_headers = {
            key.lower(): value
            for key, value in mock_core.runtime_config_requests[0].headers.items()
        }
        assert captured_headers["x-container-id"] == "runtime-123"
        assert captured_headers["x-piphi-integration-token"] == "secret-token"
    finally:
        mock_core.shutdown()
