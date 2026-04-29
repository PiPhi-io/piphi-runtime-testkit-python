from __future__ import annotations

from dataclasses import dataclass
import json
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from threading import Thread
from typing import Any


TELEMETRY_PATH = "/api/v2/integrations/telemetry"
EVENT_PATH = "/api/v2/events/ingest"
RUNTIME_CONFIG_FETCH_PATH = "/api/v2/integrations/config/fetch/all/by/container/internal"


@dataclass(slots=True)
class CapturedRequest:
    method: str
    path: str
    headers: dict[str, str]
    body: bytes
    json_body: Any


class _RequestStore:
    def __init__(self) -> None:
        self.telemetry_requests: list[CapturedRequest] = []
        self.event_requests: list[CapturedRequest] = []
        self.runtime_config_requests: list[CapturedRequest] = []
        self.telemetry_status = 200
        self.event_status = 200
        self.runtime_config_status = 200
        self.telemetry_json: Any = {"ok": True}
        self.event_json: Any = {"ok": True}
        self.runtime_config_json: Any = []

    def reset(self) -> None:
        self.telemetry_requests.clear()
        self.event_requests.clear()
        self.runtime_config_requests.clear()
        self.telemetry_status = 200
        self.event_status = 200
        self.runtime_config_status = 200
        self.telemetry_json = {"ok": True}
        self.event_json = {"ok": True}
        self.runtime_config_json = []


class _MockCoreRequestHandler(BaseHTTPRequestHandler):
    store: _RequestStore

    def do_GET(self) -> None:  # noqa: N802
        request = CapturedRequest(
            method="GET",
            path=self.path,
            headers={key: value for key, value in self.headers.items()},
            body=b"",
            json_body=None,
        )

        if self.path.split("?", 1)[0] == RUNTIME_CONFIG_FETCH_PATH:
            self.store.runtime_config_requests.append(request)
            self._send_json(
                self.store.runtime_config_status,
                self.store.runtime_config_json,
            )
            return

        self._send_json(404, {"ok": False, "detail": "unknown path"})

    def do_POST(self) -> None:  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        body = self.rfile.read(content_length)
        try:
            parsed_json = json.loads(body.decode("utf-8")) if body else None
        except json.JSONDecodeError:
            parsed_json = None

        request = CapturedRequest(
            method="POST",
            path=self.path,
            headers={key: value for key, value in self.headers.items()},
            body=body,
            json_body=parsed_json,
        )

        if self.path == TELEMETRY_PATH:
            self.store.telemetry_requests.append(request)
            self._send_json(self.store.telemetry_status, self.store.telemetry_json)
            return

        if self.path == EVENT_PATH:
            self.store.event_requests.append(request)
            self._send_json(self.store.event_status, self.store.event_json)
            return

        self._send_json(404, {"ok": False, "detail": "unknown path"})

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return None

    def _send_json(self, status_code: int, payload: Any) -> None:
        data = json.dumps(payload).encode("utf-8")
        self.send_response(status_code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)


class MockCoreServer:
    """Small local HTTP server that simulates PiPhi Core callbacks."""

    def __init__(self) -> None:
        self._store = _RequestStore()
        self._server = ThreadingHTTPServer(("127.0.0.1", 0), _MockCoreRequestHandler)
        self._server.RequestHandlerClass.store = self._store
        self._thread = Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()

    @property
    def host(self) -> str:
        return "127.0.0.1"

    @property
    def port(self) -> int:
        return int(self._server.server_address[1])

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def telemetry_url(self) -> str:
        return f"{self.base_url}{TELEMETRY_PATH}"

    @property
    def event_url(self) -> str:
        return f"{self.base_url}{EVENT_PATH}"

    @property
    def telemetry_requests(self) -> list[CapturedRequest]:
        return self._store.telemetry_requests

    @property
    def event_requests(self) -> list[CapturedRequest]:
        return self._store.event_requests

    @property
    def runtime_config_requests(self) -> list[CapturedRequest]:
        return self._store.runtime_config_requests

    def set_telemetry_response(self, *, status_code: int = 200, json_body: Any = None) -> None:
        self._store.telemetry_status = status_code
        self._store.telemetry_json = {"ok": status_code < 400} if json_body is None else json_body

    def set_event_response(self, *, status_code: int = 200, json_body: Any = None) -> None:
        self._store.event_status = status_code
        self._store.event_json = {"ok": status_code < 400} if json_body is None else json_body

    def set_runtime_config_response(self, *, status_code: int = 200, json_body: Any = None) -> None:
        self._store.runtime_config_status = status_code
        self._store.runtime_config_json = [] if json_body is None else json_body

    def set_runtime_config_rows(self, rows: list[dict[str, Any]]) -> None:
        self.set_runtime_config_response(status_code=200, json_body=rows)

    def reset(self) -> None:
        self._store.reset()

    def captured_telemetry_device_ids(self) -> list[Any]:
        return [
            request.json_body.get("device_id")
            for request in self.telemetry_requests
            if isinstance(request.json_body, dict)
        ]

    def shutdown(self) -> None:
        self._server.shutdown()
        self._server.server_close()
        self._thread.join(timeout=2)

    def assert_telemetry_sent(self, *, device_id: str | None = None) -> CapturedRequest:
        from .assertions import assert_telemetry_sent

        return assert_telemetry_sent(self, device_id=device_id)

    def assert_event_sent(
        self,
        *,
        device_id: str | None = None,
        config_id: str | None = None,
        event_type: str | None = None,
    ) -> CapturedRequest:
        from .assertions import assert_event_sent

        return assert_event_sent(
            self,
            device_id=device_id,
            config_id=config_id,
            event_type=event_type,
        )
