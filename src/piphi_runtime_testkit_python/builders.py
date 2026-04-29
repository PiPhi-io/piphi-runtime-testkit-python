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
    deleted_config_ids: list[str] | None = None,
    config_hash: str | None = None,
    schema_version: int = 1,
    updated_at: str | None = None,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a snapshot payload for `/config/sync` style tests."""

    payload: dict[str, Any] = {
        "schema_version": schema_version,
        "container_id": container_id,
        "integration_id": integration_id,
        "generation": generation,
        "configs": configs or [],
        "deleted_config_ids": deleted_config_ids or [],
    }
    if config_hash is not None:
        payload["config_hash"] = config_hash
    if updated_at is not None:
        payload["updated_at"] = updated_at
    if extra:
        payload.update(extra)
    return payload


def build_core_config_row(
    *,
    config_data: dict[str, Any] | None = None,
    config_id: str = "config-1",
    container_id: str = "test-container",
    integration_id: str = "test-integration",
    generation: int = 1,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Build a Core database-shaped config row for startup rehydrate tests."""

    payload = build_config_payload(
        config_id=config_id,
        container_id=container_id,
        integration_id=integration_id,
        extra=config_data,
    )
    row: dict[str, Any] = {
        "id": config_id,
        "container_id": container_id,
        "integration_id": integration_id,
        "generation": generation,
        "config_data": payload,
    }
    if extra:
        row.update(extra)
    return row
