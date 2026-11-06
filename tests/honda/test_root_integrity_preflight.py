import hashlib
import json
from pathlib import Path
import stat
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
TOOLS = ROOT / "tools/honda-readonly-preflight"
sys.path.insert(0, str(TOOLS))

import collector
import root_integrity_preflight as preflight


def test_fixed_plan_is_exact_and_uses_only_explicit_serial(monkeypatch, tmp_path):
    monkeypatch.setattr(collector.shutil, "which", lambda _: "/opt/homebrew/bin/adb")
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    adb = collector.FixedAdb("TEST-ENDPOINT", resolve_auto=False)
    assert adb.plan("read", ("/proc/mounts",)) == (
        "/opt/homebrew/bin/adb", "-s", "TEST-ENDPOINT", "shell", "cat", "/proc/mounts")
    assert adb.plan("ls-su-n", ()) == (
        "/opt/homebrew/bin/adb", "-s", "TEST-ENDPOINT", "shell", "ls", "-n", "/system/xbin/su")
    assert preflight.plan_su_pull(adb, private / "su.bin") == (
        "/opt/homebrew/bin/adb", "-s", "TEST-ENDPOINT", "pull",
        "/system/xbin/su", str(private / "su.bin"))
    with pytest.raises(collector.SafetyStop):
        preflight.plan_su_pull(adb, ROOT / "su.bin")
    existing = private / "existing.bin"
    existing.write_bytes(b"preserve")
    with pytest.raises(collector.SafetyStop):
        preflight.plan_su_pull(adb, existing)
    assert existing.read_bytes() == b"preserve"


@pytest.mark.parametrize(("line", "expected"), [
    (b"-rwsrwsrwx 0 0 75348 2026-09-25 12:00 su\n", "0o6777"),
    (b"-rwsr-sr-x 0 0 75348 2026-09-25 12:00 su\n", "0o6755"),
])
def test_parse_api17_numeric_metadata(line, expected):
    assert preflight.parse_ls_numeric(line)["mode_octal"] == expected


@pytest.mark.parametrize("raw", [
    b"", b"lrwxrwxrwx 0 0 1 2026-09-25 12:00 su -> /data/su\n",
    b"-rwsr-sr-x root root 75348 2026-09-25 12:00 su\n",
    b"-rwsr-sr-x 0 0 75348 2026-09-25 12:00 other\n",
    b"-rwsr-sr-x 0 0 75348 2026-09-25 12:00 su\n-rwsr-sr-x 0 0 1 2026-09-25 12:00 su\n",
])
def test_metadata_parser_fails_closed(raw):
    with pytest.raises(collector.SafetyStop):
        preflight.parse_ls_numeric(raw)


def test_mount_parser_uses_most_specific_covering_entry_and_reports_ro():
    raw = (b"/dev/root / ext4 rw,seclabel 0 0\n"
           b"/dev/block/system /system ext4 ro,seclabel,relatime 0 0\n"
           b"/dev/block/data /data ext4 rw,seclabel 0 0\n")
    result = preflight.covering_mount(raw)
    assert result["complete"] is True
    assert result["mount_point"] == "/system"
    assert result["filesystem_type"] == "ext4"
    assert result["read_only"] is True and result["read_write"] is False


def test_mount_parser_detects_more_specific_rw_overlay_or_ambiguity():
    raw = (b"/dev/block/system /system ext4 ro 0 0\n"
           b"overlay /system/xbin overlay rw,lowerdir=/lower,upperdir=/upper 0 0\n")
    result = preflight.covering_mount(raw)
    assert result["mount_point"] == "/system/xbin"
    assert result["read_write"] is True
    assert result["overlay_uncertainty"]
    duplicate = (b"/dev/block/a /system ext4 ro 0 0\n"
                 b"/dev/block/b /system ext4 rw 0 0\n")
    assert preflight.covering_mount(duplicate)["complete"] is False


