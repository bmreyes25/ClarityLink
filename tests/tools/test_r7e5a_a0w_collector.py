import hashlib
import importlib.util
import json
from pathlib import Path
import subprocess

import pytest


ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("r7e5a_a0w", ROOT / "tools/r7e5a_a0w_collector.py")
collector = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(collector)


class FakeAdb:
    def __init__(self, fault=None):
        self.fault = fault
        self.calls = []
        self.push_attempts = 0
        self.path_ls_calls = 0

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        assert kwargs["timeout"] == collector.TIMEOUT_SECONDS
        assert kwargs["capture_output"] is True
        assert kwargs["text"] is True
        i = len(self.calls)
        if i == 1:
            return subprocess.CompletedProcess(argv, 0, "List of devices attached\nSERIAL_SECRET\tdevice\n", "")
        assert argv[1:3] == ["-s", "SERIAL_SECRET"]
        op = argv[3:]
        if op == ["shell", "ls", "-ld", collector.PARENT_PATH]:
            owner = "root root" if self.fault == "parent_mismatch" else "shell shell"
            return subprocess.CompletedProcess(argv, 0,
                f"drwxrwx--x {owner} 2026-10-03 02:00 tmp\n", "")
        if op == ["shell", "ls", "-l", collector.REMOTE_PATH]:
            self.path_ls_calls += 1
            if self.path_ls_calls == 1 and self.fault == "existing":
                return subprocess.CompletedProcess(argv, 0,
                    "-rw-r--r-- shell shell 58 2026-10-10 10:00 old.probe\n", "")
            if self.path_ls_calls == 1 and self.fault == "ambiguous_absence":
                return subprocess.CompletedProcess(argv, 1, "", "permission denied\n")
            if self.path_ls_calls == 1:
                return subprocess.CompletedProcess(argv, 1, "",
                    f"{collector.REMOTE_PATH}: No such file or directory\n")
            if self.path_ls_calls == 2:
                mode = "-rwxr-xr-x" if self.fault == "metadata_mismatch" else "-rw-r--r--"
                return subprocess.CompletedProcess(argv, 0,
                    f"{mode} shell shell {len(collector.MARKER_BYTES)} 2026-10-10 10:00 {Path(collector.REMOTE_PATH).name}\n", "")
            if self.fault == "verify_present":
                return subprocess.CompletedProcess(argv, 0,
                    f"-rw-r--r-- shell shell {len(collector.MARKER_BYTES)} 2026-10-10 10:00 {Path(collector.REMOTE_PATH).name}\n", "")
            if self.fault == "verify_unknown":
                return subprocess.CompletedProcess(argv, 1, "", "permission denied\n")
            return subprocess.CompletedProcess(argv, 1, "",
                f"{collector.REMOTE_PATH}: No such file or directory\n")
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
    marker.chmod(0o644)
    manifest_path = tmp_path / "manifest.json"
    evidence_root = tmp_path / "evidence"
    monkeypatch.setattr(collector, "MARKER_PATH", marker)
    monkeypatch.setattr(collector, "MANIFEST_PATH", manifest_path)
    monkeypatch.setattr(collector, "EVIDENCE_ROOT", evidence_root)
    monkeypatch.setattr(collector, "REMOTE_PATH", "/data/local/tmp/claritylink_a0w_test.probe")
    doc = collector.manifest_template()
    doc["collector_source_sha256"] = hashlib.sha256(Path(collector.__file__).read_bytes()).hexdigest()
    doc["marker_sha256"] = hashlib.sha256(collector.MARKER_BYTES).hexdigest()
    doc["marker_md5"] = hashlib.md5(collector.MARKER_BYTES).hexdigest()
    manifest_path.write_text(json.dumps(doc, sort_keys=True, indent=2) + "\n")
    source_sha = doc["collector_source_sha256"]
    manifest_sha = hashlib.sha256(manifest_path.read_bytes()).hexdigest()
    return ["--execute-authorized-a0-write-delete", "--authorization-ref", "A0W-TEST-REF",
            "--expected-source-sha256", source_sha, "--expected-manifest-sha256", manifest_sha,
            "--observed-power-state", "on main honda screen", "--audio-state-before",
            "playing bluetooth music from my phone", "--stationary", "--parked",
            "--center-display-booted", "--cluster-normal", "--no-unexpected-warnings",
            "--confirm-intended-honda-target", "--exclusive-adb-window-confirmed"]


