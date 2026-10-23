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


# steps after casting cannot have been observed when casting never started
NO_CASTING = dict(casting_on_navigation="NOT_TESTED", restoration_result="NOT_CASTING_STARTED",
                  page_exit_result="NOT_REACHED", page_reentry_result="NOT_REACHED", stop_casting_result="NOT_REACHED")


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
    ("out of focus before casting", dict(NO_CASTING, recording_legible=False), True, ev.INCONCLUSIVE),
    ("missing event markers", dict(event_timeline_preserved=False), True, ev.INCONCLUSIVE),
    ("corrupt recording, casting started", dict(), False, ev.RESTORATION_UNVERIFIED),
    ("corrupt recording, casting not started", dict(NO_CASTING), False, ev.INCONCLUSIVE),
    ("incomplete baseline", dict(NO_CASTING, baseline_recorded="NOT_OBSERVED"), True, ev.INCONCLUSIVE),
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


# ---- hardening regressions (ECC findings on the first preflight commit) ----

def _git_repo(tmp_path):
    repo = tmp_path / "somerepo"
    repo.mkdir()
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    return repo


def test_init_refuses_nonexistent_dir_inside_a_git_work_tree(tmp_path):
    repo = _git_repo(tmp_path)
    target = repo / "a" / "b" / "S1"
    with pytest.raises(ev.RecordError):
        ev.init_layout(target)
    assert not (repo / "a").exists()


def test_init_refuses_symlink_into_a_git_work_tree(tmp_path):
    repo = _git_repo(tmp_path)
    link = tmp_path / "link"
    link.symlink_to(repo)
    with pytest.raises(ev.RecordError):
        ev.init_layout(link / "S1")
    assert not (repo / "S1").exists()


def test_init_refuses_subdir_symlinked_into_a_git_work_tree(tmp_path):
    repo = _git_repo(tmp_path)
    root = tmp_path / "CL-OBS-02" / "S1"
    root.mkdir(parents=True)
    (root / "original-recording").symlink_to(repo)
    with pytest.raises(ev.RecordError):
        ev.init_layout(root)


@pytest.mark.parametrize("mode", ["nonzero", "missing_git", "timeout", "garbage"])
def test_git_guard_fails_closed_on_probe_errors(tmp_path, monkeypatch, mode):
    def fake_run(*args, **kwargs):
        if mode == "missing_git":
            raise FileNotFoundError("git")
        if mode == "timeout":
            raise subprocess.TimeoutExpired("git", 1)
        if mode == "nonzero":
            return subprocess.CompletedProcess(args, 1, "", "fatal: detected dubious ownership")
        return subprocess.CompletedProcess(args, 0, "maybe\n", "")
    monkeypatch.setattr(ev.subprocess, "run", fake_run)
    with pytest.raises(ev.RecordError):
        ev.init_layout(tmp_path / "CL-OBS-02" / "S1")
    assert not (tmp_path / "CL-OBS-02").exists()


def test_git_guard_accepts_a_genuine_non_repository(tmp_path):
    root = tmp_path / "deep" / "CL-OBS-02" / "S1"
    assert ev.init_layout(root) == list(ev.SUBDIRS)


def test_init_rejects_malformed_paths(tmp_path):
    with pytest.raises((ev.RecordError, ValueError)):
        ev.init_layout(Path(str(tmp_path / "bad\0path")))
    assert ev.main(["init", "--root", str(tmp_path / "bad\0path")]) == 2


def test_init_on_existing_private_root_preserves_contents(private_root):
    raw = private_root / "original-recording" / "keep.bin"
    raw.write_bytes(b"original")
    template = private_root / "private-observation-notes" / "manifest.template.json"
    template.write_text("operator edited")
    ev.init_layout(private_root)
    assert raw.read_bytes() == b"original"
    assert template.read_text() == "operator edited"


