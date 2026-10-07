"""Conformance checks between automation behaviors and emitted telemetry."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BehaviorTelemetryIssue:
    """One behavior condition that cannot be evaluated from runtime telemetry."""

    device_id: str
    condition_id: str
    field: str
    aliases: tuple[str, ...]
    reason: str
    template_id: str | None = None

    def describe(self) -> str:
        owner = (
            f"template {self.template_id!r}"
            if self.template_id
            else f"device {self.device_id!r}"
        )
        candidates = ", ".join(repr(item) for item in (self.field, *self.aliases))
        return (
            f"{owner} condition {self.condition_id!r}: {self.reason}; "
            f"expected one of [{candidates}]"
        )


def _as_mapping(value: Any) -> Mapping[str, Any]:
    return value if isinstance(value, Mapping) else {}


def _as_list(value: Any) -> list[Any]:
    return list(value) if isinstance(value, (list, tuple)) else []


def _metric_samples(
    telemetry_samples: Iterable[Mapping[str, Any]] | Mapping[str, Any],
) -> list[Mapping[str, Any]]:
    raw_samples = (
        [telemetry_samples]
        if isinstance(telemetry_samples, Mapping)
        else list(telemetry_samples)
    )
    samples: list[Mapping[str, Any]] = []
    for sample in raw_samples:
        payload = _as_mapping(sample)
        metrics = payload.get("metrics")
        samples.append(_as_mapping(metrics) if isinstance(metrics, Mapping) else payload)
    return samples


def _field_aliases(runtime: Mapping[str, Any]) -> tuple[str, ...]:
    raw_aliases = runtime.get("fieldAliases", runtime.get("field_aliases"))
    return tuple(
        dict.fromkeys(
            str(alias or "").strip()
            for alias in _as_list(raw_aliases)
            if str(alias or "").strip()
        )
    )


def _value_matches_type(value: Any, condition_type: str) -> bool:
    normalized_type = str(condition_type or "").strip().lower()
    if not normalized_type:
        return True
    if normalized_type == "boolean":
        return isinstance(value, bool)
    if normalized_type == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if normalized_type in {"text", "enum"}:
        return isinstance(value, str)
    return True


def _condition_issue(
    condition: Mapping[str, Any],
    *,
    device_id: str,
    samples: list[Mapping[str, Any]],
    dynamic_condition_ids: set[str],
    template_id: str | None = None,
) -> BehaviorTelemetryIssue | None:
    condition_id = str(condition.get("id") or condition.get("field") or "condition").strip()
    runtime = _as_mapping(condition.get("runtime"))
    source = str(runtime.get("source") or condition.get("source") or "state").strip().lower()
    if source not in {"", "state"}:
        return None

    if condition_id in dynamic_condition_ids:
        return None

    dynamic_field_param = str(
        runtime.get("fieldFromParam") or runtime.get("field_from_param") or ""
    ).strip()
    if dynamic_field_param:
        return BehaviorTelemetryIssue(
            device_id=device_id,
            condition_id=condition_id,
            field=dynamic_field_param,
            aliases=(),
            reason="dynamic condition needs an explicit test exemption",
            template_id=template_id,
        )

    field = str(runtime.get("field") or condition.get("field") or "").strip()
    if not field:
        return BehaviorTelemetryIssue(
            device_id=device_id,
            condition_id=condition_id,
            field="<missing>",
            aliases=(),
            reason="state-backed condition does not declare a runtime field",
            template_id=template_id,
        )

    aliases = _field_aliases(runtime)
    candidates = (field, *aliases)
    observed = [
        sample[candidate]
        for sample in samples
        for candidate in candidates
        if candidate in sample
    ]
    if not observed:
        return BehaviorTelemetryIssue(
            device_id=device_id,
            condition_id=condition_id,
            field=field,
            aliases=aliases,
            reason="field was not emitted by any representative telemetry sample",
            template_id=template_id,
        )

    condition_type = str(condition.get("type") or runtime.get("type") or "").strip()
    if condition_type and not any(
        _value_matches_type(value, condition_type) for value in observed
    ):
        return BehaviorTelemetryIssue(
            device_id=device_id,
            condition_id=condition_id,
            field=field,
            aliases=aliases,
            reason=f"emitted value does not match declared type {condition_type!r}",
            template_id=template_id,
        )
    return None


def _condition_leaves(node: Any) -> Iterable[Mapping[str, Any]]:
    current = _as_mapping(node)
    if not current:
        return
    children = _as_list(current.get("children"))
    if children:
        for child in children:
            yield from _condition_leaves(child)
        return
    yield current


def find_behavior_telemetry_issues(
    behaviors: Mapping[str, Any],
    telemetry_samples: Iterable[Mapping[str, Any]] | Mapping[str, Any],
    *,
    dynamic_condition_ids: Iterable[str] = (),
) -> list[BehaviorTelemetryIssue]:
    """Return conditions that representative runtime telemetry cannot evaluate.

    ``telemetry_samples`` may contain raw metric mappings or Core telemetry
    payloads with a ``metrics`` object. Parameter-driven dynamic conditions must
    be named explicitly in ``dynamic_condition_ids`` and tested separately.
    """

    samples = _metric_samples(telemetry_samples)
    dynamic_ids = {
        str(condition_id or "").strip()
        for condition_id in dynamic_condition_ids
        if str(condition_id or "").strip()
    }
    devices = [
        _as_mapping(device)
        for device in _as_list(behaviors.get("devices"))
        if isinstance(device, Mapping)
    ]
    devices_by_id = {
        str(device.get("id") or "").strip(): device
        for device in devices
        if str(device.get("id") or "").strip()
    }
    options_by_device = {
        device_id: {
            str(condition.get("id") or "").strip(): condition
            for condition in _as_list(device.get("conditions"))
            if isinstance(condition, Mapping)
        }
        for device_id, device in devices_by_id.items()
    }

    issues: list[BehaviorTelemetryIssue] = []
    for device_id, device in devices_by_id.items():
        for raw_condition in _as_list(device.get("conditions")):
            condition = _as_mapping(raw_condition)
            issue = _condition_issue(
                condition,
                device_id=device_id,
                samples=samples,
                dynamic_condition_ids=dynamic_ids,
            )
            if issue:
                issues.append(issue)

    for raw_template in _as_list(behaviors.get("templates")):
        template = _as_mapping(raw_template)
        template_id = str(template.get("id") or "template").strip()
        device_id = str(
            template.get("deviceKey") or template.get("device_key") or ""
        ).strip()
        condition_options = options_by_device.get(device_id, {})
        config = _as_mapping(template.get("config"))
        condition_tree = config.get("conditionTree", config.get("condition_tree"))
        for leaf in _condition_leaves(condition_tree):
            option_key = str(
                _as_mapping(leaf.get("sourceRef")).get("optionKey")
                or _as_mapping(leaf.get("source_ref")).get("option_key")
                or leaf.get("id")
                or ""
            ).strip()
            option = condition_options.get(option_key, {})
            merged = {**option, **leaf}
            if option.get("runtime") and not leaf.get("runtime"):
                merged["runtime"] = option["runtime"]
            issue = _condition_issue(
                merged,
                device_id=device_id,
                samples=samples,
                dynamic_condition_ids=dynamic_ids,
                template_id=template_id,
            )
            if issue:
                issues.append(issue)
    return issues


def assert_behavior_conditions_match_telemetry(
    behaviors: Mapping[str, Any],
    telemetry_samples: Iterable[Mapping[str, Any]] | Mapping[str, Any],
    *,
    dynamic_condition_ids: Iterable[str] = (),
) -> None:
    """Fail a contract test when advertised conditions lack runtime telemetry."""

    issues = find_behavior_telemetry_issues(
        behaviors,
        telemetry_samples,
        dynamic_condition_ids=dynamic_condition_ids,
    )
    if issues:
        details = "\n".join(f"- {issue.describe()}" for issue in issues)
        raise AssertionError(
            "Behavior conditions do not match emitted telemetry:\n" + details
        )
