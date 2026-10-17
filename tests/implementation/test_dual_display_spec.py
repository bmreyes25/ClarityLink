"""Executable guards for ClarityLink's fixed dual-display requirements."""
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
ALLOWED_EVIDENCE_LABELS = {
    "SOURCE_IMPLEMENTED", "HOST_TESTED", "API17_EMULATOR_TESTED", "ARMV7_BUILT",
    "STATIC_HONDA_EVIDENCE", "EXTERNAL_PRIOR_ART", "UNPROVEN_EXTERNAL_INTERFACE",
    "NOT_IMPLEMENTED",
}
EXPECTED_DISPLAY0 = (
    "Factory Honda CarPlay primary Type110, video, USB/iAP2, authentication, audio, "
    "microphone, Siri, calls, and controls remain Honda-owned."
)
EXPECTED_DISPLAY1 = (
    "A distinct simultaneous authentic iPhone CarPlay Type111 navigation stream "
    "in the existing instrument-cluster Navigation region."
)


def load_spec():
    # The private engineering inventory is deliberately not shipped. Keep the
    # public test contract synthetic and point it at the implementation under test.
    ids = ["capability_descriptors", "info_response", "type110_transport_ownership",
           "type111_setup", "stream_endpoint_management", "security_context_ownership",
           "screen_frame_parsing", "h264_decoder", "android_native_buffer_bridge",
           "android_view_renderer", "presentation_host", "hosted_view_adapter",
           "shared_memory_frame_transport", "session_lifecycle", "render_safe_area",
           "warning_preemption", "resource_cleanup", "armv7_build", "test_apk_packaging",
           "future_diagnostic_deployment_tooling"]
    source_paths = [
        "src/claritylink-jmcs/claritylink_jmcs/capabilities.py",
        "src/claritylink-jmcs/claritylink_jmcs/info.py",
        "src/claritylink-jmcs/claritylink_jmcs/receiver.py",
        "src/claritylink-jmcs/claritylink_jmcs/receiver.py",
        "src/claritylink-jmcs/claritylink_jmcs/stream_dispatch.py",
        "src/claritylink-jmcs/claritylink_jmcs/security.py",
        "android/cl-imp-03-app/java/org/claritylink/android/FrameIpcProtocol.java",
        "android/cl-imp-03-app/java/org/claritylink/android/Api17DecoderLabActivity.java",
        "android/src/main/java/org/claritylink/android/Yuv420FrameAdapter.java",
        "android/cl-imp-03-app/java/org/claritylink/android/ClarityLinkDisplayActivity.java",
        "src/claritylink-renderer/android-api17/Display1OutputBackend.java",
        "src/claritylink-renderer/android-api17/ClarityLinkContentView.java",
        "src/claritylink-renderer/android-api17/FrameDispatchGate.java",
        "src/claritylink-jmcs/claritylink_jmcs/session.py",
        "src/claritylink-renderer/safe_area.py",
        "src/claritylink-renderer/cluster_priority_model.py",
        "src/claritylink-renderer/android-api17/FrameDispatchGate.java",
        "tools/compile_android_api17_java.sh",
        "tools/build_test3_admission_probe.sh",
        "tools/test3_output_validation_v2.py",
    ]
    return {
        "production_feature_enabled": False,
        "fixed_goal": {
            "display0": EXPECTED_DISPLAY0,
            "display1": EXPECTED_DISPLAY1,
            "carplay_ultra": False,
            "mirror_is_completion": False,
            "synthetic_content_is_authentic": False,
        },
        "ownership_contract": {
            "primary_session": "factory_honda", "type110_owner": "factory_honda",
            "usb_iap2_owner": "factory_honda", "accessory_authentication_owner": "factory_honda",
            "audio_owner": "factory_honda", "microphone_owner": "factory_honda",
            "siri_owner": "factory_honda", "calls_owner": "factory_honda",
            "steering_controls_owner": "factory_honda", "touch_controls_owner": "factory_honda",
            "primary_video_type": 110,
        },
        "stream_contract": {
            "primary_stream_type": 110, "primary_owner": "factory_honda",
            "secondary_stream_type": 111, "secondary_source": "connected_iphone",
            "secondary_content": "authentic_carplay_navigation",
            "secondary_derived_from_primary": False, "synthetic_fixture_is_lab_only": True,
        },
        "accepted_honda_integration_evidence_records": [],
        "accepted_authentic_iphone_type111_evidence_records": [],
        "components": [{"id": component_id, "claims_honda_integration": False,
                        "claims_authentic_iphone_type111": False,
                        "evidence": [], "files": [source_paths[index]], "tests": []}
                       for index, component_id in enumerate(ids)],
        "external_gates": [{"id": f"GATE-{index}", "status": "UNPROVEN"}
                           for index in range(1, 7)],
    }


