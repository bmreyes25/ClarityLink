from pathlib import Path
import json
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-jmcs"))

from claritylink_jmcs.capabilities import (  # noqa: E402
    CapabilityError,
    CapabilityMode,
    DisplayRole,
    EvidenceClass,
    HondaStatus,
    LocalDisplayGeometry,
    SecondaryDisplayCapability,
    SessionOwner,
    build_dual_display_plan,
    host_info,
    resolve_local_renderer_geometry,
)


def test_type110_primary_owner_survives_optional_type111_plan():
    plan = build_dual_display_plan(7, 1100, 1110, mode=CapabilityMode.SYNTHETIC_LAB)
    assert plan.preserves_primary_ownership
    assert (plan.primary.stream_type, plan.primary.role, plan.primary.owner) == (
        110, DisplayRole.PRIMARY, SessionOwner.FACTORY_HONDA_RECEIVER)
    assert (plan.primary.honda_status, plan.secondary.honda_status) == (
        HondaStatus.UNKNOWN, HondaStatus.UNKNOWN)
    assert plan.primary.evidence is EvidenceClass.SYNTHETIC_TEST_VALUE
    assert plan.primary_ownership.evidence is EvidenceClass.HONDA_CONFIRMED
    assert plan.primary_ownership.honda_status is HondaStatus.CONFIRMED
    assert plan.primary.generation == plan.secondary.generation == 7
    assert plan.secondary.stream_connection_id != plan.primary.stream_connection_id


def test_secondary_type111_is_disabled_outside_explicit_synthetic_mode():
    primary_only = build_dual_display_plan(1, 11)
    assert primary_only.secondary is None and primary_only.preserves_primary_ownership
    with pytest.raises(CapabilityError, match="production_advertisement_disabled"):
        build_dual_display_plan(1, 11, 12)
    with pytest.raises(CapabilityError, match="production_advertisement_disabled"):
        build_dual_display_plan(1, 11, 12, mode=CapabilityMode.PRODUCTION)


def test_duplicate_stream_identity_and_invalid_generations_fail_closed():
    with pytest.raises(CapabilityError, match="invalid_secondary_stream_ownership"):
        build_dual_display_plan(2, 12, 12, mode=CapabilityMode.SYNTHETIC_LAB)
    for generation in (0, -1, True):
        with pytest.raises(CapabilityError, match="invalid_session_generation"):
            build_dual_display_plan(generation, 12)


def test_navigation_map_role_and_geometry_preserve_field_provenance():
    plan = build_dual_display_plan(3, 30, 31, mode=CapabilityMode.SYNTHETIC_LAB)
    secondary = plan.secondary
    assert secondary.role is DisplayRole.SECONDARY_NAVIGATION
    assert secondary.evidence is EvidenceClass.CURRENT_IOS_LAB_CONFIRMED
    assert secondary.geometry.evidence is EvidenceClass.SYNTHETIC_TEST_VALUE
    assert secondary.navigation_role.value == "maps:/car/instrumentcluster/map"
    assert secondary.navigation_role.evidence is EvidenceClass.CURRENT_IOS_LAB_CONFIRMED
    assert secondary.navigation_role.honda_status is HondaStatus.UNKNOWN


def test_local_geometry_fits_safe_area_and_preserves_aspect_ratio():
    target = LocalDisplayGeometry(800, 480, 20, 20, 760, 440)
    left, top, width, height = resolve_local_renderer_geometry(1920, 1080, target)
    assert (left, top, width, height) == (20, 26, 760, 427)
    assert left >= target.safe_left_px and top >= target.safe_top_px
    assert left + width <= target.safe_left_px + target.safe_width_px
    assert top + height <= target.safe_top_px + target.safe_height_px
    with pytest.raises(CapabilityError, match="invalid_source_geometry"):
        resolve_local_renderer_geometry(0, 1080, target)


def test_info_advertisement_is_primary_only_unless_lab_mode_is_explicit():
    assert [item["type"] for item in host_info(SecondaryDisplayCapability())["displays"]] == [110]
    with pytest.raises(CapabilityError, match="explicit_synthetic_lab_mode"):
        SecondaryDisplayCapability(enabled=True)
    lab = host_info(SecondaryDisplayCapability.synthetic_lab())
    assert [item["type"] for item in lab["displays"]] == [110, 111]
    assert lab["displays"][0]["uuid"] != lab["displays"][1]["uuid"]
    with pytest.raises(CapabilityError, match="duplicate_display_uuid"):
        SecondaryDisplayCapability.synthetic_lab(main_uuid="b7e6c5a0-1111-4000-8000-000000000001",
                                                 secondary_uuid="b7e6c5a0-1111-4000-8000-000000000001")


def test_internal_capability_fields_are_not_wire_serializable():
    plan = build_dual_display_plan(9, 90, 91, mode=CapabilityMode.SYNTHETIC_LAB)
    assert not hasattr(plan, "to_plist")
    assert not hasattr(plan, "as_wire_fields")
    assert plan.primary.stream_type == 110 and plan.secondary.stream_type == 111


def test_sanitized_43r_fixture_maps_by_type_not_array_order():
    sys.path.insert(0, str(ROOT / "src" / "claritylink-jmcs"))
    from claritylink_jmcs.setup import SetupRequest

    fixture = json.loads((ROOT / "research/simulator/43r-type111-first-setup.json").read_text())
    request = SetupRequest.parse(fixture["request"], 12)
    ids = {item.type: item.stream_connection_id for item in request.streams}
    plan = build_dual_display_plan(
        12, ids[110], ids[111], mode=CapabilityMode.SYNTHETIC_LAB)
    assert [item.type for item in request.streams] == [111, 110]
    assert plan.primary.stream_type == 110 and plan.secondary.stream_type == 111
    assert plan.primary.stream_connection_id == 1101
    assert plan.secondary.stream_connection_id == 2201
