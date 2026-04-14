from __future__ import annotations

from typing import Any

from .mock_core import CapturedRequest, MockCoreServer


def _pick_alias(mapping: dict[str, Any], *names: str) -> Any:
    for name in names:
        if name in mapping:
            return mapping[name]
    return None


def _assert_string_list(value: Any, *, label: str) -> None:
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise AssertionError(f"Expected {label} to be a list[str], but received {value!r}.")


def _assert_optional_string(mapping: dict[str, Any], *, names: tuple[str, ...], label: str) -> None:
    value = _pick_alias(mapping, *names)
    if value is not None and not isinstance(value, str):
        raise AssertionError(f"Expected {label} to be a string when provided, but received {value!r}.")


def _assert_optional_object(mapping: dict[str, Any], *, names: tuple[str, ...], label: str) -> dict[str, Any] | None:
    value = _pick_alias(mapping, *names)
    if value is None:
        return None
    if not isinstance(value, dict):
        raise AssertionError(f"Expected {label} to be an object when provided, but received {value!r}.")
    return value


def _assert_entity_shape(entity: Any, *, index: int) -> dict[str, Any]:
    if not isinstance(entity, dict):
        raise AssertionError(f"Expected entities[{index}] to be an object, but received {entity!r}.")
    if not isinstance(entity.get("id"), str) or not entity["id"]:
        raise AssertionError(f"Expected entities[{index}].id to be a non-empty string, but received {entity.get('id')!r}.")
    if not isinstance(entity.get("name"), str) or not entity["name"]:
        raise AssertionError(
            f"Expected entities[{index}].name to be a non-empty string, but received {entity.get('name')!r}."
        )
    _assert_string_list(entity.get("capabilities"), label=f"entities[{index}].capabilities")
    _assert_optional_string(entity, names=("config_id", "configId"), label=f"entities[{index}].config_id")
    _assert_optional_string(entity, names=("device_id", "deviceId"), label=f"entities[{index}].device_id")
    _assert_optional_string(entity, names=("device_type", "deviceType"), label=f"entities[{index}].device_type")
    _assert_optional_string(entity, names=("device_class", "deviceClass"), label=f"entities[{index}].device_class")
    _assert_optional_string(entity, names=("entity_type", "entityType"), label=f"entities[{index}].entity_type")

    dashboard = _assert_optional_object(entity, names=("dashboard",), label=f"entities[{index}].dashboard")
    if dashboard is not None:
        allowed_widgets = _pick_alias(dashboard, "allowed_widgets", "allowedWidgets")
        if allowed_widgets is not None:
            _assert_string_list(allowed_widgets, label=f"entities[{index}].dashboard.allowed_widgets")
        recommended_widgets = _pick_alias(dashboard, "recommended_widgets", "recommendedWidgets")
        if recommended_widgets is not None:
            _assert_string_list(recommended_widgets, label=f"entities[{index}].dashboard.recommended_widgets")
        _assert_optional_string(
            dashboard,
            names=("default_widget", "defaultWidget"),
            label=f"entities[{index}].dashboard.default_widget",
        )
    return entity


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


def assert_entities_response(payload: Any) -> dict[str, Any]:
    """Assert that a runtime /entities payload matches the PiPhi contract."""

    if not isinstance(payload, dict):
        raise AssertionError(f"Expected /entities payload to be an object, but received {payload!r}.")

    entities = payload.get("entities")
    if not isinstance(entities, list):
        raise AssertionError(f"Expected /entities payload to include an entities list, but received {entities!r}.")

    for index, entity in enumerate(entities):
        _assert_entity_shape(entity, index=index)

    capabilities = payload.get("capabilities")
    if capabilities is not None and not isinstance(capabilities, dict):
        raise AssertionError(f"Expected /entities payload capabilities to be an object, but received {capabilities!r}.")

    commands = payload.get("commands")
    if commands is not None and not isinstance(commands, dict):
        raise AssertionError(f"Expected /entities payload commands to be an object, but received {commands!r}.")

    return payload
