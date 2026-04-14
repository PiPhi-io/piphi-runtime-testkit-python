from __future__ import annotations

import time
from typing import Any

from fastapi import FastAPI, Request
from fastapi.testclient import TestClient

from piphi_runtime_kit_python import (
    IntegrationEventIngestResponse,
    RuntimeConfig,
    build_config_apply_response,
    build_event_ingest_response,
    build_local_event_record,
    create_runtime_starter,
    schedule_event_delivery,
    schedule_telemetry_delivery,
)
from piphi_runtime_kit_python.fastapi import sync_runtime_auth_from_fastapi_payload
from piphi_runtime_testkit_python import assert_entities_response


class DemoConfig(RuntimeConfig):
    host: str


def create_demo_app(*, core_base_url: str) -> tuple[FastAPI, Any]:
    starter = create_runtime_starter(
        integration_id="demo-runtime",
        integration_name="Demo Runtime",
        version="0.1.0",
        core_base_url=core_base_url,
    )

    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, Any]:
        return starter.health_response()

    @app.post("/config")
    async def config(payload: DemoConfig, request: Request):
        sync_runtime_auth_from_fastapi_payload(starter.runtime, request, payload)
        starter.registry.set(
            payload.id,
            {
                "config_id": payload.config_id or payload.id,
                "device_id": payload.device_id or payload.id,
                "container_id": payload.container_id,
                "integration_id": payload.integration_id or "demo-runtime",
                "host": payload.host,
            },
        )
        starter.registry.update_state(
            payload.id,
            {
                "connected": True,
                "host": payload.host,
            },
        )
        return build_config_apply_response(
            config_id=payload.config_id or payload.id,
            container_id=payload.container_id,
        )

    @app.post("/telemetry/example")
    async def telemetry_example():
        entry = starter.registry.primary_entry()
        if entry is None:
            return {"status": "skipped", "reason": "no configured device"}

        schedule_telemetry_delivery(
            process_state=starter.runtime.process_state,
            telemetry_client=starter.telemetry_client,
            auth_context=starter.runtime.auth,
            device_id=str(entry["device_id"]),
            container_id=entry.get("container_id"),
            metrics={"temperature_c": 21.4},
            units={"temperature_c": "C"},
        )
        return {"status": "queued"}

    @app.post("/events/example", response_model=IntegrationEventIngestResponse)
    async def event_example():
        entry = starter.registry.primary_entry()
        if entry is None:
            raise RuntimeError("expected config to exist before creating event")

        local_event = build_local_event_record(
            event_type="device.configured",
            device=entry,
            payload={"host": entry["host"]},
            source="demo-runtime",
            severity="info",
        )
        starter.registry.append_event(local_event)
        schedule_event_delivery(
            process_state=starter.runtime.process_state,
            event_client=starter.event_client,
            auth_context=starter.runtime.auth,
            event_type="device.configured",
            device=entry,
            payload={"host": entry["host"]},
            source="demo-runtime",
        )
        return build_event_ingest_response(local_event)

    @app.get("/state")
    async def state() -> dict[str, Any]:
        return {
            "entries": starter.registry.entries,
            "state_snapshots": starter.registry.state_snapshots,
        }

    @app.get("/entities")
    async def entities():
        entry = starter.registry.primary_entry()
        if entry is None:
            return {"entities": [], "capabilities": {}, "commands": {}}

        return {
            "entities": [
                {
                    "id": f"sensor.{entry['device_id']}",
                    "name": f"Demo Sensor {entry['device_id']}",
                    "capabilities": ["temperature", "humidity"],
                    "config_id": str(entry["config_id"]),
                    "device_id": str(entry["device_id"]),
                    "device_type": "sensor",
                    "device_class": "environment",
                    "entity_type": "sensor",
                    "dashboard": {
                        "allowed_widgets": ["sensor-card", "line-chart"],
                        "default_widget": "sensor-card",
                        "recommended_widgets": ["sensor-card"],
                    },
                }
            ],
            "capabilities": {
                "temperature": {"label": "Temperature"},
                "humidity": {"label": "Humidity"},
            },
            "commands": {},
        }

    return app, starter


def wait_for(condition, *, timeout: float = 2.0) -> None:
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if condition():
            return
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for background delivery to complete.")


def test_fastapi_runtime_example_round_trip(mock_core, runtime_headers, config_payload):
    app, starter = create_demo_app(core_base_url=mock_core.base_url)
    with TestClient(app) as client:
        payload = config_payload(
            config_id="sensor-1",
            container_id="runtime-123",
            extra={"host": "127.0.0.1"},
        )
        headers = runtime_headers(container_id="runtime-123", internal_token="secret-token")

        config_response = client.post("/config", json=payload, headers=headers)
        assert config_response.status_code == 200
        assert config_response.json()["config_id"] == "sensor-1"

        telemetry_response = client.post("/telemetry/example")
        assert telemetry_response.status_code == 200
        assert telemetry_response.json()["status"] == "queued"

        event_response = client.post("/events/example")
        assert event_response.status_code == 200
        assert event_response.json()["event"]["event_type"] == "device.configured"

        state_response = client.get("/state")
        assert state_response.status_code == 200
        state_json = state_response.json()
        assert "sensor-1" in state_json["entries"]
        assert "sensor-1" in state_json["state_snapshots"]

        wait_for(lambda: len(mock_core.telemetry_requests) >= 1)
        wait_for(lambda: len(mock_core.event_requests) >= 1)

        telemetry_request = mock_core.assert_telemetry_sent(device_id="sensor-1")
        event_request = mock_core.assert_event_sent(
            device_id="sensor-1",
            config_id="sensor-1",
            event_type="device.configured",
        )

        telemetry_headers = {key.lower(): value for key, value in telemetry_request.headers.items()}
        event_headers = {key.lower(): value for key, value in event_request.headers.items()}

        assert telemetry_headers["x-container-id"] == "runtime-123"
        assert telemetry_headers["x-piphi-integration-token"] == "secret-token"
        assert event_headers["x-container-id"] == "runtime-123"
        assert event_headers["x-piphi-integration-token"] == "secret-token"
        assert telemetry_request.json_body["device_id"] == "sensor-1"
        assert (event_request.json_body.get("event_type") or event_request.json_body.get("type")) == "device.configured"


def test_fastapi_runtime_example_entities_endpoint(mock_core, runtime_headers, config_payload):
    app, _starter = create_demo_app(core_base_url=mock_core.base_url)
    with TestClient(app) as client:
        payload = config_payload(
            config_id="sensor-entities-1",
            container_id="runtime-entities-123",
            extra={"host": "127.0.0.10"},
        )
        headers = runtime_headers(container_id="runtime-entities-123", internal_token="secret-token")

        config_response = client.post("/config", json=payload, headers=headers)
        assert config_response.status_code == 200

        entities_response = client.get("/entities")
        assert entities_response.status_code == 200

        entities_json = entities_response.json()
        assert_entities_response(entities_json)
        assert entities_json["entities"][0]["config_id"] == "sensor-entities-1"
        assert entities_json["entities"][0]["device_type"] == "sensor"
        assert entities_json["entities"][0]["dashboard"]["default_widget"] == "sensor-card"
