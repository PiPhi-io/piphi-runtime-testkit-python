from __future__ import annotations

import pytest

from piphi_runtime_testkit_python import (
    assert_camera_capability,
    assert_public_camera_message_redacted,
    build_camera_session_offer,
    build_camera_sidecar_session_open,
    build_camera_source,
)


def test_camera_builders_keep_private_source_out_of_browser_offer() -> None:
    source = build_camera_source(source_url="rtsps://user:secret@camera.local/live")
    offer = build_camera_session_offer(include_audio=True)
    sidecar_request = build_camera_sidecar_session_open(source=source, offer=offer)

    assert source["audience"] == "core-sidecar"
    assert source["source_protocol"] == "rtsps"
    assert "source_url" not in offer
    assert sidecar_request["source"] == source
    assert sidecar_request["offer"]["include_audio"] is True


def test_public_camera_redaction_assertion_rejects_secret_fields() -> None:
    assert_public_camera_message_redacted({
        "contract_version": "camera.media.v1",
        "message_type": "camera.session.opened",
        "audience": "browser-core",
        "session_id": "opaque",
        "type": "answer",
        "sdp": "v=0",
    })

    with pytest.raises(AssertionError, match="source_url"):
        assert_public_camera_message_redacted({
            "contract_version": "camera.media.v1",
            "message_type": "camera.session.opened",
            "audience": "browser-core",
            "source_url": "rtsp://user:secret@camera.local/live",
        })


def test_camera_capability_assertion_requires_endpoint_and_entity() -> None:
    payload = {
        "capabilities": {
            "camera_stream": {
                "kind": "camera",
                "camera": {"gateway_source_endpoint": "/v1/cameras/{config_id}/source"},
            }
        },
        "entities": [
            {
                "id": "front-door",
                "name": "Front door",
                "capabilities": ["camera_stream"],
            }
        ],
    }

    capability = assert_camera_capability(payload)
    assert capability["kind"] == "camera"