@pytest.mark.parametrize("changes", [
    dict(casting_on_navigation="NOT_TESTED"),                              # restored, yet casting never tested
    dict(restoration_result="NOT_CASTING_STARTED"),                        # casting observed, yet "not started"
    dict(casting_on_navigation="NOT_TESTED", restoration_result="RESTORED_ON_RECORDING"),
    dict(casting_on_navigation="NOT_OBSERVED", restoration_result="NOT_CASTING_STARTED"),
    dict(session_status="COMPLETED", stop_reason="WARNING_OR_PROMPT"),
    dict(session_status="STOPPED_EARLY", stop_reason="NONE"),
    dict(stop_casting_result="NOT_REACHED"),                               # restored on recording, stop never reached
    dict(center_display_normal="UNOBSERVABLE"),
    dict(recording_duration_s=0.5, restoration_result="RESTORED_ON_RECORDING", recording_legible=False),
])
def test_contradictory_fields_are_rejected(changes):
    with pytest.raises(ev.RecordError):
        ev.classify(rec(**changes), True)


def test_missing_restoration_evidence_never_completes():
    for result in ("NOT_REACHED", "RESTORED_DIRECT_SIGHT_ONLY", "NOT_RESTORED_OBSERVED"):
        for integrity in (True, False):
            label = ev.classify(rec(restoration_result=result), integrity)[0]
            assert label == ev.RESTORATION_UNVERIFIED, (result, integrity)


def test_aborted_and_restoration_unverified_are_preserved():
    cam = dict(session_status="STOPPED_EARLY", stop_reason="CAMERA_FAILURE")
    assert ev.classify(rec(**cam, page_exit_result="NOT_REACHED", page_reentry_result="NOT_REACHED"),
                       True)[0] == ev.ABORTED
    assert ev.classify(rec(**cam, restoration_result="RESTORED_DIRECT_SIGHT_ONLY"), True)[0] == ev.RESTORATION_UNVERIFIED


@pytest.mark.parametrize("bad", [float("nan"), float("inf"), float("-inf"), -1, 10 ** 400, 86401, "420", None, True, [1]])
def test_bad_durations_are_rejected(bad):
    with pytest.raises(ev.RecordError):
        ev.classify(rec(recording_duration_s=bad), True)


def test_zero_duration_cannot_complete():
    assert ev.classify(rec(recording_duration_s=0), True)[0] == ev.INCONCLUSIVE


def test_nonfinite_json_literals_are_rejected(private_root):
    notes = private_root / "private-observation-notes" / "observation.json"
    import json
    notes.write_text(json.dumps(rec()).replace('"recording_duration_s": 420', '"recording_duration_s": NaN'))
    assert "NaN" in notes.read_text()
    assert ev.main(["classify", "--root", str(private_root)]) == 2


@pytest.mark.parametrize("bad", [None, [], "x", 3, [{"a": 1}]])
def test_non_object_record_is_rejected(bad):
    with pytest.raises(ev.RecordError):
        ev.classify(bad, True)


@pytest.mark.parametrize("field,value", [
    ("geometry", ["MEASURED_SAMPLE"]), ("stop_reason", {"a": 1}), ("baseline_recorded", None),
    ("session_status", 5), ("owner_written_approval", 1), ("restoration_result", ["x"]),
])
def test_unhashable_or_mistyped_values_raise_record_error_not_typeerror(field, value):
    with pytest.raises(ev.RecordError):
        ev.classify(rec(**{field: value}), True)


def test_unexpected_extra_fields_are_rejected():
    with pytest.raises(ev.RecordError):
        ev.classify(rec(surprise="x"), True)


@pytest.mark.parametrize("payload", ["[]", "null", '"s"', "{", '{"file": 3, "sha256": "x"}',
                                     '{"file": "../x", "sha256": "ab"}', '{"file": "a/b", "sha256": "ab"}',
                                     '{"file": "/etc/hosts", "sha256": "ab"}', '{"file": "", "sha256": "ab"}',
                                     '{"file": "x", "sha256": 7}', '{"file": "x"}',
                                     '{"file": "x", "sha256": "ab"}', '{"file": "x", "sha256": "ab", "bytes": 0}',
                                     '{"file": "x", "sha256": "ab", "bytes": true}'])