def test_mount_parser_fails_incomplete_and_unescaped_flags():
    assert preflight.covering_mount(b"broken\n")["complete"] is False
    missing_flag = preflight.covering_mount(b"/dev/block/system /system ext4 relatime 0 0\n")
    assert missing_flag["complete"] is False
    escaped = preflight.covering_mount(b"/dev/block/system /system\\040A ext4 ro 0 0\n")
    assert escaped["complete"] is False


def test_candidate_requires_exact_hash_and_ro_but_never_calls_it_integrity_pass():
    metadata = {"file_type": "regular", "uid": 0, "gid": 0,
                "mode_octal": "0o6777", "size_bytes": 75348, "setuid": True}
    mount = {"complete": True, "read_only": True, "read_write": False}
    assert preflight.controlled_candidate(metadata, preflight.EXPECTED_SU_SHA256, 75348, mount) == (
        True, "CONTROLLED_IDENTITY_CHECK_CANDIDATE_PENDING_NEW_OWNER_DECISION")
    assert preflight.controlled_candidate(metadata, "0" * 64, 75348, mount)[0] is False
    assert preflight.controlled_candidate(metadata, preflight.EXPECTED_SU_SHA256, 75348,
                                          {**mount, "read_only": False, "read_write": True}) == (
        False, "INELIGIBLE_SYSTEM_MOUNT_READ_WRITE")
    assert preflight.controlled_candidate(metadata, preflight.EXPECTED_SU_SHA256, 75348,
                                          {**mount, "overlay_uncertainty": ["bind"]}) == (
        False, "INELIGIBLE_MOUNT_LAYERING_UNRESOLVED")


class FakeAdb:
    def __init__(self, serial, binary, mounts, metadata):
        self.serial = serial
        self.adb = "/opt/homebrew/bin/adb"
        self.binary = binary
        self.mounts = mounts
        self.metadata = metadata
        self.records = []
        self.operations = []

    def run(self, operation, *args, **kwargs):
        self.operations.append((operation, args))
        output = {"read": self.mounts, "ls-su-n": self.metadata}[operation]
        self.records.append({"operation": operation, "result": "success", "exit_code": 0})
        return 0, output, b""

    def _run_planned(self, command, operation, args, *, timeout, max_bytes):
        assert command[1:4] == ("-s", self.serial, "pull")
        assert operation == "pull-su" and args[0] == "/system/xbin/su"
        Path(args[1]).write_bytes(self.binary)
        self.operations.append((operation, args))
        self.records.append({"operation": operation, "result": "success", "exit_code": 0})
        return 0, b"1 file pulled\n", b""


def test_one_shot_run_collects_only_three_target_operations_and_hashes_host_copy(monkeypatch, tmp_path):
    binary = b"synthetic su bytes"
    digest = hashlib.sha256(binary).hexdigest()
    monkeypatch.setattr(preflight, "EXPECTED_SU_SHA256", digest)
    monkeypatch.setattr(preflight, "EXPECTED_SU_SIZE", len(binary))
    mounts = b"/dev/root / ext4 rw 0 0\n/dev/system /system ext4 ro,seclabel 0 0\n"
    metadata = b"-rwsrwsrwx 0 0 18 2026-09-25 12:00 su\n"
    fake = FakeAdb("TEST-ENDPOINT", binary, mounts, metadata)
    monkeypatch.setattr(preflight, "FixedAdb", lambda serial, resolve_auto: fake)
    root = tmp_path / "private"
    output = preflight.run("TEST-ENDPOINT", root)
    summary = json.loads((output / "summary.json").read_text())
    assert [name for name, _args in fake.operations] == ["read", "ls-su-n", "pull-su"]
    assert summary["observed_sha256"] == digest
    assert summary["pulled_size_bytes"] == len(binary)
    assert summary["controlled_root_identity_candidate"] is True
    assert summary["conventional_integrity_status"].startswith("NOT_A_CONVENTIONAL")
    assert summary["stage_a"].startswith("NOT_EXECUTED")
    assert summary["root_or_target_writes_performed"] is False
    assert stat.S_IMODE(output.stat().st_mode) == 0o700
    assert stat.S_IMODE((output / "summary.json").stat().st_mode) == 0o600
    assert stat.S_IMODE((output / "system_xbin_su.bin").stat().st_mode) == 0o600
    assert summary["expected_sha256"] == summary["observed_sha256"]
    assert (output / "manifest.json").is_file() and (output / "sha256.txt").is_file()


