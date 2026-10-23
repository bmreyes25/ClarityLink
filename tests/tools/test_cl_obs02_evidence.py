"""CL-OBS-02 evidence workflow: private layout, sealing, classification, and document agreement.

Uses synthetic notes and dummy media only. No Honda footage, vehicle, ADB, or network is involved.
"""
import copy
import os
import re
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "tools"))
import check_public_safety  # noqa: E402
import cl_obs02_evidence as ev  # noqa: E402

PACKET = REPO / "docs/development/cl-obs-02-preflight-packet.md"
ACCEPT = REPO / "docs/development/cl-obs-02-evidence-acceptance.md"

COMPLETE_RECORD = {
    "baseline_recorded": "OBSERVED", "casting_on_navigation": "OBSERVED", "page_exit_result": "OBSERVED",
    "page_reentry_result": "OBSERVED", "stop_casting_result": "OBSERVED", "center_display_normal": "OBSERVED",
    "restoration_result": "RESTORED_ON_RECORDING", "stale_crop_overlap_anomaly": "NONE_SEEN",
    "geometry": "GEOMETRY_NOT_TESTED", "session_status": "COMPLETED", "stop_reason": "NONE",
    "recording_duration_s": 420, "recording_legible": True, "event_timeline_preserved": True,
    "integrity_manifest_created": True, "owner_written_approval": True, "independent_safety_review": True,
    "operator_read_stop_procedure": True,
}


def rec(**changes):
    r = copy.deepcopy(COMPLETE_RECORD)
    r.update(changes)
    return r


@pytest.fixture
def private_root(tmp_path_factory):
    # tmp dirs are outside this repository, as the real private root must be
    root = tmp_path_factory.mktemp("obs02") / "CL-OBS-02" / "S1"
    ev.init_layout(root)
    return root


def test_layout_is_private_and_complete(private_root):
    for name in ev.SUBDIRS:
        d = private_root / name
        assert d.is_dir() and (d.stat().st_mode & 0o077) == 0
    assert (private_root / "private-observation-notes/manifest.template.json").is_file()


def test_init_refuses_a_root_inside_a_git_work_tree():
    with pytest.raises(ev.RecordError):
        ev.init_layout(REPO / "docs" / "obs02-should-never-exist")
    assert not (REPO / "docs" / "obs02-should-never-exist").exists()


def test_seal_verify_and_tamper_detection(private_root):
    raw = private_root / "original-recording" / "dummy.bin"
    raw.write_bytes(os.urandom(4096))
    entry = ev.seal(private_root, raw)
    assert re.fullmatch(r"[0-9a-f]{64}", entry["sha256"])
    assert ev.verify(private_root) == (True, "match")
    assert not os.access(raw, os.W_OK), "sealed original must be read-only"
    with pytest.raises(ev.RecordError):
        ev.seal(private_root, raw)  # no overwrite of the integrity manifest
    raw.chmod(0o600)
    raw.write_bytes(b"changed")
    assert ev.verify(private_root) == (False, "digest mismatch")
    raw.unlink()
    assert ev.verify(private_root) == (False, "raw recording missing")


def test_seal_requires_the_original_recording_folder(private_root, tmp_path):
    stray = tmp_path / "x.bin"
    stray.write_bytes(b"1")
    with pytest.raises(ev.RecordError):
        ev.seal(private_root, stray)


def test_public_safety_gate_rejects_media_files():
    for name in ("clip.mp4", "clip.mov"):
        violations = check_public_safety.scan_blob(f"docs/{name}", b"\x00\x00\x00\x18ftypmp42", {})
        assert any(v.rule == "PS001" for v in violations), name


def test_complete_session():
    assert ev.classify(rec(), True)[0] == ev.COMPLETE