def test_default_and_dry_run_make_zero_adb_calls(tmp_path, capsys):
    calls = []
    assert collector.main([], runner=lambda *a, **k: calls.append(a)) == 2
    assert "NOT_AUTHORIZED" in capsys.readouterr().err
    assert collector.main(["--dry-run"], runner=lambda *a, **k: calls.append(a)) == 0
    assert calls == []
    assert "TARGET_REDACTED" in capsys.readouterr().out


def test_frozen_manifest_has_one_push_one_exact_rm_and_no_other_target_mutation():
    manifest = collector.manifest_template()
    commands = manifest["commands"]
    assert len(commands) == 8
    push = [entry for entry in commands if entry["id"] == "A0W-03"]
    cleanup = [entry for entry in commands if entry["id"] == "A0W-06"]
    assert len(push) == len(cleanup) == 1
    assert push[0]["argv"][-1] == collector.REMOTE_PATH
    assert cleanup[0]["argv"][-2:] == ["/system/bin/rm", collector.REMOTE_PATH]
    assert manifest["retries"] == 0 and manifest["fallbacks"] == []
    all_argv = " ".join(" ".join(entry["argv"]) for entry in commands)
    for forbidden in ("chmod", "mkdir", "touch", "dd", "cp", "mv", "install",
                      "setprop", "mount", "remount", "su", "reboot", "am", "pm", "kill", "-r", "-f", "*"):
        assert forbidden not in all_argv


