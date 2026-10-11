import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location(
    "r7e5c_a0wr", ROOT / "tools/r7e5c_a0wr_collector.py")
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


@pytest.mark.parametrize(("host", "remote"), [
    (0o644, 0o666),
    (0o755, 0o777),
    (0o444, 0o444),
    (0o555, 0o555),
    (0o600, 0o666),
    (0o700, 0o777),
])
def test_legacy_adb_v1_mode_transform(host, remote):
    assert collector.legacy_adb_v1_remote_mode(host) == remote


def test_second_or_copies_the_updated_group_bits_into_other():
    after_group_copy = 0o644 | ((0o644 >> 3) & 0o070)
    assert after_group_copy == 0o664
    assert after_group_copy | ((after_group_copy >> 3) & 0o007) == 0o666
    assert collector.legacy_adb_v1_remote_mode(0o644) == 0o666


def test_previous_a0w_0666_observation_is_classified_as_aosp_mode_match():
    assert collector.classify_legacy_adb_mode_observation(0o644, 0o666) == (
        "HONDA_OBSERVED_MATCHES_AOSP_LEGACY_ADB_MODE_TRANSFORM")
    # The classification describes behavioral agreement, never target identity.


class FakeAdb:
    def __init__(self, fault=None):
        self.fault = fault
        self.calls = []
        self.push_attempts = 0
        self.marker_ls_calls = 0

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        assert kwargs["timeout"] == collector.TIMEOUT_SECONDS
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        if len(self.calls) == 1:
            return subprocess.CompletedProcess(
                argv, 0, "List of devices attached\nSERIAL_SECRET\tdevice\n", "")
        assert argv[1:3] == ["-s", "SERIAL_SECRET"]
        op = argv[3:]
        if op == ["shell", "ls", "-ld", collector.PARENT_PATH]:
            return subprocess.CompletedProcess(
                argv, 0, "drwxrwx--x shell shell 2026-10-11 02:00 tmp\n", "")
        if op == ["shell", "ls", "-l", collector.REMOTE_PATH]:
            self.marker_ls_calls += 1
            if self.marker_ls_calls == 1:
                if self.fault == "existing":
                    return subprocess.CompletedProcess(
                        argv, 0,
                        f"-r--r--r-- shell shell 62 2026-10-11 10:00 {Path(collector.REMOTE_PATH).name}\n", "")
                return subprocess.CompletedProcess(
                    argv, 1, "", f"{collector.REMOTE_PATH}: No such file or directory\n")
            if self.marker_ls_calls == 2:
                modes = {
                    "mode_0644": "-rw-r--r--",
                    "mode_0666": "-rw-rw-rw-",
                    "mode_executable": "-r-xr-xr-x",
                }
                mode = modes.get(self.fault, "-r--r--r--")
                return subprocess.CompletedProcess(
                    argv, 0,
                    f"{mode} shell shell {len(collector.MARKER_BYTES)} 2026-10-11 10:00 {Path(collector.REMOTE_PATH).name}\n", "")
            if self.fault == "absence_present":
                return subprocess.CompletedProcess(
                    argv, 0,
                    f"-r--r--r-- shell shell {len(collector.MARKER_BYTES)} 2026-10-11 10:00 {Path(collector.REMOTE_PATH).name}\n", "")
            if self.fault == "absence_unknown":
                return subprocess.CompletedProcess(argv, 1, "", "permission denied\n")
            return subprocess.CompletedProcess(
                argv, 1, "", f"{collector.REMOTE_PATH}: No such file or directory\n")
        if op[0] == "push":
            self.push_attempts += 1
            if self.fault == "push_timeout":
                raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
            if self.fault == "push_failure":
                return subprocess.CompletedProcess(argv, 1, "", "sync failure\n")
            return subprocess.CompletedProcess(argv, 0, "", "1 file pushed.\n")
        if op == ["shell", "/system/bin/md5", collector.REMOTE_PATH]:
            if self.fault == "md5_failure":
                return subprocess.CompletedProcess(argv, 127, "", "md5 unavailable\n")
            digest = "0" * 32 if self.fault == "md5_mismatch" else collector.MARKER_MD5
            return subprocess.CompletedProcess(argv, 0, f"{digest} {collector.REMOTE_PATH}\n", "")
        if op == ["shell", "/system/bin/rm", collector.REMOTE_PATH]:
            if self.fault == "rm_failure":
                return subprocess.CompletedProcess(argv, 1, "", "rm failed\n")
            return subprocess.CompletedProcess(argv, 0, "", "")
        raise AssertionError(f"unexpected command {argv!r}")