def validate_fixed_architecture(spec):
    errors = []
    goal = spec.get("fixed_goal", {})
    if spec.get("production_feature_enabled") is not False:
        errors.append("production feature must remain disabled")
    if goal.get("display0") != EXPECTED_DISPLAY0:
        errors.append("Display 0 goal text must preserve the fixed factory-owned primary path")
    if goal.get("display1") != EXPECTED_DISPLAY1:
        errors.append("Display 1 goal text must preserve the fixed authentic Type111 path")
    ownership = spec.get("ownership_contract", {})
    for key in ("primary_session", "type110_owner", "usb_iap2_owner",
                "accessory_authentication_owner", "audio_owner", "microphone_owner",
                "siri_owner", "calls_owner", "steering_controls_owner", "touch_controls_owner"):
        if ownership.get(key) != "factory_honda":
            errors.append(f"Display 0 owner must remain factory Honda: {key}")
    if ownership.get("primary_video_type") != 110:
        errors.append("factory Type110 video must remain primary")
    display1 = goal.get("display1", "").lower()
    for required in ("type111", "simultaneous", "authentic", "iphone"):
        if required not in display1:
            errors.append(f"Display 1 requirement missing {required}")
    if goal.get("carplay_ultra") is not False:
        errors.append("CarPlay Ultra is outside the goal")
    if goal.get("mirror_is_completion") is not False:
        errors.append("mirroring cannot satisfy the goal")
    if goal.get("synthetic_content_is_authentic") is not False:
        errors.append("synthetic content cannot be authentic")
    stream = spec.get("stream_contract", {})
    if stream.get("primary_stream_type") != 110 or stream.get("primary_owner") != "factory_honda":
        errors.append("factory Type110 ownership must remain primary")
    if stream.get("secondary_stream_type") != 111:
        errors.append("secondary stream must be Type111")
    if stream.get("secondary_source") != "connected_iphone":
        errors.append("secondary stream must come from the connected iPhone")
    if stream.get("secondary_content") != "authentic_carplay_navigation":
        errors.append("secondary content must be authentic CarPlay navigation")
    if stream.get("secondary_derived_from_primary") is not False:
        errors.append("mirrored primary frames cannot be labeled Type111")
    if stream.get("synthetic_fixture_is_lab_only") is not True:
        errors.append("synthetic frames must remain lab-only")
    if spec.get("accepted_honda_integration_evidence_records") != []:
        errors.append("no Honda integration evidence is accepted at this offline baseline")
    if spec.get("accepted_authentic_iphone_type111_evidence_records") != []:
        errors.append("no authentic iPhone Type111 evidence is accepted at this offline baseline")
    for component in spec.get("components", []):
        if component.get("claims_honda_integration") is not False:
            errors.append(f"component {component.get('id')} must explicitly deny Honda integration")
        if component.get("claims_authentic_iphone_type111") is not False:
            errors.append(f"component {component.get('id')} must explicitly deny authentic iPhone Type111")
        if not set(component.get("evidence", [])).issubset(ALLOWED_EVIDENCE_LABELS):
            errors.append(f"component {component.get('id')} has unrecognized evidence labels")
    return errors


def validate_evidence_claim(evidence, claim):
    """No external-integration evidence is accepted by this offline baseline."""
    del evidence, claim
    return False


def test_committed_spec_preserves_fixed_goal():
    assert validate_fixed_architecture(load_spec()) == []