def test_unsafe_or_malformed_integrity_manifest_fails_verify(private_root, payload):
    (private_root / "integrity-manifest" / "raw-sha256.json").write_text(payload)
    ok, msg = ev.verify(private_root)
    assert ok is False and msg


def test_verify_does_not_follow_manifest_path_outside_recording_dir(private_root, tmp_path):
    outside = tmp_path / "outside.bin"
    outside.write_bytes(b"x")
    (private_root / "original-recording" / "ln").symlink_to(outside)
    import json
    (private_root / "integrity-manifest" / "raw-sha256.json").write_text(
        json.dumps({"file": "ln", "sha256": ev.sha256_file(outside)}))
    assert ev.verify(private_root)[0] is False


def test_seal_is_atomic_when_chmod_fails(private_root, monkeypatch):
    raw = private_root / "original-recording" / "d.bin"
    raw.write_bytes(b"data")
    monkeypatch.setattr(ev.os, "chmod", lambda *a, **k: (_ for _ in ()).throw(PermissionError("no")))
    with pytest.raises(OSError):
        ev.seal(private_root, raw)
    assert not (private_root / "integrity-manifest" / "raw-sha256.json").exists()
    assert not list((private_root / "integrity-manifest").iterdir())


def test_seal_never_overwrites_an_existing_manifest(private_root):
    raw = private_root / "original-recording" / "d.bin"
    raw.write_bytes(b"data")
    mf = private_root / "integrity-manifest" / "raw-sha256.json"
    mf.write_text("precious")
    with pytest.raises(ev.RecordError):
        ev.seal(private_root, raw)
    assert mf.read_text() == "precious"


def test_cli_returns_2_not_a_traceback_on_malformed_input(private_root):
    notes = private_root / "private-observation-notes" / "observation.json"
    tool = str(REPO / "tools/cl_obs02_evidence.py")
    for body in ("[]", "{" , '{"geometry": ["x"]}', "[" * 100000):
        notes.write_text(body)
        out = subprocess.run([sys.executable, "-I", tool, "classify", "--root", str(private_root)],
                             capture_output=True, text=True)
        assert out.returncode == 2 and "Traceback" not in out.stderr, body[:20]


def test_seal_rollback_never_deletes_a_manifest_it_did_not_create(private_root, monkeypatch):
    raw = private_root / "original-recording" / "d.bin"
    raw.write_bytes(b"data")
    mf = private_root / "integrity-manifest" / "raw-sha256.json"
    real_link = os.link

    def racing_link(src, dst, *a, **k):
        Path(dst).write_text("OTHER")             # another sealer wins the race
        return real_link(src, dst, *a, **k)
    monkeypatch.setattr(ev.os, "link", racing_link)
    with pytest.raises(FileExistsError):
        ev.seal(private_root, raw)
    assert mf.read_text() == "OTHER"
    assert os.access(raw, os.W_OK), "raw must be untouched when sealing never published"


def test_seal_restores_raw_mode_when_post_publish_check_fails(private_root, monkeypatch):
    raw = private_root / "original-recording" / "d.bin"
    raw.write_bytes(b"data")
    raw.chmod(0o640)
    digests = iter(["a" * 64, "b" * 64])
    monkeypatch.setattr(ev, "sha256_file", lambda p: next(digests))
    with pytest.raises(ev.RecordError):
        ev.seal(private_root, raw)
    assert not (private_root / "integrity-manifest" / "raw-sha256.json").exists()
    assert (raw.stat().st_mode & 0o777) == 0o640
    assert not list((private_root / "integrity-manifest").iterdir())