def test_package_mismatch_stops_before_adb(tmp_path, monkeypatch, capsys):
    args = package_env(tmp_path, monkeypatch)
    args[args.index("--expected-manifest-sha256") + 1] = "0" * 64
    fake = FakeAdb()
    assert collector.main(args, runner=fake, input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 2
    assert fake.calls == []
    assert "A0W_AUTHORIZATION_BINDING_MISMATCH" in capsys.readouterr().err


def test_operator_gate_missing_stops_before_adb(tmp_path, monkeypatch, capsys):
    args = package_env(tmp_path, monkeypatch)
    args.remove("--parked")
    fake = FakeAdb()
    assert collector.main(args, runner=fake) == 2
    assert fake.calls == []
    assert "missing/invalid inputs" in capsys.readouterr().err


def test_exclusive_adb_window_is_a_required_operator_gate(tmp_path, monkeypatch, capsys):
    args = package_env(tmp_path, monkeypatch)
    args.remove("--exclusive-adb-window-confirmed")
    fake = FakeAdb()
    assert collector.main(args, runner=fake) == 2
    assert fake.calls == []
    assert "--exclusive-adb-window-confirmed" in capsys.readouterr().err


def test_happy_path_one_push_exact_cleanup_and_private_selector(tmp_path, monkeypatch):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb()
    assert collector.main(args, runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 0
    assert sum("push" in call for call in fake.calls) == 1
    assert len(fake.calls) == 8
    assert fake.calls[0] == ["adb", "devices"]
    assert all(call[1:3] == ["-s", "SERIAL_SECRET"] for call in fake.calls[1:])
    assert fake.calls[3] == ["adb", "-s", "SERIAL_SECRET", "push",
                             collector.MARKER_RELATIVE_PATH, collector.REMOTE_PATH]
    assert fake.calls[6] == ["adb", "-s", "SERIAL_SECRET", "shell",
                             "/system/bin/rm", collector.REMOTE_PATH]
    run_dir = next(collector.EVIDENCE_ROOT.iterdir())
    meta = json.loads((run_dir / "metadata.json").read_text())
    assert meta["decision"] == "A0W_PASS_FOR_REVIEW"
    assert meta["target_identity"] == "REDACTED"
    assert "SERIAL_SECRET" not in json.dumps(meta)
    assert meta["target_writes"] == 1
    assert meta["cleanup_verified"] is True
    assert meta["test_a"] == "NOT_AUTHORIZED"
    assert (run_dir / "target-identity.local.txt").read_text().strip() == "SERIAL_SECRET"


@pytest.mark.parametrize("inventory", [
    "List of devices attached\n",
    "List of devices attached\na\tdevice\nb\tdevice\n",
    "List of devices attached\na	offline\n",
    "List of devices attached\na	unauthorized\n",
])
def test_bad_inventory_stops_before_target_write(tmp_path, monkeypatch, inventory):
    args = package_env(tmp_path, monkeypatch)

    class InventoryFake(FakeAdb):
        def __call__(self, argv, **kwargs):
            if len(self.calls) == 0:
                self.calls.append(argv)
                return subprocess.CompletedProcess(argv, 0, inventory, "")
            return super().__call__(argv, **kwargs)

    fake = InventoryFake()
    assert collector.main(args, runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
    assert len(fake.calls) == 1
    assert fake.push_attempts == 0


@pytest.mark.parametrize("fault", ["existing", "ambiguous_absence"])
def test_preexistence_or_ambiguous_ls_stops_before_push(tmp_path, monkeypatch, fault):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb(fault=fault)
    assert collector.main(args, runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
    assert fake.push_attempts == 0
    assert len(fake.calls) == 3


def test_parent_metadata_mismatch_stops_before_marker_precheck_and_push(tmp_path, monkeypatch):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb(fault="parent_mismatch")
    assert collector.main(args, runner=fake) == 1
    assert len(fake.calls) == 2
    assert fake.push_attempts == 0


@pytest.mark.parametrize("fault", ["push_failure", "push_timeout", "metadata_mismatch", "md5_mismatch", "md5_failure"])
def test_transfer_or_verification_failure_still_runs_exact_cleanup(tmp_path, monkeypatch, fault):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb(fault=fault)
    assert collector.main(args, runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
    assert fake.push_attempts == 1
    assert any(call[-2:] == ["/system/bin/rm", collector.REMOTE_PATH] for call in fake.calls)
    assert sum("push" in call for call in fake.calls) == 1
    flattened = " ".join(" ".join(call) for call in fake.calls)
    assert all(value not in flattened for value in ("chmod", "kill", "su", "reboot", "am ", "pm "))


@pytest.mark.parametrize("fault", ["verify_present", "verify_unknown"])
def test_absence_verification_failure_is_hard_cleanup_blocker(tmp_path, monkeypatch, fault):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb(fault=fault)
    assert collector.main(args, runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
    run_dir = next(collector.EVIDENCE_ROOT.iterdir())
    meta = json.loads((run_dir / "metadata.json").read_text())
    assert meta["decision"] == "A0W_CLEANUP_NOT_VERIFIED"
    assert meta["cleanup_verified"] is False
    assert sum("/system/bin/rm" in call for call in fake.calls) == 1


def test_rm_failure_is_not_pass_even_if_absence_is_observed(tmp_path, monkeypatch):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb(fault="rm_failure")
    assert collector.main(args, runner=fake,
                          input_fn=lambda _: "STOCK_STATE_UNCHANGED") == 1
    run_dir = next(collector.EVIDENCE_ROOT.iterdir())
    meta = json.loads((run_dir / "metadata.json").read_text())
    assert meta["decision"] == "A0W_STOP_CONDITION"
    assert meta["cleanup_verified"] is True


def test_post_run_operator_change_is_stop_after_verified_cleanup(tmp_path, monkeypatch):
    args = package_env(tmp_path, monkeypatch)
    fake = FakeAdb()
    assert collector.main(args, runner=fake,
                          input_fn=lambda _: "audio changed") == 1
    run_dir = next(collector.EVIDENCE_ROOT.iterdir())
    meta = json.loads((run_dir / "metadata.json").read_text())
    assert meta["decision"] == "A0W_STOP_CONDITION"
    assert meta["cleanup_verified"] is True
