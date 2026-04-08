from __future__ import annotations

from typing import Any


def build_runtime_headers(
    *,
    container_id: str = "test-container",
    internal_token: str = "test-token",
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]:
    """Build standard PiPhi runtime auth headers for tests."""

    headers = {
        "X-Container-Id": container_id,
        "X-PiPhi-Integration-Token": internal_token,
    }
    if extra_headers:
        headers.update(extra_headers)
    return headers


def build_config_payload(
    *,
    config_id: str = "config-1",
    device_id: str | None = None,
    container_id: str = "test-container",
    integration_id: str = "test-integration",
    include_core_config_id: bool = True,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a single config payload for `/config` tests."""

    payload: dict[str, Any] = {
        "id": config_id,
        "device_id": device_id or config_id,
        "container_id": container_id,
        "integration_id": integration_id,
    }
    if include_core_config_id:
        payload["config_id"] = config_id
    if extra:
        payload.update(extra)
    return payload


def build_config_snapshot(
    *,
    configs: list[dict[str, Any]] | None = None,
    container_id: str = "test-container",
    integration_id: str = "test-integration",
    generation: int = 1,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a snapshot payload for `/config/sync` style tests."""

    payload: dict[str, Any] = {
        "container_id": container_id,
        "integration_id": integration_id,
        "generation": generation,
        "configs": configs or [],
    }
    if extra:
        payload.update(extra)
    return payload
