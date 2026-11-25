from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import uuid

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools/honda-readonly-preflight"
sys.path.insert(0, str(TOOLS))

import root_access_v2 as v2


GOOD_META = {"file_type": "regular", "uid": 0, "gid": 0,
             "mode_octal": "0o6777", "size_bytes": v2.EXPECTED_SU_SIZE,
             "setuid": True, "setgid": True}
GOOD_MOUNT = {"complete": True, "read_only": True, "read_write": False,
              "overlay_uncertainty": []}
GOOD_PARENTS = {"/": (0, 0, 0o755), "/system": (0, 0, 0o755),
                "/system/xbin": (0, 0, 0o755)}


def assess(**changes):
    values = {"metadata": GOOD_META, "digest": v2.EXPECTED_SU_SHA256,
              "size": v2.EXPECTED_SU_SIZE, "mount": GOOD_MOUNT,
              "resolved_path": v2.EXPECTED_SU_PATH,
              "parent_modes": GOOD_PARENTS}
    values.update(changes)
    return v2.assess_legacy_su(**values)


def test_archived_06777_is_explicit_high_risk_candidate_only_on_ro_mount():
    result = assess()
    assert result["eligible"] is True
    assert result["observed_mode_octal"] == "0o6777"
    assert result["risk_severity"] == "HIGH_ACCEPTED_RESIDUAL"
    assert any("write bits to group and other" in item for item in result["risks"])
    assert "do not prove race-free" in result["integrity_limit"]


@pytest.mark.parametrize(("changes", "status"), [
    ({"mount": {"complete": True, "read_only": False, "read_write": True}},
     "REJECT_MOUNT_NOT_PROVEN_READ_ONLY"),
    ({"digest": "0" * 64}, "REJECT_EXECUTABLE_IDENTITY_MISMATCH"),
    ({"resolved_path": "/data/local/tmp/su"}, "REJECT_PATH_OR_SYMLINK_MISMATCH"),
    ({"metadata": {**GOOD_META, "uid": 2000}}, "REJECT_FILE_TYPE_OR_OWNER"),
    ({"metadata": {**GOOD_META, "mode_octal": "0o6755"}}, "REJECT_MODE_DIFFERS_FROM_ARCHIVE"),
    ({"parent_modes": {**GOOD_PARENTS, "/system/xbin": (0, 0, 0o777)}},
     "REJECT_UNPRIVILEGED_REPLACEMENT_POSSIBLE"),
    ({"mount": {"complete": True, "read_only": True, "overlay_uncertainty": ["bind"]}},
     "REJECT_MOUNT_NOT_PROVEN_READ_ONLY"),
])
def test_legacy_su_integrity_mismatches_fail_closed(changes, status):
    result = assess(**changes)
    assert result["eligible"] is False
    assert result["status"] == status


def test_fixed_root_command_builder_has_no_arbitrary_shell_or_path_surface():
    argv = v2.fixed_root_argv("192.0.2.4:5555", "process", pid=4321, leaf="maps")
    assert argv[-2:] == ("-c", "cat /proc/4321/maps")
    with pytest.raises(v2.V2Stop):
        v2.fixed_root_argv("auto", "identity")
    with pytest.raises(v2.V2Stop):
        v2.fixed_root_argv("SERIAL", "process", pid=4321, leaf="mem")
    with pytest.raises(v2.V2Stop):
        v2.fixed_root_argv("SERIAL", "network", table="/etc/passwd")
    assert v2.fixed_root_argv("SERIAL", "exe", pid=4321)[-2:] == (
        "-c", "ls -l /proc/4321/exe")
    with pytest.raises(v2.V2Stop):
        v2.fixed_root_argv("SERIAL", "shell", leaf="id")


def valid_authorization(endpoint="SERIAL-EXACT"):
    source_hash, profile_hash = v2.source_binding()
    return {"schema": v2.SCHEMA, "campaign": v2.CAMPAIGN,
            "endpoint": endpoint, "target_properties": v2.V2_TARGET_IDENTITY,
            "run_id": uuid.uuid4().hex, "risk_acceptance": v2.EXPECTED_ROOT_RISK,
            "scope": ["root_process_socket_metadata", "normal_stock_carplay_transitions"],
            "owner_approved": True, "parked": True, "parking_brake_set": True,
            "owner_present": True, "approved_power_state": True,
            "power_state": "PARKED_ON_READY_ABSENT",
            "factory_display_cluster_audio_normal": True,
            "source_lock_sha256": source_hash, "profile_sha256": profile_hash,
            "expires_utc": (datetime.now(timezone.utc) + timedelta(minutes=10)).isoformat()}


