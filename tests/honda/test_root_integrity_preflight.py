import sys
import json
from pathlib import Path
import stat

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools/honda-readonly-preflight"))

import collector
import root_integrity_preflight as preflight
from privileged import EXPECTED_SU_SHA256


def test_api17_fixed_ls_and_hash_forms_are_unprivileged_and_literal(monkeypatch, tmp_path):
    monkeypatch.setattr(collector.shutil, "which", lambda _: "/usr/bin/adb")
    adb = collector.FixedAdb("AUTHORIZED-ENDPOINT", resolve_auto=False)
    assert adb.plan("host-devices", ()) == ("/usr/bin/adb", "devices", "-l")
    assert adb.plan("ls-su-n", ()) == (
        "/usr/bin/adb", "-s", "AUTHORIZED-ENDPOINT", "shell", "ls", "-n", "/system/xbin/su")
    assert adb.plan("hash-su", ()) == (
        "/usr/bin/adb", "-s", "AUTHORIZED-ENDPOINT", "shell", "sha256sum", "/system/xbin/su")
    capture = collector.Capture(adb, tmp_path)
    calls = []
    monkeypatch.setattr(adb, "_run_planned", lambda command, *args, **kwargs:
                        (calls.append(command) or (0, b"-rwsr-sr-x 0 0 75348 2026-09-25 12:00 su\n", b"")))
    assert preflight.read_numeric_su_metadata(adb, capture)[0] == 0
    assert calls == [("/usr/bin/adb", "-s", "AUTHORIZED-ENDPOINT", "shell", "ls", "-n",
                      "/system/xbin/su")]
    assert "-c" not in calls[0]
    assert "chmod" not in calls[0] and "chown" not in calls[0]


class HostListingAdb:
    serial = "SERIAL-42"

    def __init__(self, output, result="success", code=0):
        self.output = output
        self.result = result
        self.code = code
        self.records = [{"operation": "host-devices", "result": result,
                         "timeout_seconds": 5, "max_output_bytes": 4096}]

    def run(self, operation, **kwargs):
        assert operation == "host-devices"
        assert kwargs == {"timeout": 5, "max_bytes": 4096}
        return self.code, self.output, b""


def test_exact_endpoint_requires_one_matching_authorized_target():
    adb = HostListingAdb(b"List of devices attached\nSERIAL-42 device product:clarity\n")
    preflight.verify_exact_endpoint(adb)
    assert adb.records[-1]["endpoint_result"] == "ok"
    assert "SERIAL-42" not in str(adb.records[-1])


@pytest.mark.parametrize("listing", [
    "List of devices attached\nOTHER device\n",
    "List of devices attached\nSERIAL-42 unauthorized\n",
    "List of devices attached\nSERIAL-42 device\nOTHER device\n",
])
def test_exact_endpoint_refuses_wrong_or_ambiguous_target(monkeypatch, listing):
    adb = HostListingAdb(listing.encode())
    with pytest.raises(collector.SafetyStop):
        preflight.verify_exact_endpoint(adb)


@pytest.mark.parametrize(("line", "expected_mode"), [
    (b"-rwsrwsrwx 0 0 75348 2026-09-25 12:00 su\n", "0o6777"),
    (b"-rwsr-sr-x 0 0 75348 2026-09-25 12:00 su\n", "0o6755"),
    (b"-rwxr-xr-x 0 0 75348 2026-09-25 12:00 su\n", "0o0755"),
    (b"-rwSr-Sr-T 0 0 75348 2026-09-25 12:00 su\n", "0o7644"),
])
def test_parse_api17_numeric_metadata(line, expected_mode):
    assert preflight.parse_ls_numeric(line)["mode_octal"] == expected_mode