@pytest.mark.parametrize(("mounts", "expected_status"), [
    (b"/dev/root / ext4 rw 0 0\n/dev/system /system ext4 rw,seclabel 0 0\n",
     "INELIGIBLE_SYSTEM_MOUNT_READ_WRITE"),
    (b"malformed mount table\n", "INCOMPLETE_EVIDENCE"),
])
def test_non_readonly_or_incomplete_mount_stops_before_metadata_and_pull(
        monkeypatch, tmp_path, mounts, expected_status):
    fake = FakeAdb("TEST-ENDPOINT", b"unused", mounts,
                   b"-rwsrwsrwx 0 0 75348 2026-09-25 12:00 su\n")
    monkeypatch.setattr(preflight, "FixedAdb", lambda serial, resolve_auto: fake)
    output = preflight.run("TEST-ENDPOINT", tmp_path / "private")
    summary = json.loads((output / "summary.json").read_text())
    assert [name for name, _args in fake.operations] == ["read"]
    assert summary["root_execution_eligibility"] == expected_status
    assert summary["observed_sha256"] is None
    assert summary["controlled_root_identity_candidate"] is False
    assert (output / "manifest.json").is_file()


def test_implausibly_large_reported_file_stops_before_pull(monkeypatch, tmp_path):
    mounts = b"/dev/root / ext4 rw 0 0\n/dev/system /system ext4 ro,seclabel 0 0\n"
    metadata = b"-rwsrwsrwx 0 0 1048577 2026-09-25 12:00 su\n"
    fake = FakeAdb("TEST-ENDPOINT", b"unused", mounts, metadata)
    monkeypatch.setattr(preflight, "FixedAdb", lambda serial, resolve_auto: fake)
    output = preflight.run("TEST-ENDPOINT", tmp_path / "private")
    summary = json.loads((output / "summary.json").read_text())
    assert [name for name, _args in fake.operations] == ["read", "ls-su-n"]
    assert summary["execution_status"] == "STOPPED_IMPLAUSIBLE_FILE_SIZE"
    assert summary["observed_sha256"] is None
    assert not (output / "system_xbin_su.bin").exists()


def test_mount_transport_failure_stops_once_and_preserves_partial_capture(monkeypatch, tmp_path):
    mounts = b"/dev/root / ext4 rw 0 0\n/dev/system /system ext4 ro 0 0\n"
    fake = FakeAdb("TEST-ENDPOINT", b"unused", mounts,
                   b"-rwsrwsrwx 0 0 75348 2026-09-25 12:00 su\n")
    def failed_mount(operation, *args, **kwargs):
        fake.operations.append((operation, args))
        fake.records.append({"operation": operation, "result": "transport_failure", "exit_code": 1})
        return 1, b"", b"device offline"
    fake.run = failed_mount
    monkeypatch.setattr(preflight, "FixedAdb", lambda serial, resolve_auto: fake)
    with pytest.raises(collector.SafetyStop, match="partial capture preserved"):
        preflight.run("TEST-ENDPOINT", tmp_path / "private")
    output = next((tmp_path / "private").iterdir())
    assert [name for name, _args in fake.operations] == ["read"]
    assert json.loads((output / "summary.json").read_text())["execution_status"] == "ABORTED"
    assert (output / "manifest.json").is_file()