# (scenario, record changes, integrity_ok, expected class) - mirrors the failure table in the acceptance doc
SCENARIOS = [
    ("camera failure before casting", dict(session_status="STOPPED_EARLY", stop_reason="CAMERA_FAILURE",
        casting_on_navigation="NOT_TESTED", page_exit_result="NOT_REACHED", page_reentry_result="NOT_REACHED",
        stop_casting_result="NOT_REACHED", restoration_result="NOT_CASTING_STARTED"), True, ev.ABORTED),
    ("camera failure while casting", dict(session_status="STOPPED_EARLY", stop_reason="CAMERA_FAILURE",
        page_exit_result="NOT_REACHED", page_reentry_result="NOT_REACHED", stop_casting_result="UNOBSERVABLE",
        restoration_result="RESTORED_DIRECT_SIGHT_ONLY"), True, ev.RESTORATION_UNVERIFIED),
    ("out of focus", dict(recording_legible=False, restoration_result="RESTORED_DIRECT_SIGHT_ONLY"),
        True, ev.RESTORATION_UNVERIFIED),
    ("out of focus before casting", dict(recording_legible=False, casting_on_navigation="NOT_TESTED",
        restoration_result="NOT_CASTING_STARTED"), True, ev.INCONCLUSIVE),
    ("missing event markers", dict(event_timeline_preserved=False), True, ev.INCONCLUSIVE),
    ("corrupt recording, casting started", dict(), False, ev.RESTORATION_UNVERIFIED),
    ("corrupt recording, casting not started", dict(casting_on_navigation="NOT_TESTED",
        restoration_result="NOT_CASTING_STARTED"), False, ev.INCONCLUSIVE),
    ("incomplete baseline", dict(baseline_recorded="NOT_OBSERVED", casting_on_navigation="NOT_TESTED",
        restoration_result="NOT_CASTING_STARTED"), True, ev.INCONCLUSIVE),
    ("missing restoration footage", dict(restoration_result="NOT_REACHED"), True, ev.RESTORATION_UNVERIFIED),
    ("geometry not available", dict(geometry="GEOMETRY_NOT_TESTED"), True, ev.COMPLETE),
    ("stopped early, restored", dict(session_status="STOPPED_EARLY", stop_reason="OPERATOR_UNCERTAINTY",
        page_exit_result="NOT_REACHED", page_reentry_result="NOT_REACHED"), True, ev.ABORTED),
    ("unexpected warning, restored", dict(session_status="STOPPED_EARLY", stop_reason="WARNING_OR_PROMPT",
        page_reentry_result="NOT_REACHED"), True, ev.ABORTED),
    ("unexpected warning, not restored", dict(session_status="STOPPED_EARLY", stop_reason="WARNING_OR_PROMPT",
        restoration_result="NOT_RESTORED_OBSERVED"), True, ev.RESTORATION_UNVERIFIED),
    ("casting visible on another page", dict(session_status="STOPPED_EARLY", stop_reason="CASTING_ON_OTHER_PAGE",
        page_reentry_result="NOT_REACHED"), True, ev.ABORTED),
    ("factory content not restored", dict(restoration_result="NOT_RESTORED_OBSERVED"), True, ev.RESTORATION_UNVERIFIED),
    ("re-entry not reached but session finished", dict(page_reentry_result="NOT_REACHED"), True, ev.PARTIAL),
    ("over the time limit", dict(recording_duration_s=601), True, ev.PARTIAL),
    ("no owner authorization", dict(owner_written_approval=False), True, ev.NOT_AUTHORIZED),
    ("no independent review", dict(independent_safety_review=False), True, ev.NOT_AUTHORIZED),
    ("stop procedure not read", dict(operator_read_stop_procedure=False), True, ev.NOT_AUTHORIZED),
]


@pytest.mark.parametrize("name,changes,integrity,expected", SCENARIOS, ids=[s[0] for s in SCENARIOS])
def test_failure_scenarios(name, changes, integrity, expected):
    assert ev.classify(rec(**changes), integrity)[0] == expected


