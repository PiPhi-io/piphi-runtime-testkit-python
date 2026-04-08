from __future__ import annotations

from urllib import request

from piphi_runtime_testkit_python.mock_core import TELEMETRY_PATH


def test_runtime_headers_fixture(runtime_headers):
    headers = runtime_headers(container_id="runtime-123", internal_token="secret-token")

    assert headers["X-Container-Id"] == "runtime-123"
    assert headers["X-PiPhi-Integration-Token"] == "secret-token"


def test_config_payload_fixture(config_payload):
    payload = config_payload(config_id="config-1", extra={"host": "127.0.0.1"})

    assert payload["config_id"] == "config-1"
    assert payload["host"] == "127.0.0.1"


def test_config_snapshot_fixture(config_snapshot):
    snapshot = config_snapshot(configs=[{"id": "config-1"}], generation=5)

    assert snapshot["generation"] == 5
    assert snapshot["configs"] == [{"id": "config-1"}]


def test_mock_core_fixture_captures_requests(mock_core):
    req = request.Request(  # noqa: S310
        f"{mock_core.base_url}{TELEMETRY_PATH}",
        data=b'{"device_id":"plug-1"}',
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with request.urlopen(req) as response:  # noqa: S310
        assert response.status == 200

    captured = mock_core.assert_telemetry_sent(device_id="plug-1")
    assert captured.json_body["device_id"] == "plug-1"
