from piphi_runtime_testkit_python.builders import (
    build_config_payload,
    build_config_snapshot,
    build_runtime_headers,
)


def test_build_runtime_headers_defaults():
    headers = build_runtime_headers()

    assert headers["X-Container-Id"] == "test-container"
    assert headers["X-PiPhi-Integration-Token"] == "test-token"


def test_build_config_payload_defaults():
    payload = build_config_payload(extra={"host": "127.0.0.1"})

    assert payload["id"] == "config-1"
    assert payload["device_id"] == "config-1"
    assert payload["config_id"] == "config-1"
    assert payload["host"] == "127.0.0.1"


def test_build_config_snapshot_defaults():
    snapshot = build_config_snapshot(configs=[{"id": "config-1"}], generation=7)

    assert snapshot["generation"] == 7
    assert snapshot["configs"] == [{"id": "config-1"}]


def test_build_runtime_headers_with_overrides():
    headers = build_runtime_headers(
        container_id="runtime-123",
        internal_token="secret-token",
        extra_headers={"X-Debug": "yes"},
    )

    assert headers["X-Container-Id"] == "runtime-123"
    assert headers["X-PiPhi-Integration-Token"] == "secret-token"
    assert headers["X-Debug"] == "yes"


def test_build_config_payload_without_core_config_id():
    payload = build_config_payload(
        config_id="config-2",
        include_core_config_id=False,
        extra={"host": "192.168.1.20"},
    )

    assert payload["id"] == "config-2"
    assert payload["device_id"] == "config-2"
    assert "config_id" not in payload
    assert payload["host"] == "192.168.1.20"


def test_build_config_snapshot_with_extra_fields():
    snapshot = build_config_snapshot(
        configs=[{"id": "config-3"}],
        generation=9,
        extra={"source": "test-suite"},
    )

    assert snapshot["generation"] == 9
    assert snapshot["source"] == "test-suite"


def test_build_config_payload_with_device_override():
    payload = build_config_payload(
        config_id="config-4",
        device_id="device-4",
        extra={"alias": "Office Sensor"},
    )

    assert payload["id"] == "config-4"
    assert payload["device_id"] == "device-4"
    assert payload["config_id"] == "config-4"
    assert payload["alias"] == "Office Sensor"


def test_build_config_snapshot_defaults_to_empty_configs():
    snapshot = build_config_snapshot()

    assert snapshot["configs"] == []
    assert snapshot["generation"] == 1