def package_env(tmp_path, monkeypatch):
    marker = tmp_path / "marker.txt"
    marker.write_bytes(collector.MARKER_BYTES)
    marker.chmod(0o444)
    manifest_path = tmp_path / "manifest.json"
    monkeypatch.setattr(collector, "MARKER_PATH", marker)
    monkeypatch.setattr(collector, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(collector, "EVIDENCE_ROOT", tmp_path / "evidence")
    monkeypatch.setattr(collector, "REMOTE_PATH", "/data/local/tmp/claritylink_a0wr_test.probe")
    doc = collector.manifest_template()
    doc["collector_source_sha256"] = hashlib.sha256(Path(collector.__file__).read_bytes()).hexdigest()
    manifest_path.write_text(json.dumps(doc, sort_keys=True, indent=2) + "\n")
    source_sha = doc["collector_source_sha256"]
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    args = ["--execute-authorized-a0wr-write-delete", "--authorization-ref", "A0WR-TEST-REF",
            "--expected-source-sha256", source_sha, "--expected-manifest-sha256", manifest_sha,
            "--observed-power-state", "car powered on", "--audio-state-before",
            "Bluetooth music playing", "--stationary", "--parked", "--center-display-booted",
            "--cluster-normal", "--no-unexpected-warnings", "--confirm-intended-honda-target",
            "--exclusive-adb-window-confirmed"]
    return args


def run_fake(args, fake):
    return collector.main(args, runner=fake, input_fn=lambda _: "STOCK_STATE_UNCHANGED")


def test_default_and_dry_run_make_zero_adb_calls(capsys):
    calls = []
    runner = lambda *a, **k: calls.append(a)
    assert collector.main([], runner=runner) == 2
    assert "NOT_AUTHORIZED" in capsys.readouterr().err
    assert collector.main(["--dry-run"], runner=runner) == 0
    assert calls == []
    dry_run = capsys.readouterr().out
    assert "TARGET_REDACTED" in dry_run
    assert "/system/bin/md5" in dry_run
    assert "/system/bin/rm" in dry_run


def test_manifest_has_one_push_one_exact_rm_no_retry_fallback_or_chmod():
    manifest = collector.manifest_template()
    commands = manifest["commands"]
    assert len(commands) == 8
    assert sum(entry["id"] == "A0WR-03" for entry in commands) == 1
    assert sum(entry["id"] == "A0WR-06" for entry in commands) == 1
    assert manifest["retries"] == 0
    assert manifest["fallbacks"] == []
    assert manifest["host_staging_mode"] == "0444"
    assert manifest["expected_remote_mode"] == "0444"
    assert manifest["md5_required_after_push_attempt"] is True
    commands_text = " ".join(" ".join(entry["argv"]) for entry in commands)
    assert "chmod" not in commands_text
    assert "claritylink-target-diag" not in commands_text


def test_mode_model_and_new_marker_staging_are_idempotent():
    assert collector.HOST_STAGING_MODE == 0o444
    assert collector.EXPECTED_REMOTE_MODE == 0o444
    assert collector.legacy_adb_v1_remote_mode(0o444) == 0o444


def test_package_binding_mismatch_stops_before_adb(tmp_path, monkeypatch, capsys):
    args = package_env(tmp_path, monkeypatch)
    args[args.index("--expected-manifest-sha256") + 1] = "0" * 64
    fake = FakeAdb()
    assert collector.main(args, runner=fake) == 2
    assert fake.calls == []
    assert "A0WR_AUTHORIZATION_BINDING_MISMATCH" in capsys.readouterr().err


def test_host_marker_wrong_mode_stops_before_adb(tmp_path, monkeypatch, capsys):
    args = package_env(tmp_path, monkeypatch)
    marker_path = collector.MARKER_PATH
    marker_path.chmod(0o644)
    fake = FakeAdb()
    assert collector.main(args, runner=fake) == 2
    assert fake.calls == []
    assert "host marker mode is not exactly 0444" in capsys.readouterr().err


@pytest.mark.parametrize("invalid", ["missing", "symlink", "mutated"])
def test_invalid_host_marker_stops_before_adb(tmp_path, monkeypatch, capsys, invalid):
    args = package_env(tmp_path, monkeypatch)
    marker_path = collector.MARKER_PATH
    if invalid == "missing":
        marker_path.unlink()
    elif invalid == "symlink":
        target = tmp_path / "target-marker.txt"
        target.write_bytes(collector.MARKER_BYTES)
        target.chmod(0o444)
        marker_path.unlink()
        marker_path.symlink_to(target)
    else:
        marker_path.chmod(0o644)
        marker_path.write_bytes(collector.MARKER_BYTES + b"changed")
        marker_path.chmod(0o444)
    fake = FakeAdb()
    assert collector.main(args, runner=fake) == 2
    assert fake.calls == []
    assert "A0WR_AUTHORIZATION_BINDING_MISMATCH" in capsys.readouterr().err


@pytest.mark.parametrize("inventory", [
    "List of devices attached\n", "List of devices attached\nA\tdevice\nB\tdevice\n",
    "List of devices attached\nA\toffline\n",
])
def test_invalid_target_inventory_stops_before_shell_or_write(tmp_path, monkeypatch, inventory):
    args = package_env(tmp_path, monkeypatch)

    class InvalidInventory(FakeAdb):
        def __call__(self, argv, **kwargs):
            self.calls.append(argv)
            return subprocess.CompletedProcess(argv, 0, inventory, "")

    fake = InvalidInventory()
    assert run_fake(args, fake) == 1
    assert len(fake.calls) == 1
    assert fake.push_attempts == 0


def test_destination_metadata_mismatch_stops_before_push(tmp_path, monkeypatch):
    args = package_env(tmp_path, monkeypatch)

    class WrongParent(FakeAdb):
        def __call__(self, argv, **kwargs):
            if not self.calls:
                self.calls.append(argv)
                return subprocess.CompletedProcess(
                    argv, 0, "List of devices attached\nSERIAL_SECRET\tdevice\n", "")
            if argv[3:] == ["shell", "ls", "-ld", collector.PARENT_PATH]:
                self.calls.append(argv)
                return subprocess.CompletedProcess(
                    argv, 0, "drwxrwxrwx shell shell 2026-10-11 02:00 tmp\n", "")
            raise AssertionError(f"unexpected command after destination mismatch: {argv!r}")

    fake = WrongParent()
    assert run_fake(args, fake) == 1
    assert len(fake.calls) == 2
    assert fake.push_attempts == 0


def test_happy_path_runs_one_push_md5_exact_cleanup_and_keeps_selector_private(tmp_path, monkeypatch):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb()
    assert run_fake(args, fake) == 0
    assert fake.push_attempts == 1
    assert len(fake.calls) == 8
    assert [call[3:4] for call in fake.calls[1:]] == [
        ["shell"], ["shell"], ["push"], ["shell"], ["shell"], ["shell"], ["shell"]]
    assert fake.calls[5][3:] == ["shell", "/system/bin/md5", collector.REMOTE_PATH]
    assert fake.calls[6][3:] == ["shell", "/system/bin/rm", collector.REMOTE_PATH]
    run_dir = next(collector.EVIDENCE_ROOT.iterdir())
    meta = json.loads((run_dir / "metadata.json").read_text())
    assert meta["decision"] == "A0WR_PASS_FOR_REVIEW"
    assert meta["target_identity"] == "REDACTED"
    assert "SERIAL_SECRET" not in json.dumps(meta)
    assert meta["target_writes"] == 1
    assert meta["cleanup_verified"] is True
    assert meta["md5_attempted_after_push"] is True
    assert meta["test_a"] == "NOT_AUTHORIZED"
    assert (run_dir / "target-identity.local.txt").read_text().strip() == "SERIAL_SECRET"


@pytest.mark.parametrize(("fault", "expected"), [
    ("mode_0644", "A0WR_STOP_CONDITION"),
    ("mode_0666", "A0WR_STOP_CONDITION"),
    ("mode_executable", "A0WR_STOP_CONDITION"),
])
def test_any_unexpected_remote_mode_stops_but_still_md5_and_cleans(tmp_path, monkeypatch, fault, expected):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb(fault=fault)
    assert run_fake(args, fake) == 1
    assert fake.push_attempts == 1
    assert any(call[3:] == ["shell", "/system/bin/md5", collector.REMOTE_PATH] for call in fake.calls)
    assert any(call[3:] == ["shell", "/system/bin/rm", collector.REMOTE_PATH] for call in fake.calls)
    run_dir = next(collector.EVIDENCE_ROOT.iterdir())
    meta = json.loads((run_dir / "metadata.json").read_text())
    assert meta["decision"] == expected
    assert meta["cleanup_verified"] is True
    assert meta["marker_metadata_verified"] is False


@pytest.mark.parametrize("fault", ["md5_mismatch", "md5_failure"])
def test_md5_failure_stops_and_cleans(tmp_path, monkeypatch, fault):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb(fault=fault)
    assert run_fake(args, fake) == 1
    assert fake.push_attempts == 1
    run_dir = next(collector.EVIDENCE_ROOT.iterdir())
    meta = json.loads((run_dir / "metadata.json").read_text())
    assert meta["decision"] == "A0WR_STOP_CONDITION"
    assert meta["md5_attempted_after_push"] is True
    assert meta["md5_transport_consistency_verified"] is False
    assert meta["cleanup_verified"] is True


@pytest.mark.parametrize("fault", ["push_failure", "push_timeout"])
def test_failed_push_attempt_still_runs_read_md5_cleanup_and_absence(tmp_path, monkeypatch, fault):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb(fault=fault)
    assert run_fake(args, fake) == 1
    assert fake.push_attempts == 1
    assert any(call[3:] == ["shell", "/system/bin/md5", collector.REMOTE_PATH] for call in fake.calls)
    assert any(call[3:] == ["shell", "/system/bin/rm", collector.REMOTE_PATH] for call in fake.calls)
    run_dir = next(collector.EVIDENCE_ROOT.iterdir())
    meta = json.loads((run_dir / "metadata.json").read_text())
    assert meta["decision"] == "A0WR_STOP_CONDITION"
    assert meta["cleanup_verified"] is True


@pytest.mark.parametrize("fault", ["absence_present", "absence_unknown"])
def test_absence_verification_failure_is_hard_blocker(tmp_path, monkeypatch, fault):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb(fault=fault)
    assert run_fake(args, fake) == 1
    run_dir = next(collector.EVIDENCE_ROOT.iterdir())
    meta = json.loads((run_dir / "metadata.json").read_text())
    assert meta["decision"] == "A0WR_CLEANUP_NOT_VERIFIED"
    assert meta["cleanup_verified"] is False


def test_cleanup_command_failure_is_not_pass(tmp_path, monkeypatch):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb(fault="rm_failure")
    assert run_fake(args, fake) == 1
    run_dir = next(collector.EVIDENCE_ROOT.iterdir())
    meta = json.loads((run_dir / "metadata.json").read_text())
    assert meta["decision"] == "A0WR_STOP_CONDITION"
    assert meta["cleanup_command_success"] is False


def test_exact_path_preexistence_gate_blocks_before_push(tmp_path, monkeypatch):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb(fault="existing")
    assert run_fake(args, fake) == 1
    assert fake.push_attempts == 0
    assert len(fake.calls) == 3