def test_unauthorized_beats_everything_else():
    r = rec(owner_written_approval=False, restoration_result="NOT_RESTORED_OBSERVED")
    assert ev.classify(r, False)[0] == ev.NOT_AUTHORIZED


def test_invalid_records_are_rejected_not_guessed():
    bad = rec()
    del bad["geometry"]
    with pytest.raises(ev.RecordError):
        ev.classify(bad, True)
    with pytest.raises(ev.RecordError):
        ev.classify(rec(stop_reason="WHO_KNOWS"), True)
    with pytest.raises(ev.RecordError):
        ev.classify(rec(owner_written_approval="yes"), True)
    with pytest.raises(ev.RecordError):
        ev.classify(rec(recording_legible=False), True)  # cannot claim restoration on an illegible recording


def test_cli_end_to_end_with_dummy_media(private_root):
    raw = private_root / "original-recording" / "dummy.bin"
    raw.write_bytes(os.urandom(1024))
    import json
    (private_root / "private-observation-notes" / "observation.json").write_text(json.dumps(rec()))
    tool = str(REPO / "tools/cl_obs02_evidence.py")
    run = lambda *a: subprocess.run([sys.executable, "-I", tool, *a], capture_output=True, text=True)  # noqa: E731
    assert run("seal", "--root", str(private_root), "--raw", str(raw)).returncode == 0
    assert run("verify", "--root", str(private_root)).returncode == 0
    out = run("classify", "--root", str(private_root))
    assert out.stdout.splitlines()[0] == ev.COMPLETE


def test_tool_has_no_vehicle_or_network_access():
    src = (REPO / "tools/cl_obs02_evidence.py").read_text()
    for banned in ("adb", "socket", "urllib", "requests", "usb", "serial", "bluetooth"):
        assert not re.search(rf"\bimport\s+{banned}\b|\bfrom\s+{banned}\b", src), banned
    assert src.count("subprocess.run(") == 1 and '"git"' in src  # only the git work-tree probe


def test_documents_agree_with_tool_and_policy():
    packet, accept = PACKET.read_text(), ACCEPT.read_text()
    for field in ev.REQUIRED_FIELDS:
        assert f"`{field}`" in accept or field in {"recording_duration_s"} and "recording_duration_s" in accept, field
    for cls in (ev.COMPLETE, ev.PARTIAL, ev.INCONCLUSIVE, ev.ABORTED, ev.RESTORATION_UNVERIFIED, ev.NOT_AUTHORIZED):
        assert cls in accept, cls
    # every question maps to a field that the record validates
    rows = re.findall(r"^\| (Q[1-8]) \|.*\| `(\w+)`(?:, `\w+`)? \|$", packet, re.M)
    assert [q for q, _ in rows] == [f"Q{i}" for i in range(1, 9)]
    for _, field in rows:
        assert field in ev.REQUIRED_FIELDS, field
    for must in ("10 minutes", "safeForHonda() == false", "RECEIVER_AUTHORIZED_SPEC_REQUIRED",
                 "DISPLAY_SUPPORTED_PATH_NOT_FOUND", "VEHICLE_SESSION_NOT_AUTHORIZED", "GEOMETRY_NOT_TESTED",
                 "fc4623f9e0b7798f9f3f335f2ca4d5d448bdc799"):
        assert must in packet, must
    assert ev.MAX_RECORDING_SECONDS == 600
    # no private paths, identifiers or media in the public text
    for text in (packet, accept):
        assert "/Users/" not in text and not re.search(r"\b[A-HJ-NPR-Z0-9]{17}\b", text)


def test_relative_links_resolve():
    for doc in (PACKET, ACCEPT):
        for target in re.findall(r"\]\(([^)#:]+\.md)(?:#[^)]*)?\)", doc.read_text()):
            assert (doc.parent / target).resolve().exists(), (doc.name, target)
