from __future__ import annotations

import pytest

from piphi_runtime_testkit_python.assertions import assert_event_sent, assert_telemetry_sent
from piphi_runtime_testkit_python.mock_core import CapturedRequest, MockCoreServer


def make_request(path: str, json_body: dict) -> CapturedRequest:
    return CapturedRequest(
        method="POST",
        path=path,
        headers={},
        body=b"",
        json_body=json_body,
    )


def test_assert_telemetry_sent_returns_matching_request():
    mock_core = MockCoreServer()
    try:
        mock_core.telemetry_requests.append(make_request("/api/v2/integrations/telemetry", {"device_id": "plug-1"}))

        request = assert_telemetry_sent(mock_core, device_id="plug-1")

        assert request.json_body["device_id"] == "plug-1"
    finally:
        mock_core.shutdown()


def test_assert_event_sent_returns_matching_request():
    mock_core = MockCoreServer()
    try:
        mock_core.event_requests.append(
            make_request("/api/v2/events/ingest", {"event_type": "device.configured", "config_id": "config-1"})
        )

        request = assert_event_sent(mock_core, config_id="config-1", event_type="device.configured")

        assert request.json_body["config_id"] == "config-1"
    finally:
        mock_core.shutdown()


def test_assert_telemetry_sent_failure_message_lists_device_ids():
    mock_core = MockCoreServer()
    try:
        mock_core.telemetry_requests.append(make_request("/api/v2/integrations/telemetry", {"device_id": "plug-1"}))

        with pytest.raises(AssertionError) as excinfo:
            assert_telemetry_sent(mock_core, device_id="plug-2")

        assert "plug-2" in str(excinfo.value)
        assert "plug-1" in str(excinfo.value)
    finally:
        mock_core.shutdown()


def test_assert_event_sent_failure_message_includes_filters():
    mock_core = MockCoreServer()
    try:
        mock_core.event_requests.append(
            make_request("/api/v2/events/ingest", {"event_type": "device.configured", "config_id": "config-1"})
        )

        with pytest.raises(AssertionError) as excinfo:
            assert_event_sent(mock_core, config_id="config-2", event_type="device.removed")

        assert "config-2" in str(excinfo.value)
        assert "device.removed" in str(excinfo.value)
    finally:
        mock_core.shutdown()


def test_mock_core_convenience_assert_methods_delegate():
    mock_core = MockCoreServer()
    try:
        mock_core.telemetry_requests.append(make_request("/api/v2/integrations/telemetry", {"device_id": "plug-1"}))
        mock_core.event_requests.append(
            make_request("/api/v2/events/ingest", {"event_type": "device.configured", "config_id": "config-1"})
        )

        telemetry_request = mock_core.assert_telemetry_sent(device_id="plug-1")
        event_request = mock_core.assert_event_sent(config_id="config-1", event_type="device.configured")

        assert telemetry_request.json_body["device_id"] == "plug-1"
        assert event_request.json_body["config_id"] == "config-1"
    finally:
        mock_core.shutdown()


def test_assert_telemetry_sent_without_requests_fails_cleanly():
    mock_core = MockCoreServer()
    try:
        with pytest.raises(AssertionError) as excinfo:
            assert_telemetry_sent(mock_core)

        assert "no telemetry requests were captured" in str(excinfo.value)
    finally:
        mock_core.shutdown()


def test_assert_event_sent_without_requests_fails_cleanly():
    mock_core = MockCoreServer()
    try:
        with pytest.raises(AssertionError) as excinfo:
            assert_event_sent(mock_core)

        assert "no event requests were captured" in str(excinfo.value)
    finally:
        mock_core.shutdown()