def test_authorization_binds_scope_endpoint_identity_risk_and_expiry():
    record = valid_authorization()
    source_hash, profile_hash = v2.source_binding()
    assert v2.validate_authorization(record, endpoint="SERIAL-EXACT",
                                     source_lock_sha256=source_hash,
                                     profile_sha256=profile_hash) == record
    for change in ({"risk_acceptance": "read-only intent"},
                   {"owner_approved": False}, {"parked": False},
                   {"endpoint": "OTHER"}, {"target_properties": {}},
                   {"scope": ["arbitrary shell"]}):
        changed = {**record, **change}
        with pytest.raises(v2.V2Stop):
            v2.validate_authorization(changed, endpoint="SERIAL-EXACT")
    expired = {**record, "expires_utc": (datetime.now(timezone.utc) - timedelta(seconds=1)).isoformat()}
    with pytest.raises(v2.V2Stop, match="expired"):
        v2.validate_authorization(expired, endpoint="SERIAL-EXACT")


def test_source_integrity_detects_modified_locked_input(tmp_path, monkeypatch):
    lock_hash, profile_hash = v2.source_binding()
    assert len(lock_hash) == len(profile_hash) == 64
    original_here = v2.HERE
    original_profile = v2.PROFILE_PATH
    original_lock = v2.SOURCE_LOCK_PATH
    for name in ("root_access_v2.py", "root_access_v2_profile.json", "collector.py",
                 "root_integrity_preflight.py", "parsers.py", "privileged.py",
                 "root_access_v2_source_lock.json"):
        (tmp_path / name).write_bytes((original_here / name).read_bytes())
    monkeypatch.setattr(v2, "HERE", tmp_path)
    monkeypatch.setattr(v2, "PROFILE_PATH", tmp_path / "profile.json")
    monkeypatch.setattr(v2, "SOURCE_LOCK_PATH", tmp_path / "lock.json")
    (tmp_path / "profile.json").write_bytes(original_profile.read_bytes())
    (tmp_path / "lock.json").write_bytes(original_lock.read_bytes())
    (tmp_path / "privileged.py").write_text("tampered")
    # A tampered source file does not match the reviewed lock digest.
    with pytest.raises(v2.V2Stop, match="integrity mismatch"):
        v2.source_binding()


def test_replayed_run_id_is_rejected_without_overwriting_ledger(tmp_path):
    parent = tmp_path / "private"
    parent.mkdir(mode=0o700)
    parent.chmod(0o700)
    run_id = "a" * 32
    ledger = parent / "consumed" / run_id
    v2.consume_run_id(run_id, ledger)
    assert ledger.read_text() == run_id + "\n"
    with pytest.raises(v2.V2Stop, match="replay"):
        v2.consume_run_id(run_id, ledger)
    assert ledger.read_text() == run_id + "\n"


def test_auth_file_requires_regular_0600_and_private_output_is_outside_git(tmp_path):
    auth_file = tmp_path / "auth.json"
    auth_file.write_text(json.dumps(valid_authorization()))
    auth_file.chmod(0o644)
    with pytest.raises(v2.V2Stop, match="0600"):
        v2._read_auth(auth_file, "SERIAL-EXACT")
    with pytest.raises(v2.V2Stop, match="outside Git"):
        v2._private_output(ROOT / "private-evidence")
    private_parent = tmp_path / "private-parent"
    private_parent.mkdir(mode=0o700); private_parent.chmod(0o700)
    output = v2._private_output(private_parent / "capture")
    assert output.stat().st_mode & 0o777 == 0o700