@pytest.mark.parametrize("raw", [
    b"", b"lrwxrwxrwx 0 0 1 2026-09-25 12:00 su -> /data/su\n",
    b"-rwsr-sr-x root root 75348 2026-09-25 12:00 su\n",
    b"-rwsr-sr-x 0 0 75348 2026-09-25 12:00 other\n",
    b"-rwsr-sr-x 0 0 75348 2026-09-25 12:00 su\n-rwsr-sr-x 0 0 1 2026-09-25 12:00 su\n",
    b"-rwxrSxr-x 0 0 75348 2026-09-25 12:00 su\n",
])
def test_metadata_parser_fails_closed(raw):
    with pytest.raises(collector.SafetyStop):
        preflight.parse_ls_numeric(raw)


def test_hash_parser_requires_exact_single_path_and_digest():
    assert preflight.parse_sha256sum(
        f"{EXPECTED_SU_SHA256}  /system/xbin/su\n".encode()) == EXPECTED_SU_SHA256
    with pytest.raises(collector.SafetyStop):
        preflight.parse_sha256sum(b"not available\n")
    with pytest.raises(collector.SafetyStop):
        preflight.parse_sha256sum(("0" * 64 + "  /system/bin/jmcs\n").encode())


def test_integrity_success_never_authorizes_root_execution():
    metadata = {"file_type": "regular", "uid": 0, "gid": 0,
                "mode_string": "-rwsr-sr-x", "mode_octal": "0o6755"}
    assert preflight.integrity_decision(metadata, EXPECTED_SU_SHA256) == (
        True, "NOT_READY_SIDE_EFFECTS_UNRESOLVED")


@pytest.mark.parametrize(("mode", "digest"), [
    ("0o6777", EXPECTED_SU_SHA256),  # archived unsafe write permissions
    ("0o6755", "0" * 64),
    ("0o0755", EXPECTED_SU_SHA256),
])
def test_integrity_failure_never_authorizes_root_execution(mode, digest):
    metadata = {"file_type": "regular", "uid": 0, "gid": 0,
                "mode_string": "-rwsr-sr-x", "mode_octal": mode}
    assert preflight.integrity_decision(metadata, digest) == (False, "INELIGIBLE")


@pytest.mark.parametrize("mode", ["0o6777", "0o6755"])
@pytest.mark.parametrize(("uid", "gid"), [(2000, 0), (0, 2000)])
def test_integrity_gate_requires_numeric_root_owner_and_group(mode, uid, gid):
    metadata = {"file_type": "regular", "uid": uid, "gid": gid,
                "mode_string": "-rwsr-sr-x", "mode_octal": mode}
    assert preflight.integrity_decision(metadata, EXPECTED_SU_SHA256) == (False, "INELIGIBLE")


def test_missing_metadata_or_digest_is_incomplete_not_a_current_integrity_verdict():
    assert preflight.integrity_decision(None, EXPECTED_SU_SHA256) == (False, "INCOMPLETE_EVIDENCE")
    assert preflight.integrity_decision(
        {"uid": 0, "gid": 0, "mode_octal": "0o6755"}, None) == (False, "INCOMPLETE_EVIDENCE")


