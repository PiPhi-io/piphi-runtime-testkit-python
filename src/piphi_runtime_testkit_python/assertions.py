from __future__ import annotations

from typing import Any

from .mock_core import CapturedRequest, MockCoreServer


def _find_request(
    requests: list[CapturedRequest],
    *,
    device_id: str | None = None,
    config_id: str | None = None,
    event_type: str | None = None,
) -> CapturedRequest | None:
    for request in requests:
        body = request.json_body
        if body is None:
            continue
        body_event_type = body.get("event_type") if isinstance(body, dict) else None
        if body_event_type is None and isinstance(body, dict):
            body_event_type = body.get("type")
        if device_id is not None:
            if isinstance(body, dict) and body.get("device_id") != device_id:
                continue
        if config_id is not None:
            if isinstance(body, dict) and body.get("config_id") != config_id:
                continue
        if event_type is not None:
            if body_event_type != event_type:
                continue
        return request
    return None


def assert_telemetry_sent(
    mock_core: MockCoreServer,
    *,
    device_id: str | None = None,
) -> CapturedRequest:
    """Assert that at least one telemetry request was captured."""

    if not mock_core.telemetry_requests:
        raise AssertionError("Expected telemetry to be sent to mock Core, but no telemetry requests were captured.")

    if device_id is None:
        return mock_core.telemetry_requests[-1]

    request = _find_request(mock_core.telemetry_requests, device_id=device_id)
    if request is None:
        raise AssertionError(f"Expected telemetry for device_id={device_id!r}, but captured device_ids were {mock_core.captured_telemetry_device_ids()!r}.")
    return request


def assert_event_sent(
    mock_core: MockCoreServer,
    *,
    device_id: str | None = None,
    config_id: str | None = None,
    event_type: str | None = None,
) -> CapturedRequest:
    """Assert that at least one event request was captured."""

    if not mock_core.event_requests:
        raise AssertionError("Expected an event to be sent to mock Core, but no event requests were captured.")

    if device_id is None and config_id is None and event_type is None:
        return mock_core.event_requests[-1]

    request = _find_request(
        mock_core.event_requests,
        device_id=device_id,
        config_id=config_id,
        event_type=event_type,
    )
    if request is None:
        raise AssertionError(
            "Expected event matching filters, but none were captured. "
            f"device_id={device_id!r} config_id={config_id!r} event_type={event_type!r}"
        )
    return request