def test_generated_authorization_draft_is_private_and_never_authorizes(tmp_path):
    parent = tmp_path / "owner-only"
    parent.mkdir(mode=0o700); parent.chmod(0o700)
    path = v2.write_authorization_draft(parent / "approval.json", "192.0.2.2:5555")
    assert path.stat().st_mode & 0o777 == 0o600
    draft = json.loads(path.read_text())
    assert draft["owner_approved"] is False
    assert draft["parked"] is False
    assert draft["parking_brake_set"] is False
    assert draft["factory_display_cluster_audio_normal"] is False
    assert draft["risk_acceptance"] == ""
    with pytest.raises(v2.V2Stop):
        v2.validate_authorization(draft, endpoint="192.0.2.2:5555")


def test_timeout_and_output_limit_raise_stop_without_retry(monkeypatch, tmp_path):
    class FakeAdb:
        serial = "SERIAL"
        adb = "/usr/bin/adb"
        def plan(self, operation, args):
            return (self.adb, "-s", "SERIAL", "shell", operation, *args)
        def _run_planned(self, *args, **kwargs):
            raise v2.SafetyStop("timeout")
    session = object.__new__(v2.Session)
    session.endpoint = "SERIAL"; session.output = tmp_path
    session.started = __import__("time").monotonic()
    session.started_utc = datetime.now(timezone.utc).isoformat()
    session.commands = 0; session.used = 0; session.files = []; session.adb = FakeAdb()
    with pytest.raises(v2.SafetyStop, match="timeout"):
        session.call("baseline", "timeout", ("/usr/bin/adb", "-s", "SERIAL", "shell",
                                                "/system/xbin/su", "-c", "id"))


def test_elapsed_session_deadline_stops_before_any_adb_action(tmp_path):
    class NeverAdb:
        def run(self, *args, **kwargs):
            pytest.fail("expired session must stop before ADB")
    session = object.__new__(v2.Session)
    session.endpoint = "SERIAL"; session.output = tmp_path
    session.started = __import__("time").monotonic() - v2.MAX_SECONDS
    session.commands = 0; session.used = 0; session.adb = NeverAdb()
    with pytest.raises(v2.V2Stop, match="15-minute"):
        session._ordinary("property", "ro.product.model")


def test_runner_enforces_output_limit_and_abort_manifest_is_private(tmp_path):
    class FakeAdb:
        serial = "SERIAL"
        adb = "/usr/bin/adb"
        def plan(self, operation, args):
            if operation in {"hash-su", "ls-su-n", "read"}:
                return (self.adb, "-s", self.serial, "shell", "cat", *args)
            return (self.adb, "-s", self.serial, "shell", operation, *args)
        def _run_planned(self, *args, **kwargs):
            return 0, b"0123456789", b""
    session = object.__new__(v2.Session)
    session.endpoint = "SERIAL"; session.output = tmp_path
    session.started = __import__("time").monotonic()
    session.started_utc = datetime.now(timezone.utc).isoformat()
    session.commands = 0; session.used = 0; session.files = []; session.adb = FakeAdb()
    argv = ("/usr/bin/adb", "-s", "SERIAL", "shell", "/system/xbin/su", "-c", "id")
    with pytest.raises(v2.V2Stop, match="output bound"):
        session.call("baseline", "bounded", argv, maximum=5)
    session.finalize("f" * 32, "ABORTED_OUTPUT_LIMIT")
    manifest = json.loads((tmp_path / "manifest.json").read_text())
    assert manifest["stop_status"] == "ABORTED_OUTPUT_LIMIT"
    assert (tmp_path / "sha256.txt").stat().st_mode & 0o777 == 0o600


def test_session_refuses_arbitrary_shell_before_any_adb_call(tmp_path):
    class FakeAdb:
        serial = "SERIAL"
        adb = "/usr/bin/adb"
        def plan(self, operation, args):
            return (self.adb, "-s", "SERIAL", "shell", operation, *args)
        def _run_planned(self, *args, **kwargs):
            pytest.fail("ADB must not run for a non-manifest command")
    session = object.__new__(v2.Session)
    session.endpoint = "SERIAL"; session.output = tmp_path
    session.started = __import__("time").monotonic()
    session.commands = 0; session.used = 0; session.files = []; session.adb = FakeAdb()
    with pytest.raises(v2.V2Stop, match="outside the fixed V2"):
        session.call("baseline", "escape", ("/usr/bin/adb", "-s", "SERIAL", "shell",
                                              "/system/xbin/su", "-c", "rm -rf /"))