def test_unprivileged_owner_confirmations_precede_any_device_command(monkeypatch, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("ADB target initialization must not occur without confirmations")
    monkeypatch.setattr(preflight, "FixedAdb", forbidden)
    assert preflight.main(["--serial", "AUTHORIZED-ENDPOINT"]) == 1
    assert "confirmations are required" in capsys.readouterr().err


def test_api17_device_listing_tolerates_daemon_notice_without_accepting_extra_devices():
    adb = HostListingAdb(b"* daemon started successfully *\nList of devices attached\nSERIAL-42 device\n")
    preflight.verify_exact_endpoint(adb)
    assert adb.records[-1]["candidate_count"] == 1


def test_private_output_summary_is_exclusive_and_mode_restricted(tmp_path):
    target = tmp_path / "summary.json"
    preflight._write_summary(target, {"safe": True})
    assert stat.S_IMODE(target.stat().st_mode) == 0o600
    with pytest.raises(FileExistsError):
        preflight._write_summary(target, {"safe": False})
    assert not list(tmp_path.glob(".*.tmp"))


def test_summary_write_failure_leaves_no_partial_published_file(tmp_path, monkeypatch):
    target = tmp_path / "summary.json"
    monkeypatch.setattr(preflight.os, "link", lambda *_args: (_ for _ in ()).throw(OSError("disk full")))
    with pytest.raises(OSError, match="disk full"):
        preflight._write_summary(target, {"safe": True})
    assert not target.exists()
    assert not list(tmp_path.glob(".*.tmp"))


def test_existing_broad_output_root_is_refused_without_changing_its_mode(tmp_path):
    target = tmp_path / "publicish"
    target.mkdir(mode=0o755)
    target.chmod(0o755)
    with pytest.raises(collector.SafetyStop, match="refusing to change it"):
        preflight.run("SERIAL-42", target)
    assert stat.S_IMODE(target.stat().st_mode) == 0o755


class FakeAdb:
    adb = "/usr/bin/adb"

    def __init__(self, *, metadata_result="success", metadata_code=0,
                 hash_result="success", hash_code=0, hash_output=None,
                 identity_device="vcm30t30a"):
        self.serial = "SERIAL-42"
        self.records = []
        self.metadata_result = metadata_result
        self.metadata_code = metadata_code
        self.hash_result = hash_result
        self.hash_code = hash_code
        self.hash_output = hash_output
        self.identity_device = identity_device
        self.operations = []

    def run(self, operation, *args, **kwargs):
        self.operations.append((operation, args))
        if operation == "read":
            output = b"Linux version 3.1.10+ (builder)\n"
        elif operation == "property":
            values = {"ro.build.version.release": "4.2.2", "ro.build.version.sdk": "17",
                      "ro.product.device": self.identity_device, "ro.product.board": "Andromeda",
                      "ro.hardware": "vcm30t30"}
            output = (values[args[0]] + "\n").encode()
        elif operation == "ls-su-n":
            output = b"-rwsrwsrwx 0 0 75348 2026-09-25 12:00 su\n"
        elif operation == "hash-su":
            output = self.hash_output or f"{EXPECTED_SU_SHA256}  /system/xbin/su\n".encode()
        else:
            raise AssertionError(f"unexpected operation {operation}")
        result = (self.metadata_result if operation == "ls-su-n" else
                  self.hash_result if operation == "hash-su" else "success")
        self.records.append({"operation": operation, "result": result,
                             "command": ["adb", "-s", self.serial, "shell", operation],
                             "exit_code": self.metadata_code if operation == "ls-su-n" else
                             self.hash_code if operation == "hash-su" else 0})
        return (self.metadata_code if operation == "ls-su-n" else
                self.hash_code if operation == "hash-su" else 0), output, b""


def _run_fake(monkeypatch, tmp_path, fake):
    monkeypatch.setattr(preflight, "FixedAdb", lambda *args, **kwargs: fake)
    monkeypatch.setattr(preflight, "verify_exact_endpoint", lambda adb: None)
    return preflight.run("SERIAL-42", tmp_path / "private"), fake


def test_run_captures_metadata_privately_and_never_invokes_su(monkeypatch, tmp_path):
    fake = FakeAdb()
    output, fake = _run_fake(monkeypatch, tmp_path, fake)
    summary = json.loads((output / "summary.json").read_text())
    assert summary["metadata"]["uid"] == summary["metadata"]["gid"] == 0
    assert summary["metadata"]["mode_octal"] == "0o6777"
    assert summary["integrity_gate"] == "FAIL_OR_INCOMPLETE"
    assert summary["root_execution_eligibility"] == "INELIGIBLE"
    assert summary["existing_root_authorization_change"] == "UNKNOWN_NOT_OBSERVED"
    assert summary["root_or_target_writes_performed"] is False
    assert [op for op, _ in fake.operations] == [
        "read", "property", "property", "property", "property", "property",
        "ls-su-n", "hash-su"]
    assert all(op != "su" for op, _ in fake.operations)
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert stat.S_IMODE((output / "summary.json").stat().st_mode) == 0o600
    assert (output / "manifest.json").is_file() and (output / "sha256.txt").is_file()


@pytest.mark.parametrize("failure", ["timeout", "output_limit", "transport_failure"])
def test_run_stops_on_metadata_transport_timeout_or_truncation(monkeypatch, tmp_path, failure):
    fake = FakeAdb(metadata_result=failure)
    with pytest.raises(collector.SafetyStop, match="partial private capture preserved"):
        _run_fake(monkeypatch, tmp_path, fake)
    output, = (tmp_path / "private").iterdir()
    summary = json.loads((output / "summary.json").read_text())
    assert summary["execution_status"] == "ABORTED"
    assert [op for op, _ in fake.operations][-1] == "ls-su-n"
    assert "hash-su" not in [op for op, _ in fake.operations]
    assert (output / "manifest.json").is_file()


def test_run_preserves_failure_summary_when_target_identity_does_not_match(monkeypatch, tmp_path):
    fake = FakeAdb(identity_device="wrong-device")
    with pytest.raises(collector.SafetyStop, match="partial private capture preserved"):
        _run_fake(monkeypatch, tmp_path, fake)
    output = next((tmp_path / "private").iterdir())
    summary = json.loads((output / "summary.json").read_text())
    assert summary["execution_status"] == "ABORTED"
    assert "device" in summary["details"]
    assert [op for op, _ in fake.operations] == ["read", "property", "property", "property"]
    assert (output / "manifest.json").is_file()


def test_nonzero_metadata_result_reports_incomplete_and_skips_hash(monkeypatch, tmp_path):
    fake = FakeAdb(metadata_result="other_command_failure", metadata_code=1)
    output, fake = _run_fake(monkeypatch, tmp_path, fake)
    summary = json.loads((output / "summary.json").read_text())
    assert summary["execution_status"] == "INCOMPLETE"
    assert summary["integrity_gate"] == "FAIL_OR_INCOMPLETE"
    assert summary["root_execution_eligibility"] == "INCOMPLETE_EVIDENCE"
    assert "hash-su" not in [op for op, _ in fake.operations]


@pytest.mark.parametrize(("result", "hash_output"), [
    ("command_unavailable", b""),
    ("success", b"sha256sum produced a malformed response\n"),
])
def test_failed_or_unparseable_optional_hash_is_incomplete_evidence(monkeypatch, tmp_path, result, hash_output):
    fake = FakeAdb(hash_result=result, hash_code=127 if result != "success" else 0,
                   hash_output=hash_output)
    output, fake = _run_fake(monkeypatch, tmp_path, fake)
    summary = json.loads((output / "summary.json").read_text())
    assert summary["execution_status"] == "COMPLETE"
    assert summary["sha256_status"] == "unavailable_or_unparseable"
    assert summary["root_execution_eligibility"] == "INCOMPLETE_EVIDENCE"
    assert [op for op, _ in fake.operations].count("hash-su") == 1


def test_capture_id_collision_never_overwrites_existing_evidence(monkeypatch, tmp_path):
    import datetime as datetime_module

    fixed = datetime_module.datetime(2026, 11, 2, 12, 0, 0, tzinfo=datetime_module.timezone.utc)
    class FixedDateTime:
        @staticmethod
        def now(_timezone):
            return fixed
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    output = root / "su-preflight-20261102T120000.000000Z"
    output.mkdir(mode=0o700)
    marker = output / "summary.json"
    marker.write_text("preserve me")
    monkeypatch.setattr(preflight, "datetime", FixedDateTime)
    fake = FakeAdb()
    monkeypatch.setattr(preflight, "FixedAdb", lambda *args, **kwargs: fake)
    monkeypatch.setattr(preflight, "verify_exact_endpoint", lambda _adb: None)
    with pytest.raises(FileExistsError):
        preflight.run("SERIAL-42", root)
    assert marker.read_text() == "preserve me"
    assert fake.operations == []
