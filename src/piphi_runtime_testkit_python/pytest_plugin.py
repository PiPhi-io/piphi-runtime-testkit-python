from __future__ import annotations

from collections.abc import Callable
from typing import Any

import pytest

from .builders import build_config_payload, build_config_snapshot, build_runtime_headers
from .mock_core import MockCoreServer


@pytest.fixture
def mock_core() -> MockCoreServer:
    """Run a small local mock Core server and capture outbound requests."""

    server = MockCoreServer()
    try:
        yield server
    finally:
        server.shutdown()


@pytest.fixture
def runtime_headers() -> Callable[..., dict[str, str]]:
    """Build standard PiPhi runtime auth headers."""

    return build_runtime_headers


@pytest.fixture
def config_payload() -> Callable[..., dict[str, Any]]:
    """Build a single config payload for `/config` tests."""

    return build_config_payload


@pytest.fixture
def config_snapshot() -> Callable[..., dict[str, Any]]:
    """Build a snapshot payload for `/config/sync` tests."""

    return build_config_snapshot