def test_replacing_primary_carplay_is_rejected():
    spec = load_spec()
    spec["fixed_goal"]["display0"] = "ClarityLink owns primary Type110 and all controls."
    assert "Display 0 goal text must preserve the fixed factory-owned primary path" in validate_fixed_architecture(spec)
    spec["ownership_contract"]["primary_session"] = "claritylink"
    assert "Display 0 owner must remain factory Honda: primary_session" in validate_fixed_architecture(spec)
    spec = load_spec()
    spec["ownership_contract"]["microphone_owner"] = "claritylink"
    assert "Display 0 owner must remain factory Honda: microphone_owner" in validate_fixed_architecture(spec)


def test_mirrored_display0_is_not_type111_completion():
    spec = load_spec()
    spec["fixed_goal"]["mirror_is_completion"] = True
    assert "mirroring cannot satisfy the goal" in validate_fixed_architecture(spec)
    spec["fixed_goal"]["mirror_is_completion"] = False
    spec["stream_contract"]["secondary_derived_from_primary"] = True
    assert "mirrored primary frames cannot be labeled Type111" in validate_fixed_architecture(spec)


def test_synthetic_navigation_cannot_be_claimed_authentic():
    spec = load_spec()
    spec["fixed_goal"]["synthetic_content_is_authentic"] = True
    assert "synthetic content cannot be authentic" in validate_fixed_architecture(spec)
    assert not validate_evidence_claim(["HOST_TESTED", "SYNTHETIC_TEST_VALUE"], "AUTHENTIC_IPHONE_TYPE111")


def test_mock_or_build_evidence_cannot_claim_honda_integration():
    for evidence in (["HOST_TESTED"], ["API17_EMULATOR_TESTED"], ["ARMV7_BUILT"],
                     ["SOURCE_IMPLEMENTED"], ["STATIC_HONDA_EVIDENCE"],
                     ["OBSERVED_ON_HONDA_READ_ONLY"], ["EXTERNAL_PRIOR_ART"]):
        assert not validate_evidence_claim(evidence, "HONDA_INTEGRATION")
    assert not validate_evidence_claim(["HONDA_INTEGRATION_VALIDATED"], "HONDA_INTEGRATION")
    assert not validate_evidence_claim(["AUTHENTIC_IPHONE_TYPE111"], "AUTHENTIC_IPHONE_TYPE111")


def test_component_cannot_promote_unproven_external_claims():
    spec = load_spec()
    spec["components"][0]["claims_honda_integration"] = True
    assert any("explicitly deny Honda integration" in error for error in validate_fixed_architecture(spec))
    spec = load_spec()
    spec["components"][0]["claims_authentic_iphone_type111"] = True
    assert any("explicitly deny authentic iPhone Type111" in error for error in validate_fixed_architecture(spec))


def test_component_claim_fields_must_be_explicit_false():
    spec = load_spec()
    del spec["components"][0]["claims_honda_integration"]
    assert any("must explicitly deny Honda integration" in error
               for error in validate_fixed_architecture(spec))
    spec = load_spec()
    spec["components"][0]["claims_authentic_iphone_type111"] = "no"
    assert any("must explicitly deny authentic iPhone Type111" in error
               for error in validate_fixed_architecture(spec))


def test_inventory_has_all_required_component_families_and_external_gates():
    spec = load_spec()
    ids = {component["id"] for component in spec["components"]}
    assert len(ids) == 20
    assert {"capability_descriptors", "info_response", "type110_transport_ownership",
            "type111_setup", "stream_endpoint_management", "security_context_ownership",
            "screen_frame_parsing", "h264_decoder", "android_native_buffer_bridge",
            "android_view_renderer", "presentation_host", "hosted_view_adapter",
            "shared_memory_frame_transport", "session_lifecycle", "render_safe_area",
            "warning_preemption", "resource_cleanup", "armv7_build",
            "test_apk_packaging", "future_diagnostic_deployment_tooling"} == ids
    assert len(spec["external_gates"]) >= 6


def test_inventory_references_existing_repository_paths():
    spec = load_spec()
    missing = [item for component in spec["components"] for item in component["files"] + component["tests"]
               if not (ROOT / item).exists()]
    assert missing == []
