# piphi-runtime-testkit-python

Pytest-first helpers for testing PiPhi runtime integrations.

This package exists to make integration tests easier to write, easier to read,
and easier to debug. It is designed for developers who are building PiPhi
runtimes and want a simple way to simulate PiPhi Core, build realistic request
payloads, and assert that telemetry and events were sent correctly.

It is intentionally small. The goal is not to hide pytest or hide your runtime.
The goal is to give you a few strong building blocks so your tests feel
predictable instead of repetitive.

> Safety note: the IDs and tokens in this README are fake test values. Use placeholders like `test-token` in tests, and never paste real production credentials into fixtures, screenshots, or public docs.

## Start Here

If you are brand new, read these sections in order:

1. [What This Package Helps With](#what-this-package-helps-with)
2. [Plain-Language Concepts](#plain-language-concepts)
3. [Install](#install)
4. [Quick Start](#quick-start)
5. [Pytest Fixtures](#pytest-fixtures)
6. [FastAPI End-to-End Example](#fastapi-end-to-end-example)

If you already know the basics and just need the API:

- [Pytest Fixtures](#pytest-fixtures)
- [Builder Functions](#builder-functions)
- [Assertion Helpers](#assertion-helpers)
- [MockCoreServer API](#mockcoreserver-api)

## What This Package Helps With

When you test a PiPhi runtime, you usually need to answer questions like:

- How do I generate realistic config payloads without rewriting dictionaries in every test?
- How do I simulate PiPhi Core receiving telemetry and events?
- How do I assert what my runtime sent to Core?
- How do I keep the test readable for another developer?

This package gives you helpers for exactly those jobs.

It includes:

- a local mock Core server that captures outbound HTTP requests
- builder functions for runtime headers, `/config` payloads, and `/config/sync` snapshots
- readable assertion helpers for telemetry and event delivery
- a pytest plugin so the fixtures are available automatically

It does not try to replace:

- pytest
- FastAPI test clients
- your runtime SDK
- your vendor-specific integration logic

## Plain-Language Concepts

### Mock Core

A "mock Core" is a tiny fake PiPhi Core server that your runtime can talk to in
tests.

Instead of sending telemetry to a real Core instance, your runtime sends it to
the mock server. The mock server captures the request so your test can inspect
it.

Think of it like a mailbox that keeps every letter your runtime mailed, so your
test can open the mailbox and check what was sent.

Example:

```python
def test_runtime_sent_telemetry(mock_core):
    # Your runtime posts to mock_core.base_url instead of a real Core server.
    assert mock_core.base_url.startswith("http://127.0.0.1:")
```

### Runtime Headers

PiPhi runtimes use headers like `X-Container-Id` and
`X-PiPhi-Integration-Token` to identify themselves when communicating with
Core. In tests, use fake values rather than real runtime credentials.

The `runtime_headers` fixture and `build_runtime_headers(...)` helper build
those headers for you so you do not need to remember the exact names every
time.

Example:

```python
def test_headers(runtime_headers):
    headers = runtime_headers(container_id="runtime-123", internal_token="test-token")

    assert headers["X-Container-Id"] == "runtime-123"
    assert headers["X-PiPhi-Integration-Token"] == "test-token"
```

### Config Payload

A config payload is the JSON body your runtime receives on `/config`.

It usually contains things like:

- `id`
- `config_id`
- `device_id`
- `container_id`
- `integration_id`

The config payload builder gives you a realistic base payload and lets you add
integration-specific fields such as `host`, `username`, `path`, or anything
else your runtime needs.

Example:

```python
def test_config_payload(config_payload):
    payload = config_payload(
        config_id="plug-1",
        extra={"host": "10.0.0.20"},
    )

    assert payload["config_id"] == "plug-1"
    assert payload["device_id"] == "plug-1"
    assert payload["host"] == "10.0.0.20"
```

### Config Snapshot

A config snapshot is the payload your runtime receives on `/config/sync`.

It represents the full current picture of what Core thinks should be configured.

Think of a snapshot like a fresh class attendance sheet. Instead of asking
"who changed?", you get the whole current list and compare it against what you
already have.

Example:

```python
def test_config_snapshot(config_payload, config_snapshot):
    one_device = config_payload(config_id="sensor-1", extra={"host": "10.0.0.5"})
    snapshot = config_snapshot(configs=[one_device], generation=3)

    assert snapshot["generation"] == 3
    assert snapshot["configs"][0]["config_id"] == "sensor-1"
```

### Captured Request

When the mock Core receives telemetry or an event, it stores a `CapturedRequest`
object.

That object includes:

- the HTTP method
- the path
- the headers
- the raw body
- the parsed JSON body, if the request body was valid JSON

This makes debugging much easier because your test can inspect exactly what was
sent.

Example:

```python
request = mock_core.telemetry_requests[-1]
assert request.path == "/api/v2/integrations/telemetry"
assert request.json_body["device_id"] == "sensor-1"
```

### Assertion Helper

An assertion helper is just a small function that checks the captured requests
for you and raises a readable failure message if nothing matched.

Instead of manually looping through requests, you can write:

```python
mock_core.assert_telemetry_sent(device_id="sensor-1")
mock_core.assert_event_sent(config_id="sensor-1", event_type="device.configured")
```

That makes the test much easier to understand at a glance.

## Install

### Local development install

If you are working from sibling repositories locally:

```bash
pdm add -d /path/to/piphi-runtime-testkit-python
```

### What this package depends on

The package itself is intentionally light. Its main runtime dependency is
pytest.

If you want to write full runtime tests for a FastAPI runtime, your integration
project will also usually need:

- `piphi-runtime-kit-python`
- `fastapi`
- `httpx`

Example:

```bash
pdm add -d /path/to/piphi-runtime-testkit-python
pdm add -d /path/to/piphi-runtime-kit-python
pdm add -d fastapi httpx
```

## Quick Start

This is the smallest realistic example:

```python
def test_builders(config_payload, config_snapshot, runtime_headers):
    payload = config_payload(
        config_id="plug-1",
        extra={"host": "10.0.0.50"},
    )
    snapshot = config_snapshot(configs=[payload], generation=7)
    headers = runtime_headers(container_id="runtime-123")

    assert payload["config_id"] == "plug-1"
    assert snapshot["generation"] == 7
    assert headers["X-Container-Id"] == "runtime-123"
```

What is happening here:

- `config_payload(...)` creates a realistic `/config` body
- `config_snapshot(...)` wraps that config inside a `/config/sync` body
- `runtime_headers(...)` builds the auth headers Core-style runtimes expect

This example does not start a server yet. It is a good first step when you only
need realistic test data.

## How The Pytest Plugin Works

This package registers itself as a pytest plugin. That means when pytest loads
the package, these fixtures become available automatically:

- `mock_core`
- `runtime_headers`
- `config_payload`
- `config_snapshot`

In most cases you do not need to import the fixtures manually. You can just use
them as test function arguments.

Example:

```python
def test_with_fixtures(mock_core, runtime_headers):
    headers = runtime_headers()
    assert mock_core.base_url.startswith("http://127.0.0.1:")
    assert "X-Container-Id" in headers
```

## Pytest Fixtures

### `mock_core`

Starts a small local HTTP server in the background and shuts it down after the
test finishes.

The server listens on a random local port and exposes:

- `POST /api/v2/integrations/telemetry`
- `POST /api/v2/events/ingest`

Both routes capture requests and return configurable JSON responses.

Use this fixture when:

- your runtime sends telemetry to Core
- your runtime sends events to Core
- you want to inspect what was sent
- you want to simulate error responses from Core

Example:

```python
def test_mock_core_defaults(mock_core):
    assert mock_core.telemetry_requests == []
    assert mock_core.event_requests == []
    assert mock_core.base_url.startswith("http://127.0.0.1:")
```

### `runtime_headers`

Returns the `build_runtime_headers(...)` function.

Use this fixture when you want to send realistic PiPhi auth headers into your
runtime routes.

Example:

```python
def test_runtime_headers(runtime_headers):
    headers = runtime_headers(container_id="runtime-123", internal_token="test-token")

    assert headers["X-Container-Id"] == "runtime-123"
    assert headers["X-PiPhi-Integration-Token"] == "test-token"
```

### `config_payload`

Returns the `build_config_payload(...)` function.

Use this fixture when you are testing `/config` or when you need a realistic
single config object for any other workflow.

Example:

```python
def test_config_payload_fixture(config_payload):
    payload = config_payload(
        config_id="sensor-1",
        extra={"host": "127.0.0.1"},
    )

    assert payload["id"] == "sensor-1"
    assert payload["config_id"] == "sensor-1"
    assert payload["host"] == "127.0.0.1"
```

### `config_snapshot`

Returns the `build_config_snapshot(...)` function.

Use this fixture when testing `/config/sync` logic, especially when your
runtime needs to add missing configs and remove stale ones.

Example:

```python
def test_config_snapshot_fixture(config_payload, config_snapshot):
    config = config_payload(config_id="sensor-1")
    snapshot = config_snapshot(configs=[config], generation=4)

    assert snapshot["generation"] == 4
    assert len(snapshot["configs"]) == 1
```

## Builder Functions

You can use the builder functions directly without pytest fixtures if you want:

- `build_runtime_headers(...)`
- `build_config_payload(...)`
- `build_config_snapshot(...)`

This can be useful in helper modules or test utility files.

### `build_runtime_headers(...)`

Signature:

```python
build_runtime_headers(
    *,
    container_id: str = "test-container",
    internal_token: str = "test-token",
    extra_headers: dict[str, str] | None = None,
) -> dict[str, str]
```

What it returns:

- a dictionary of request headers using the PiPhi header names

Example:

```python
from piphi_runtime_testkit_python import build_runtime_headers

headers = build_runtime_headers(
    container_id="runtime-123",
    internal_token="test-token",
    extra_headers={"X-Debug-Mode": "true"},
)
```

### `build_config_payload(...)`

Signature:

```python
build_config_payload(
    *,
    config_id: str = "config-1",
    device_id: str | None = None,
    container_id: str = "test-container",
    integration_id: str = "test-integration",
    include_core_config_id: bool = True,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]
```

Important behavior:

- `id` is set to `config_id`
- `device_id` defaults to the same value as `config_id`
- `config_id` is included by default
- `extra` is merged into the final payload

Example:

```python
from piphi_runtime_testkit_python import build_config_payload

payload = build_config_payload(
    config_id="plug-1",
    device_id="plug-physical-1",
    extra={
        "host": "10.0.0.12",
        "alias": "Kitchen Plug",
    },
)
```

### `build_config_snapshot(...)`

Signature:

```python
build_config_snapshot(
    *,
    configs: list[dict[str, Any]] | None = None,
    container_id: str = "test-container",
    integration_id: str = "test-integration",
    generation: int = 1,
    extra: dict[str, Any] | None = None,
) -> dict[str, Any]
```

Important behavior:

- `configs` defaults to an empty list
- `generation` defaults to `1`
- `extra` is merged into the final payload

Example:

```python
from piphi_runtime_testkit_python import build_config_payload, build_config_snapshot

first = build_config_payload(config_id="sensor-1", extra={"host": "10.0.0.1"})
second = build_config_payload(config_id="sensor-2", extra={"host": "10.0.0.2"})

snapshot = build_config_snapshot(configs=[first, second], generation=9)
```

## Assertion Helpers

The package exports:

- `assert_telemetry_sent(...)`
- `assert_event_sent(...)`

The `MockCoreServer` instance also exposes matching convenience methods:

- `mock_core.assert_telemetry_sent(...)`
- `mock_core.assert_event_sent(...)`

### `assert_telemetry_sent(...)`

Use this when you want to confirm at least one telemetry request reached the
mock Core server.

If you pass `device_id`, the helper finds a telemetry request for that device.

Example:

```python
telemetry_request = mock_core.assert_telemetry_sent(device_id="sensor-1")
assert telemetry_request.json_body["device_id"] == "sensor-1"
```

Failure behavior:

- if no telemetry was captured, the helper raises a readable `AssertionError`
- if telemetry was captured, but not for the requested `device_id`, the helper
  raises an error listing the captured device ids

### `assert_event_sent(...)`

Use this when you want to confirm that an event request reached the mock Core
server.

It can filter by:

- `device_id`
- `config_id`
- `event_type`

Example:

```python
event_request = mock_core.assert_event_sent(
    device_id="sensor-1",
    config_id="sensor-1",
    event_type="device.configured",
)
```

Important behavior:

This helper understands both common PiPhi event shapes:

- local-style event bodies using `event_type`
- Core-bound event bodies using `type`

That means it works well both for:

- local event-like payload tests
- real runtime SDK event delivery tests

## MockCoreServer API

The `mock_core` fixture gives you a `MockCoreServer` instance.

Useful properties:

- `mock_core.host`
- `mock_core.port`
- `mock_core.base_url`
- `mock_core.telemetry_url`
- `mock_core.event_url`
- `mock_core.telemetry_requests`
- `mock_core.event_requests`

Useful methods:

- `mock_core.set_telemetry_response(...)`
- `mock_core.set_event_response(...)`
- `mock_core.reset()`
- `mock_core.shutdown()`
- `mock_core.captured_telemetry_device_ids()`
- `mock_core.assert_telemetry_sent(...)`
- `mock_core.assert_event_sent(...)`

### Configure the response Core should return

You can simulate different Core behaviors by setting the next responses.

Example:

```python
def test_runtime_handles_event_failure(mock_core):
    mock_core.set_event_response(
        status_code=500,
        json_body={"ok": False, "detail": "simulated failure"},
    )
```

This is useful when you want to test:

- retry logic
- log output
- failure handling
- typed SDK exceptions

### Inspect captured requests manually

Example:

```python
request = mock_core.telemetry_requests[-1]

assert request.method == "POST"
assert request.path == "/api/v2/integrations/telemetry"
assert request.headers["Content-Type"] == "application/json"
assert request.json_body["device_id"] == "sensor-1"
```

### Reset between phases in the same test

If one test has multiple phases, you can clear captured requests and restore the
default success responses.

Example:

```python
mock_core.reset()
assert mock_core.telemetry_requests == []
assert mock_core.event_requests == []
```

## Basic Example

This example only uses the builders and fixtures.

```python
def test_runtime_builders(config_payload, config_snapshot, runtime_headers):
    payload = config_payload(
        config_id="plug-1",
        extra={"host": "10.0.0.50"},
    )
    snapshot = config_snapshot(configs=[payload], generation=7)
    headers = runtime_headers(container_id="runtime-123")

    assert payload["config_id"] == "plug-1"
    assert snapshot["generation"] == 7
    assert headers["X-Container-Id"] == "runtime-123"
```

This style is great when you want low-overhead tests for:

- payload shape
- config sync logic
- helper functions
- request wiring

## Mock Core Example

This example shows the mock server concept without a full runtime app:

```python
def test_mock_core_captures_requests(mock_core):
    mock_core.set_telemetry_response(status_code=200, json_body={"ok": True})

    # Point your runtime SDK client at mock_core.base_url, then:
    # mock_core.assert_telemetry_sent(device_id="plug-1")
```

This example is intentionally short. In real tests, your runtime will usually
perform the `POST` and the test will assert what the mock Core captured.

## FastAPI End-to-End Example

The strongest example in this package is a real FastAPI round-trip test in
[`tests/test_fastapi_runtime_example.py`](./tests/test_fastapi_runtime_example.py).

That test does all of these things:

1. creates a real FastAPI app
2. creates a real runtime starter from `piphi-runtime-kit-python`
3. applies a config using realistic headers and payloads
4. queues telemetry delivery to mock Core
5. queues event delivery to mock Core
6. waits for background delivery to complete
7. asserts what mock Core captured

Here is the important flow in shortened form:

```python
payload = config_payload(
    config_id="sensor-1",
    container_id="runtime-123",
    extra={"host": "127.0.0.1"},
)
headers = runtime_headers(
    container_id="runtime-123",
    internal_token="test-token",
)

client.post("/config", json=payload, headers=headers)
client.post("/telemetry/example")
client.post("/events/example")

wait_for(lambda: len(mock_core.telemetry_requests) >= 1)
wait_for(lambda: len(mock_core.event_requests) >= 1)

telemetry_request = mock_core.assert_telemetry_sent(device_id="sensor-1")
event_request = mock_core.assert_event_sent(
    device_id="sensor-1",
    config_id="sensor-1",
    event_type="device.configured",
)
```

Why this example matters:

- it proves the testkit works with a real FastAPI app
- it proves the testkit works with the real Python runtime SDK
- it demonstrates the intended developer workflow

If you are building a FastAPI integration, this is the best example to study.

## Common Test Patterns

### Test `/config` route behavior

Use:

- `config_payload`
- `runtime_headers`
- your framework test client

You will usually assert:

- response status
- response body
- registry update or local state change

### Test `/config/sync` route behavior

Use:

- `config_payload`
- `config_snapshot`

You will usually assert:

- new configs were applied
- stale configs were removed
- generation or snapshot metadata was stored

### Test outbound telemetry delivery

Use:

- `mock_core`
- `assert_telemetry_sent(...)`

You will usually assert:

- telemetry reached the Core endpoint
- the right `device_id` was used
- the right headers were sent
- the metric payload shape is correct

### Test outbound event delivery

Use:

- `mock_core`
- `assert_event_sent(...)`

You will usually assert:

- event reached the Core endpoint
- the right `config_id` and `device_id` were sent
- the right event type was sent

## Common Mistakes

### Forgetting to point your runtime client at `mock_core.base_url`

Symptom:

- your test passes locally without actually exercising outbound delivery
- or your runtime tries to talk to a real Core instance

Fix:

- configure your telemetry/event client to use `mock_core.base_url`

### Using mismatched `container_id` values in headers and payload

Symptom:

- auth or routing behavior looks confusing
- runtime state reflects one container id while requests were sent with another

Fix:

- keep your test inputs intentional
- if your runtime uses payload container ids as fallback or source of truth,
  make sure the payload and headers agree unless you are explicitly testing a
  mismatch

### Asserting only request count instead of payload shape

Symptom:

- tests say "a request happened" but do not tell you if it was the correct one

Fix:

- use `assert_telemetry_sent(device_id=...)`
- use `assert_event_sent(config_id=..., event_type=...)`

### Forgetting background delivery timing

Symptom:

- flaky tests
- request count is zero right after calling a route that only queued work

Fix:

- wait for delivery to complete before asserting
- use a polling helper like the `wait_for(...)` function in
  [`tests/test_fastapi_runtime_example.py`](./tests/test_fastapi_runtime_example.py)

## Troubleshooting

### "No telemetry requests were captured"

Check:

- did the runtime actually try to send telemetry?
- did the client point to `mock_core.base_url`?
- was delivery queued in the background and asserted too early?

### "Expected event matching filters, but none were captured"

Check:

- did your runtime send the expected `device_id`?
- did it send the expected `config_id`?
- are you filtering by the correct event name?
- are you dealing with a Core-style event payload using `type` instead of a
  local-style payload using `event_type`?

### "json_body is None"

This means the request body was not valid JSON.

Check:

- whether the runtime sent plain text or malformed JSON
- whether the request body was empty

The raw bytes are still available on `CapturedRequest.body`.

### Unknown path responses from mock Core

The mock Core server only handles:

- `/api/v2/integrations/telemetry`
- `/api/v2/events/ingest`

If your runtime posts somewhere else, the mock server returns `404` with:

```json
{"ok": false, "detail": "unknown path"}
```

That usually means your runtime is using the wrong endpoint path.

## Public API Reference

Top-level exports:

- `CapturedRequest`
- `MockCoreServer`
- `assert_event_sent`
- `assert_telemetry_sent`
- `build_config_payload`
- `build_config_snapshot`
- `build_runtime_headers`

Pytest fixtures:

- `mock_core`
- `runtime_headers`
- `config_payload`
- `config_snapshot`

## Design Goals

This project is trying to stay:

- pytest-first
- easy to read
- easy to debug
- low setup
- friendly to junior developers
- flexible enough for advanced integration tests

The goal is not to create a giant testing framework. The goal is to make the
common PiPhi runtime testing tasks pleasant and obvious.
