from datetime import datetime, timedelta, timezone
import json
import hashlib
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


def test_generated_authorization_draft_is_private_nonexpiring_and_never_authorizes(tmp_path):
    parent = tmp_path / "owner-only"
    parent.mkdir(mode=0o700); parent.chmod(0o700)
    path = v2.write_authorization_draft(parent / "approval.json", None)
    assert path.stat().st_mode & 0o777 == 0o600
    draft = json.loads(path.read_text())
    assert draft["owner_approved"] is False
    assert draft["parked"] is False
    assert draft["parking_brake_set"] is False
    assert draft["factory_display_cluster_audio_normal"] is False
    assert draft["risk_acceptance"] == ""
    assert draft["endpoint"] == "OWNER_FILL_EXACT_ALREADY_AUTHORIZED_ENDPOINT"
    assert draft["power_state"] == ""
    assert draft["expires_utc"] is None
    with pytest.raises(v2.V2Stop):
        v2.validate_authorization(draft, endpoint="OWNER_FILL_EXACT_ALREADY_AUTHORIZED_ENDPOINT")


def test_v21_profile_explicitly_pins_141_command_budget():
    profile = json.loads(v2.PROFILE_PATH.read_text())
    assert profile["revision"] == "2.1"
    assert profile["limits"]["commands"] == v2.MAX_COMMANDS == 141
    assert profile["limits"]["command_budget_basis"] == (
        "exact three-phase total: 24 identity + 16 su assessment + "
        "86 root/digest + 15 display/network = 141")


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
    rows = (b"drwxr-xr-x 0 0 4096 2026-11-25 00:00 \n"
            b"drwxr-xr-x 0 0 4096 2026-11-25 00:00 system\n"
            b"drwxr-xr-x 0 0 4096 2026-11-25 00:00 xbin\n"
            b"-rwsrwsrwx 0 0 75348 2026-11-25 00:00 su\n")
    parsed = v2.parse_su_path_chain(rows)
    assert parsed["/system/xbin/su"][2] & 0o022 == 0o022
    with pytest.raises(v2.V2Stop, match="symlink"):
        v2.parse_su_path_chain(rows.replace(
            b"-rwsrwsrwx 0 0 75348 2026-11-25 00:00 su",
            b"lrwxrwxrwx 0 0 2026-11-25 00:00 su -> /data/su"))
    with pytest.raises(v2.SafetyStop):
        v2.parse_su_path_chain(rows.replace(
            b"-rwsrwsrwx 0 0 75348 2026-11-25 00:00 su",
            b"-rwsrwsrwx 0 0 75348 2026-11-25 00:00 replacement"))


def test_jmcs_executable_link_parser_requires_exact_stock_path():
    assert v2.parse_ls_symlink_target(b"lrwxrwxrwx root root 0 /proc/321/exe -> /system/bin/jmcs\n") == "/system/bin/jmcs"
    assert v2.parse_ls_symlink_target(b"lrwxrwxrwx root root 0 /proc/321/exe -> /data/local/tmp/jmcs\n") != "/system/bin/jmcs"


def test_process_status_must_bind_all_uid_and_gid_slots_to_root():
    good = "Uid:\t0\t0\t0\t0\nGid:\t0\t0\t0\t0\n"
    assert __import__("re").search(r"(?m)^Uid:\s*0\s+0\s+0\s+0$", good)
    bad = good.replace("Gid:\t0\t0\t0\t0", "Gid:\t0\t0\t2000\t2000")
    assert not __import__("re").search(r"(?m)^Gid:\s*0\s+0\s+0\s+0$", bad)


