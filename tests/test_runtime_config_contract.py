from __future__ import annotations

import httpx
import pytest

from piphi_runtime_kit_python import (
    RuntimeConfigSnapshot,
    RuntimeContext,
    rehydrate_runtime_configs,
)
from piphi_runtime_testkit_python import (
    build_core_config_row,
)


@pytest.mark.asyncio
async def test_mock_core_supports_sdk_startup_rehydrate_contract(mock_core) -> None:
    mock_core.set_runtime_config_rows(
        [
            build_core_config_row(
                config_id="sensor-1",
                container_id="runtime-123",
                integration_id="test-integration",
                config_data={"device_id": "sensor-1", "host": "10.0.0.42"},
            )
        ]
    )
    runtime = RuntimeContext()
    runtime.auth.update(container_id="runtime-123", internal_token="secret-token")
    applied_snapshots: list[RuntimeConfigSnapshot] = []

    async def apply_snapshot(snapshot: RuntimeConfigSnapshot) -> None:
        applied_snapshots.append(snapshot)

    async with httpx.AsyncClient() as client:
        result = await rehydrate_runtime_configs(
            runtime_context=runtime,
            client=client,
            apply_snapshot=apply_snapshot,
            core_base_url=mock_core.base_url,
        )

    assert result.core_applied is True
    assert result.core_config_count == 1
    assert applied_snapshots[0].container_id == "runtime-123"
    assert applied_snapshots[0].configs[0].id == "sensor-1"
    assert applied_snapshots[0].configs[0].device_id == "sensor-1"

    captured_request = mock_core.runtime_config_requests[0]
    captured_headers = {
        key.lower(): value
        for key, value in captured_request.headers.items()
    }
    assert "container_id=runtime-123" in captured_request.path
    assert captured_headers["x-container-id"] == "runtime-123"
    assert captured_headers["x-piphi-integration-token"] == "secret-token"
