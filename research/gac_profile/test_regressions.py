# SPDX-FileCopyrightText: Contributors to openadr3-client-gac-compliance
# SPDX-License-Identifier: Apache-2.0
"""GAC profile regressions against the published ElaadNL Pydantic models.

For openadr3-client-gac-compliance==3.2.4. Tests intentionally fail
on the unmodified upstream release and must pass after apply_fix.py.
No network, VTN, devices, or credentials are needed by the tests.
"""
from datetime import UTC, datetime, timedelta
from importlib import import_module

import pytest
from pydantic import ValidationError
from openadr3_client._models.common.interval import Interval
from openadr3_client._models.common.interval_period import IntervalPeriod
from openadr3_client.plugin import ValidatorPluginRegistry


def _profile(version: str):
    api = "oadr301" if version == "gac20" else "oadr310"
    event_model = import_module(f"openadr3_client.{api}.models.event.event")
    payload_model = import_module(f"openadr3_client.{api}.models.event.event_payload")
    unit_model = import_module(f"openadr3_client.{api}.models.unit")
    plugin_model = import_module(f"openadr3_client_gac_compliance.{version}.plugin")
    cls = getattr(plugin_model, {"gac20": "Gac20ValidatorPlugin", "gac21": "Gac21ValidatorPlugin", "gac22": "Gac22ValidatorPlugin"}[version])
    return event_model, payload_model, unit_model, cls


def _make_event(version: str, *, faulty_first: str | None = None, empty_descriptors: bool = False):
    event_model, payload_model, unit_model, plugin = _profile(version)
    ValidatorPluginRegistry.clear_plugins()
    ValidatorPluginRegistry.register_plugin(plugin.setup())
    payload = payload_model.EventPayload
    typ = payload_model.EventPayloadType

    def create_payload(kind=None, values=(25.0,)):
        return payload(type=kind or typ.IMPORT_CAPACITY_LIMIT, values=values)

    def create_interval(idx, values):
        return Interval(
            id=idx,
            interval_period=IntervalPeriod(
                start=datetime(2026, 11, 3, 10, idx * 5, tzinfo=UTC),
                duration=timedelta(minutes=5),
            ),
            payloads=values,
        )

    bad = (create_payload(),)
    if faulty_first == "extra_payload":
        bad = (create_payload(), create_payload())
    elif faulty_first == "wrong_type":
        bad = (create_payload(kind=typ.PRICE),)
    elif faulty_first == "extra_value":
        bad = (create_payload(values=(25.0, 30.0)),)
    intervals = (create_interval(0, bad), create_interval(1, (create_payload(),)))
    descriptors = () if empty_descriptors else (
        payload_model.EventPayloadDescriptor(payload_type=typ.IMPORT_CAPACITY_LIMIT, units=unit_model.Unit.KW),
    )
    if version == "gac20":
        target_mod = import_module("openadr3_client.oadr301.models.target")
        targets = (
            target_mod.Target(type="POWER_SERVICE_LOCATION", values=("123456789012345678",)),
            target_mod.Target(type="VEN_NAME", values=("test-ven",)),
        )
    else:
        targets = ("123456789012345678",)
    return event_model.NewEvent(
        programID="test-program",
        event_name="test-event",
        priority=None,
        targets=targets,
        payload_descriptors=descriptors,
        interval_period=None,
        intervals=intervals,
    )


@pytest.fixture(autouse=True)
def clear_registry():
    ValidatorPluginRegistry.clear_plugins()
    yield
    ValidatorPluginRegistry.clear_plugins()


@pytest.mark.parametrize("version", ["gac21", "gac22"])
@pytest.mark.parametrize("faulty_first,pattern", [
    ("extra_payload", "exactly one payload"),
    ("wrong_type", "must have a payload type"),
    ("extra_value", "exactly one value per payload"),
])
def test_all_intervals_checked_not_just_last(version, faulty_first, pattern):
    with pytest.raises(ValidationError, match=pattern):
        _make_event(version, faulty_first=faulty_first)


@pytest.mark.parametrize("version", ["gac20", "gac21", "gac22"])
def test_empty_descriptor_returns_structured_validation_error(version):
    with pytest.raises(ValidationError, match="exactly one payload descriptor"):
        _make_event(version, empty_descriptors=True)


def test_gac20_preexisting_multi_interval_validation():
    # 2.0 already validates each interval; do not alter this implementation.
    with pytest.raises(ValidationError, match="exactly one payload"):
        _make_event("gac20", faulty_first="extra_payload")


@pytest.mark.parametrize("version", ["gac20", "gac21", "gac22"])
def test_two_valid_intervals_continue_to_pass(version):
    event = _make_event(version)
    assert len(event.intervals) == 2