def test_root_hash_is_last_read_before_privileged_invocation(tmp_path):
    class FakeAdb:
        serial = "SERIAL"
        adb = "/usr/bin/adb"
        records = []
        def plan(self, operation, args):
            if operation == "hash-su":
                return (self.adb, "-s", self.serial, "shell", "sha256sum", "/system/xbin/su")
            if operation == "ls-su-n":
                return (self.adb, "-s", self.serial, "shell", "ls", "-n", "/system/xbin/su")
            if operation == "read":
                return (self.adb, "-s", self.serial, "shell", "cat", *args)
            return (self.adb, "-s", self.serial, "shell", operation, *args)
        def _run_planned(self, command, operation, args, *, timeout, max_bytes):
            self.records.append(command)
            if "sha256sum" in command:
                return 0, (v2.EXPECTED_SU_SHA256 + "  /system/xbin/su\n").encode(), b""
            return 0, b"uid=0(root) gid=0(root)\n", b""
    fake = FakeAdb()
    session = object.__new__(v2.Session)
    session.endpoint = "SERIAL"; session.output = tmp_path
    session.started = __import__("time").monotonic()
    session.commands = 0; session.used = 0; session.files = []; session.adb = fake
    result = session.root("phase", "identity", "identity")
    assert result.startswith(b"uid=0")
    assert fake.records[-2][-2:] == ("sha256sum", "/system/xbin/su")
    assert fake.records[-1][-2:] == ("-c", "id")


def test_archived_owner_identity_and_mode_are_kept_exact():
    assert v2.EXPECTED_SU_SHA256 == "d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26"
    assert v2.EXPECTED_SU_PATH == "/system/xbin/su"
    assert GOOD_META["mode_octal"] == "0o6777"
    assert v2.parse_su_digest((v2.EXPECTED_SU_SHA256 + "  /system/xbin/su\n").encode()) == v2.EXPECTED_SU_SHA256
    with pytest.raises(v2.V2Stop):
        v2.parse_su_digest((v2.EXPECTED_SU_SHA256 + "  /data/local/tmp/su\n").encode())


def test_su_path_chain_rejects_symlinks_and_wrong_names():
    rows = (b"drwxr-xr-x 0 0 4096 2026-11-25 00:00 /\n"
            b"drwxr-xr-x 0 0 4096 2026-11-25 00:00 /system\n"
            b"drwxr-xr-x 0 0 4096 2026-11-25 00:00 /system/xbin\n"
            b"-rwsrwsrwx 0 0 75348 2026-11-25 00:00 /system/xbin/su\n")
    parsed = v2.parse_su_path_chain(rows)
    assert parsed["/system/xbin/su"][2] & 0o022 == 0o022
    with pytest.raises(v2.V2Stop, match="symlink"):
        v2.parse_su_path_chain(rows.replace(
            b"-rwsrwsrwx 0 0 75348 2026-11-25 00:00 /system/xbin/su",
            b"lrwxrwxrwx 0 0 12 2026-11-25 00:00 /system/xbin/su -> /data/su"))
    with pytest.raises(v2.V2Stop):
        v2.parse_su_path_chain(rows.replace(b"/system/xbin/su\n", b"/data/replacement\n"))


def test_jmcs_executable_link_parser_requires_exact_stock_path():
    assert v2.parse_ls_symlink_target(b"lrwxrwxrwx root root 0 /proc/321/exe -> /system/bin/jmcs\n") == "/system/bin/jmcs"
    assert v2.parse_ls_symlink_target(b"lrwxrwxrwx root root 0 /proc/321/exe -> /data/local/tmp/jmcs\n") != "/system/bin/jmcs"


def test_process_status_must_bind_all_uid_and_gid_slots_to_root():
    good = "Uid:\t0\t0\t0\t0\nGid:\t0\t0\t0\t0\n"
    assert __import__("re").search(r"(?m)^Uid:\s*0\s+0\s+0\s+0$", good)
    bad = good.replace("Gid:\t0\t0\t0\t0", "Gid:\t0\t0\t2000\t2000")
    assert not __import__("re").search(r"(?m)^Gid:\s*0\s+0\s+0\s+0$", bad)