def test_duplicate_json_keys_are_rejected(private_root):
    notes = private_root / "private-observation-notes" / "observation.json"
    import json
    body = json.dumps(rec())[:-1] + ', "geometry": "MEASURED_SAMPLE"}'
    notes.write_text(body)
    assert ev.main(["classify", "--root", str(private_root)]) == 2


def test_stop_before_casting_step_reached_is_aborted():
    r = rec(session_status="STOPPED_EARLY", stop_reason="CAMERA_FAILURE", casting_on_navigation="NOT_REACHED",
            restoration_result="NOT_CASTING_STARTED", page_exit_result="NOT_REACHED",
            page_reentry_result="NOT_REACHED", stop_casting_result="NOT_REACHED")
    assert ev.classify(r, True)[0] == ev.ABORTED
    with pytest.raises(ev.RecordError):    # casting NOT_REACHED but a restoration outcome claimed
        ev.classify(rec(casting_on_navigation="NOT_REACHED"), True)


def test_duration_boundaries():
    assert ev.classify(rec(recording_duration_s=600), True)[0] == ev.COMPLETE
    assert ev.classify(rec(recording_duration_s=601), True)[0] == ev.PARTIAL
    assert ev.classify(rec(recording_duration_s=ev.MAX_PLAUSIBLE_RECORDING_SECONDS), True)[0] == ev.PARTIAL
    with pytest.raises(ev.RecordError):
        ev.classify(rec(recording_duration_s=ev.MAX_PLAUSIBLE_RECORDING_SECONDS + 1), True)
    assert str(ev.MAX_PLAUSIBLE_RECORDING_SECONDS) in ACCEPT.read_text()


def test_seal_rejects_empty_recording_and_makes_manifest_read_only(private_root):
    raw = private_root / "original-recording" / "empty.bin"
    raw.write_bytes(b"")
    with pytest.raises(ev.RecordError):
        ev.seal(private_root, raw)
    raw.write_bytes(b"x")
    ev.seal(private_root, raw)
    mf = private_root / "integrity-manifest" / "raw-sha256.json"
    assert (mf.stat().st_mode & 0o777) == 0o400


def test_verify_detects_size_mismatch_and_symlinked_manifest(private_root, tmp_path):
    import json
    raw = private_root / "original-recording" / "d.bin"
    raw.write_bytes(b"data")
    mf = private_root / "integrity-manifest" / "raw-sha256.json"
    mf.write_text(json.dumps({"file": "d.bin", "sha256": ev.sha256_file(raw), "bytes": 99}))
    assert ev.verify(private_root) == (False, "size mismatch")
    real = tmp_path / "real.json"
    real.write_text(mf.read_text())
    mf.unlink()
    mf.symlink_to(real)
    assert ev.verify(private_root)[0] is False


def test_seal_refuses_symlinked_layout_dir_and_git_tree(tmp_path):
    repo = _git_repo(tmp_path)
    root = tmp_path / "CL-OBS-02" / "S1"
    ev.init_layout(root)
    (root / "original-recording").rmdir()
    (root / "original-recording").symlink_to(repo)
    raw = repo / "x.bin"
    raw.write_bytes(b"x")
    with pytest.raises(ev.RecordError):
        ev.seal(root, raw)
    assert not list((root / "integrity-manifest").iterdir())
    with pytest.raises(ev.RecordError):
        ev.seal(repo / "S1", raw)          # a root inside a work tree


def test_init_does_not_follow_a_symlinked_template_or_chmod_existing_root(tmp_path):
    root = tmp_path / "CL-OBS-02" / "S1"
    root.mkdir(parents=True)
    root.chmod(0o750)
    ev.init_layout(root)
    assert (root.stat().st_mode & 0o777) == 0o750
    tpl = root / "private-observation-notes" / "manifest.template.json"
    tpl.unlink()
    victim = tmp_path / "victim.txt"
    tpl.symlink_to(victim)
    with pytest.raises(ev.RecordError):
        ev.init_layout(root)
    assert not victim.exists()
