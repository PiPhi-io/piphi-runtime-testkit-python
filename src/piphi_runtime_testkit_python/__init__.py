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
from .camera import (
    CAMERA_MEDIA_CONTRACT_VERSION,
    assert_camera_capability,
    assert_public_camera_message_redacted,
    build_camera_session_offer,
    build_camera_sidecar_session_open,
    build_camera_source,
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
    "CAMERA_MEDIA_CONTRACT_VERSION",
    "MockCoreServer",
    "RUNTIME_CONFIG_FETCH_PATH",
    "assert_entities_response",
    "assert_camera_capability",
    "assert_behavior_conditions_match_telemetry",
    "assert_event_sent",
    "assert_state_refresh_response",
    "assert_telemetry_sent",
    "assert_public_camera_message_redacted",
    "build_camera_session_offer",
    "build_camera_sidecar_session_open",
    "build_camera_source",
    "build_config_payload",
    "build_config_snapshot",
    "build_core_config_row",
    "build_runtime_headers",
    "find_behavior_telemetry_issues",
]