def test_pull_failure_preserves_mount_and_numeric_metadata_without_retry(monkeypatch, tmp_path):
    binary = b"unused"
    mounts = b"/dev/root / ext4 rw 0 0\n/dev/system /system ext4 ro,seclabel 0 0\n"
    metadata = b"-rwsrwsrwx 0 0 75348 2026-09-25 12:00 su\n"
    fake = FakeAdb("TEST-ENDPOINT", binary, mounts, metadata)
    def failed_pull(command, operation, args, *, timeout, max_bytes):
        fake.operations.append((operation, args))
        fake.records.append({"operation": operation, "result": "other_command_failure", "exit_code": 1})
        return 1, b"", b"pull failed"
    fake._run_planned = failed_pull
    monkeypatch.setattr(preflight, "FixedAdb", lambda serial, resolve_auto: fake)
    with pytest.raises(collector.SafetyStop, match="partial capture preserved"):
        preflight.run("TEST-ENDPOINT", tmp_path / "private")
    output = next((tmp_path / "private").iterdir())
    summary = json.loads((output / "summary.json").read_text())
    assert [name for name, _args in fake.operations] == ["read", "ls-su-n", "pull-su"]
    assert summary["target_metadata"]["mode_octal"] == "0o6777"
    assert summary["observed_sha256"] is None
    assert (output / "manifest.json").is_file()


def test_capture_id_collision_preserves_existing_private_evidence(monkeypatch, tmp_path):
    class FixedDateTime:
        @staticmethod
        def now(_timezone):
            import datetime as datetime_module
            return datetime_module.datetime(2026, 11, 5, 12, 0, tzinfo=datetime_module.timezone.utc)
    monkeypatch.setattr(preflight, "datetime", FixedDateTime)
    root = tmp_path / "private"
    root.mkdir(mode=0o700)
    output = root / "su-preflight-20261105T120000.000000Z"
    output.mkdir(mode=0o700)
    marker = output / "preserve.txt"
    marker.write_text("keep")
    fake = FakeAdb("TEST-ENDPOINT", b"unused", b"", b"")
    monkeypatch.setattr(preflight, "FixedAdb", lambda serial, resolve_auto: fake)
    with pytest.raises(FileExistsError):
        preflight.run("TEST-ENDPOINT", root)
    assert marker.read_text() == "keep"
    assert fake.operations == []


def test_auto_serial_is_refused_before_private_directory_or_adb(monkeypatch, tmp_path):
    def forbidden(*args, **kwargs):
        raise AssertionError("ADB initialized for an unapproved serial")
    monkeypatch.setattr(preflight, "FixedAdb", forbidden)
    with pytest.raises(collector.SafetyStop, match="auto-selection is disabled"):
        preflight.run("auto", tmp_path / "private")
    assert not (tmp_path / "private").exists()


def test_confirmation_gate_precedes_adb_initialization(monkeypatch, tmp_path, capsys):
    def forbidden(*args, **kwargs):
        raise AssertionError("ADB initialized before required owner readiness")
    monkeypatch.setattr(preflight, "FixedAdb", forbidden)
    assert preflight.main(["--serial", "TEST-ENDPOINT", "--output-root", str(tmp_path / "private")]) == 1
    assert "readiness confirmations" in capsys.readouterr().err


def test_pull_plan_rejects_unowned_or_existing_destinations(monkeypatch, tmp_path):
    monkeypatch.setattr(collector.shutil, "which", lambda _: "/usr/bin/adb")
    private = tmp_path / "private"
    private.mkdir(mode=0o700)
    private.chmod(0o700)
    adb = collector.FixedAdb("TEST-ENDPOINT", resolve_auto=False)
    existing = private / "existing.bin"
    existing.write_bytes(b"keep")
    with pytest.raises(collector.SafetyStop):
        preflight.plan_su_pull(adb, existing)
    assert existing.read_bytes() == b"keep"


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
    with pytest.raises(collector.SafetyStop, match="group/other permissions"):
        preflight.run("TEST-ENDPOINT", target)
    assert stat.S_IMODE(target.stat().st_mode) == 0o755