class FullFakeAdb:
    """Complete host-side ADB double; never calls subprocess or real adb."""

    def __init__(self, *, failure=None, bad_identity_at=None, su_identity="root",
                 malformed_su=False, changing_su_digest=False):
        self.serial = "192.0.2.22:5555"
        self.adb = "/synthetic/adb-never-executed"
        self.failure = failure
        self.bad_identity_at = bad_identity_at
        self.su_identity = su_identity
        self.malformed_su = malformed_su
        self.changing_su_digest = changing_su_digest
        self.records = []
        self.property_count = 0
        self.su_digest_count = 0

    def plan(self, operation, args):
        if operation == "property":
            remote = ("getprop", *args)
        elif operation == "read":
            remote = ("cat", *args)
        elif operation == "hash-su":
            remote = ("sha256sum", "/system/xbin/su")
        elif operation == "ls-su-n":
            remote = ("ls", "-n", "/system/xbin/su")
        elif operation == "dumpsys":
            remote = ("dumpsys", *args)
        else:
            pytest.fail(f"unexpected fake ordinary operation: {operation} {args}")
        return (self.adb, "-s", self.serial, "shell", *remote)

    def run(self, operation, *args, timeout=5, max_bytes=128 * 1024):
        argv = self.plan(operation, args)
        return self._respond(argv, operation)

    def _run_planned(self, command, operation, args, *, timeout, max_bytes):
        assert command[0] == self.adb, "runner escaped to a real ADB executable"
        assert command[1:4] == ("-s", self.serial, "shell")
        return self._respond(command, operation)

    def _respond(self, command, operation):
        remote = command[4:]
        self.records.append((operation, remote))
        if self.failure == "timeout" and len(self.records) == 56:
            return 124, b"", b"collector: command timed out"
        if self.failure == "transport" and len(self.records) == 56:
            return 1, b"", b"error: device offline"
        if operation == "property":
            self.property_count += 1
            prop = remote[-1]
            if self.bad_identity_at == self.property_count:
                return 0, b"wrong-target\n", b""
            return 0, (v2.V2_TARGET_IDENTITY[prop] + "\n").encode(), b""
        if operation == "read":
            return 0, b"/dev/root / ext4 rw 0 0\n/dev/system /system ext4 ro 0 0\n", b""
        if operation == "ls-su-n":
            if self.malformed_su:
                return 0, b"-rwsrwsrwx 1 root root mystery su\n", b""
            return 0, b"-rwsrwsrwx 0 0 75348 2026-11-25 12:00 su\n", b""
        if remote[:2] == ("sha256sum", "/system/xbin/su"):
            self.su_digest_count += 1
            digest = v2.EXPECTED_SU_SHA256
            if self.changing_su_digest and self.su_digest_count == 2:
                digest = "0" * 64
            return 0, f"{digest}  /system/xbin/su\n".encode(), b""
        if remote[:3] == ("ls", "-ldn", "/"):
            return 0, (
                b"drwxr-xr-x 0 0 4096 2026-11-25 12:00 \n"
                b"drwxr-xr-x 0 0 4096 2026-11-25 12:00 system\n"
                b"drwxr-xr-x 0 0 4096 2026-11-25 12:00 xbin\n"
                b"-rwsrwsrwx 0 0 75348 2026-11-25 12:00 su\n"), b""
        if remote[:1] == ("dumpsys",):
            service = " ".join(remote[1:])
            return 0, f"synthetic {service}: Display 1 HondaExternalDisplayHost\n".encode(), b""
        if remote == ("cat", "/proc/net/dev"):
            return 0, b"Inter-| Receive | Transmit\n lo: 0 0 0 0 0 0 0 0 0 0\n", b""
        if remote[:2] != ("/system/xbin/su", "-c"):
            pytest.fail(f"unapproved remote command reached fake: {remote!r}")
        command_text = remote[2]
        if command_text == "id":
            uid = "2000" if self.su_identity == "shell" else "0"
            return 0, f"uid={uid}({self.su_identity}) gid=0({self.su_identity})\n".encode(), b""
        if command_text == "ps":
            return 0, b"USER PID PPID VSIZE RSS WCHAN PC NAME\nroot 42 1 100 80 ffffffff 0 S /system/bin/jmcs\n", b""
        if command_text == "cat /proc/42/stat":
            tail = ["S"] + ["0"] * 19
            tail[19] = "98765"
            return 0, ("42 (jmcs) " + " ".join(tail) + "\n").encode(), b""
        if command_text == "cat /proc/42/status":
            return 0, b"Name:\tjmcs\nUid:\t0\t0\t0\t0\nGid:\t0\t0\t0\t0\n", b""
        if command_text == "cat /proc/42/cmdline":
            return 0, b"/system/bin/jmcs\0", b""
        if command_text == "ls -l /proc/42/exe":
            return 0, b"lrwxrwxrwx 1 root root 18 Nov 25 12:00 /proc/42/exe -> /system/bin/jmcs\n", b""
        if command_text == "cat /proc/42/maps":
            return 0, b"1000-2000 r-xp 0 00:00 0 /system/bin/jmcs\n", b""
        if command_text == "ls -l /proc/42/fd":
            return 0, (b"lrwx------ 1 root root 64 Nov 25 12:00 3 -> socket:[12345]\n"), b""
        if command_text.startswith("cat /proc/net/"):
            table = command_text.rsplit("/", 1)[-1]
            if table == "unix":
                return 0, b"Num RefCount Protocol Flags Type St Inode Path\n0000: 2 0 1 0001 01 12345\n", b""
            header = b"sl local_address rem_address st tx_queue rx_queue tr tm->when retrnsmt uid timeout inode\n"
            row = b"0: 00000000:0000 00000000:0000 01 0:0 00:00000000 0 0 0 12345\n"
            return 0, header + row, b""
        pytest.fail(f"unapproved su command reached fake: {command_text!r}")


