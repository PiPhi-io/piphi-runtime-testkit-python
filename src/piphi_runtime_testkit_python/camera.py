"""Camera-media v1 builders and conformance assertions."""

from __future__ import annotations

from typing import Any
from urllib.parse import urlsplit


CAMERA_MEDIA_CONTRACT_VERSION = "camera.media.v1"
PUBLIC_CAMERA_AUDIENCES = {"browser-core"}
CAMERA_SECRET_FIELDS = {
    "authorization",
    "password",
    "source_url",
    "token",
    "username",
}


def build_camera_source(
    *,
    camera_id: str = "camera-1",
    source_url: str = "rtsp://camera.local/live",
    preferred_transport: str = "tcp",
    connect_timeout_seconds: int = 10,
) -> dict[str, Any]:
    """Build an internal camera source descriptor for runtime/sidecar tests."""

    parsed = urlsplit(source_url)
    return {
        "contract_version": CAMERA_MEDIA_CONTRACT_VERSION,
        "message_type": "camera.source",
        "audience": "core-sidecar",
        "camera_id": camera_id,
        "source_url": source_url,
        "source_protocol": parsed.scheme.lower(),
        "preferred_transport": preferred_transport,
        "connect_timeout_seconds": connect_timeout_seconds,
    }


def build_camera_session_offer(
    *,
    sdp: str = "v=0\r\na=recvonly\r\n",
    include_audio: bool = False,
) -> dict[str, Any]:
    """Build a browser-to-Core WebRTC offer."""

    return {
        "contract_version": CAMERA_MEDIA_CONTRACT_VERSION,
        "message_type": "camera.session.offer",
        "audience": "browser-core",
        "type": "offer",
        "sdp": sdp,
        "include_audio": include_audio,
    }


def build_camera_sidecar_session_open(
    *,
    source: dict[str, Any] | None = None,
    offer: dict[str, Any] | None = None,
    idle_timeout_seconds: int = 60,
) -> dict[str, Any]:
    """Build the private Core-to-sidecar session request."""

    browser_offer = offer or build_camera_session_offer()
    return {
        "contract_version": CAMERA_MEDIA_CONTRACT_VERSION,
        "message_type": "camera.sidecar.session.open",
        "audience": "core-sidecar",
        "source": source or build_camera_source(),
        "offer": {
            "type": browser_offer["type"],
            "sdp": browser_offer["sdp"],
            "include_audio": bool(browser_offer.get("include_audio", False)),
        },
        "idle_timeout_seconds": idle_timeout_seconds,
    }


def _field_names(value: object) -> set[str]:
    if isinstance(value, dict):
        names = {str(key).lower() for key in value}
        for nested in value.values():
            names.update(_field_names(nested))
        return names
    if isinstance(value, list):
        names: set[str] = set()
        for nested in value:
            names.update(_field_names(nested))
        return names
    return set()


def assert_public_camera_message_redacted(payload: Any) -> dict[str, Any]:
    """Assert that a browser-facing camera message contains no source secrets."""

    if not isinstance(payload, dict):
        raise AssertionError(f"Expected camera message object, received {payload!r}.")
    if payload.get("contract_version") != CAMERA_MEDIA_CONTRACT_VERSION:
        raise AssertionError("Expected camera.media.v1 contract_version.")
    if payload.get("audience") not in PUBLIC_CAMERA_AUDIENCES:
        raise AssertionError("Expected a browser-facing camera message.")
    leaked = _field_names(payload) & CAMERA_SECRET_FIELDS
    if leaked:
        raise AssertionError(f"Browser-facing camera message leaked secret fields: {sorted(leaked)!r}.")
    return payload


def assert_camera_capability(
    entities_payload: Any,
    *,
    capability_id: str = "camera_stream",
) -> dict[str, Any]:
    """Assert that an entities response advertises a usable camera capability."""

    if not isinstance(entities_payload, dict):
        raise AssertionError("Expected /entities payload to be an object.")
    capabilities = entities_payload.get("capabilities")
    if not isinstance(capabilities, dict):
        raise AssertionError("Expected /entities capabilities to be an object.")
    capability = capabilities.get(capability_id)
    if not isinstance(capability, dict) or capability.get("kind") != "camera":
        raise AssertionError(f"Expected {capability_id!r} to be a camera capability.")
    camera = capability.get("camera")
    if not isinstance(camera, dict):
        raise AssertionError(f"Expected {capability_id!r} to declare camera media endpoints.")
    endpoint_names = {
        "gateway_source_endpoint",
        "snapshot_endpoint",
        "stream_endpoint",
        "webrtc_endpoint",
    }
    if not endpoint_names.intersection(camera):
        raise AssertionError(f"Expected {capability_id!r} to declare at least one media endpoint.")
    entities = entities_payload.get("entities")
    if not isinstance(entities, list) or not any(
        isinstance(entity, dict) and capability_id in (entity.get("capabilities") or [])
        for entity in entities
    ):
        raise AssertionError(f"Expected an entity to advertise {capability_id!r}.")
    return capability

