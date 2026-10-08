"""Pytest-first helpers for testing PiPhi runtime integrations."""

from .assertions import (
    assert_entities_response,
    assert_event_sent,
    assert_state_refresh_response,
    assert_telemetry_sent,
)
from .builders import (
    build_config_payload,
    build_config_snapshot,
    build_core_config_row,
    build_runtime_headers,
)
from .behavior_contract import (
    BehaviorTelemetryIssue,
    assert_behavior_conditions_match_telemetry,
    find_behavior_telemetry_issues,
)
from .mock_core import CapturedRequest, MockCoreServer, RUNTIME_CONFIG_FETCH_PATH

__all__ = [
    "CapturedRequest",
    "BehaviorTelemetryIssue",
    "MockCoreServer",
    "RUNTIME_CONFIG_FETCH_PATH",
    "assert_entities_response",
    "assert_behavior_conditions_match_telemetry",
    "assert_event_sent",
    "assert_state_refresh_response",
    "assert_telemetry_sent",
    "build_config_payload",
    "build_config_snapshot",
    "build_core_config_row",
    "build_runtime_headers",
    "find_behavior_telemetry_issues",
]