def _run_full_fake_campaign(tmp_path, monkeypatch, *, inputs=("YES", "READY", "READY", "READY"),
                            fake=None, source_binding_override=None):
    fake = fake or FullFakeAdb()
    private = tmp_path / "private"
    private.mkdir(mode=0o700); private.chmod(0o700)
    auth_path = private / "authorization.json"
    auth = valid_authorization(endpoint=fake.serial)
    auth_path.write_text(json.dumps(auth)); auth_path.chmod(0o600)
    evidence_parent = private / "evidence"
    evidence_parent.mkdir(mode=0o700); evidence_parent.chmod(0o700)
    monkeypatch.setattr(v2, "FixedAdb", lambda serial, resolve_auto=False: fake)
    monkeypatch.setattr(v2.Path, "home", classmethod(lambda cls: tmp_path / "home"))
    answers = iter(inputs)
    monkeypatch.setattr("builtins.input", lambda *_args: next(answers))
    if source_binding_override is not None:
        monkeypatch.setattr(v2, "source_binding", source_binding_override)
    result = v2.main(["--serial", fake.serial, "--authorization", str(auth_path),
                      "--output", str(evidence_parent / "capture")])
    return result, fake, evidence_parent / "capture"


def test_full_three_phase_runner_fake_adb_completes_and_authenticates_evidence(tmp_path, monkeypatch):
    result, fake, output = _run_full_fake_campaign(tmp_path, monkeypatch)
    assert result == 0
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["stop_status"] == "COMPLETE_FIXED_DIAGNOSTIC"
    assert manifest["commands"] == v2.MAX_COMMANDS == 141
    assert manifest["output_bytes"] < v2.MAX_OUTPUT
    assert manifest["endpoint"] == fake.serial
    assert fake.su_digest_count == 47  # four integrity assessments plus 43 immediate pre-su pins
    assert len(fake.records) == 141
    assert sum(1 for _name, remote in fake.records
               if remote[:2] == ("/system/xbin/su", "-c")) == 43
    expected_phases = ("disconnected_baseline", "normal_stock_carplay_connected",
                       "normal_post_disconnect")
    for phase in expected_phases:
        correlation = json.loads((output / phase / "jmcs_socket_inode_correlation.raw").read_text())
        assert correlation["process_pid"] == 42
        assert correlation["fd_socket_pairs"] == [{"fd": 3, "inode": 12345}]
        assert all(correlation["matched_proc_net_rows"][table] for table in v2.NETWORK_TABLES)
        assert (output / phase / "dumpsys_activity_services.raw").exists()
    hashes = {}
    for line in (output / "sha256.txt").read_text().splitlines():
        digest, rel = line.split("  ", 1)
        hashes[rel] = digest
    for artifact in hashes:
        assert hashlib.sha256((output / artifact).read_bytes()).hexdigest() == hashes[artifact]
    assert hashlib.sha256((output / "manifest.json").read_bytes()).hexdigest() == hashes["manifest.json"]
    assert all(record[0] != "adb-devices" for record in fake.records)


@pytest.mark.parametrize(("case", "expected"), [
    ("transport", "ABORTED_V2Stop"),
    ("timeout", "ABORTED_V2Stop"),
    ("permission", "ABORTED_V2Stop"),
    ("malformed", "ABORTED_SafetyStop"),
    ("digest", "ABORTED_V2Stop"),
    ("identity_drift", "ABORTED_V2Stop"),
    ("cancel", "ABORTED_V2Stop"),
])
def test_full_runner_failures_preserve_abort_manifest_and_never_retry(
        tmp_path, monkeypatch, case, expected):
    if case == "permission":
        fake = FullFakeAdb(su_identity="shell")
        inputs = ("YES", "READY", "READY", "READY")
    elif case == "malformed":
        fake = FullFakeAdb(malformed_su=True)
        inputs = ("YES", "READY", "READY", "READY")
    elif case == "digest":
        fake = FullFakeAdb(changing_su_digest=True)
        inputs = ("YES", "READY", "READY", "READY")
    elif case == "identity_drift":
        fake = FullFakeAdb(bad_identity_at=13)
        inputs = ("YES", "READY", "READY", "READY")
    elif case == "cancel":
        fake = FullFakeAdb()
        inputs = ("YES", "READY", "NO")
    else:
        fake = FullFakeAdb(failure=case)
        inputs = ("YES", "READY", "READY", "READY")
    result, fake, output = _run_full_fake_campaign(
        tmp_path, monkeypatch, inputs=inputs, fake=fake)
    assert result == 1
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["stop_status"] == expected
    assert manifest["commands"] == len(fake.records)
    if case == "timeout":
        assert "timed out" in manifest["stop_reason"]
    assert not any(record[0] in {"retry", "fallback", "adb devices"} for record in fake.records)


def test_full_runner_detects_source_change_at_phase_boundary_before_next_adb(
        tmp_path, monkeypatch, capsys):
    fake = FullFakeAdb()
    actual_binding = v2.source_binding
    def source_binding():
        if len(fake.records) >= 55:
            return "0" * 64, "1" * 64
        return actual_binding()
    result, fake, output = _run_full_fake_campaign(
        tmp_path, monkeypatch, fake=fake, source_binding_override=source_binding)
    assert result == 1
    manifest = json.loads((output / "manifest.json").read_text())
    assert manifest["stop_status"] == "ABORTED_V2Stop"
    assert "source/profile changed" in manifest["stop_reason"]
    assert manifest["commands"] == 55
    assert len(fake.records) == 55
