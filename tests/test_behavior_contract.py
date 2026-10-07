import pytest

from piphi_runtime_testkit_python import (
    CapturedRequest,
    MockCoreServer,
    assert_behavior_conditions_match_telemetry,
    find_behavior_telemetry_issues,
)


def _behaviors() -> dict:
    return {
        "behaviorSchemaVersion": "integration.behaviors.v2",
        "devices": [
            {
                "id": "light",
                "name": "Light",
                "conditions": [
                    {
                        "id": "is_on",
                        "label": "Power is on",
                        "type": "boolean",
                        "runtime": {
                            "source": "state",
                            "field": "is_on",
                            "fieldAliases": ["power_state"],
                        },
                    },
                    {
                        "id": "brightness_above",
                        "label": "Brightness is above",
                        "type": "number",
                        "runtime": {"source": "state", "field": "brightness"},
                    },
                ],
            }
        ],
        "templates": [
            {
                "id": "bright_light",
                "label": "Bright light",
                "deviceKey": "light",
                "config": {
                    "conditionTree": {
                        "id": "is_on",
                        "sourceRef": {"optionKey": "is_on"},
                        "field": "is_on",
                        "operator": "eq",
                        "value": True,
                    }
                },
            }
        ],
    }


def test_behavior_conditions_accept_fields_aliases_types_and_templates() -> None:
    assert_behavior_conditions_match_telemetry(
        _behaviors(),
        {"metrics": {"power_state": True, "brightness": 42}},
    )


def test_behavior_conditions_report_missing_field_and_type_mismatch() -> None:
    issues = find_behavior_telemetry_issues(
        _behaviors(),
        [{"is_on": "yes"}],
    )

    assert [(issue.condition_id, issue.reason) for issue in issues] == [
        ("is_on", "emitted value does not match declared type 'boolean'"),
        (
            "brightness_above",
            "field was not emitted by any representative telemetry sample",
        ),
        ("is_on", "emitted value does not match declared type 'boolean'"),
    ]


def test_behavior_conditions_fail_with_actionable_message() -> None:
    with pytest.raises(AssertionError, match="brightness_above"):
        assert_behavior_conditions_match_telemetry(_behaviors(), {"is_on": True})


def test_dynamic_conditions_require_explicit_exemption() -> None:
    behaviors = _behaviors()
    behaviors["devices"][0]["conditions"] = [
        {
            "id": "feature_equals",
            "label": "Feature equals",
            "runtime": {
                "source": "state",
                "fieldFromParam": "feature_id",
            },
        }
    ]
    behaviors["templates"] = []

    issues = find_behavior_telemetry_issues(behaviors, {})
    assert issues[0].reason == "dynamic condition needs an explicit test exemption"

    assert_behavior_conditions_match_telemetry(
        behaviors,
        {},
        dynamic_condition_ids={"feature_equals"},
    )


def test_non_state_conditions_are_outside_telemetry_gate() -> None:
    behaviors = _behaviors()
    behaviors["devices"][0]["conditions"] = [
        {
            "id": "weekday",
            "label": "It is Monday",
            "runtime": {"source": "calendar", "field": "weekday"},
        }
    ]
    behaviors["templates"] = []

    assert find_behavior_telemetry_issues(behaviors, {}) == []


def test_mock_core_validates_behaviors_against_captured_telemetry() -> None:
    mock_core = MockCoreServer()
    try:
        mock_core.telemetry_requests.append(
            CapturedRequest(
                method="POST",
                path="/api/v2/integrations/telemetry",
                headers={},
                body=b"{}",
                json_body={"metrics": {"is_on": True, "brightness": 42}},
            )
        )
        mock_core.assert_behavior_conditions_match_telemetry(_behaviors())
    finally:
        mock_core.shutdown()
