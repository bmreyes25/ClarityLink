from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess

import pytest

from tools import r7e6_test_a_collector as test_a
from tools import r7e7g_phase_r_collector as phase_r
from tools import r7e7g_test_a_wet_rehearsal as rehearsal
from tools import r7e7g_recovery_decision_sim as recovery
from tests.tools.test_r7e6_test_a_collector import FakeADB as LegacyFakeADB
from tests.tools.test_r7e6_test_a_collector import package as test_a_package


def test_full_frozen_collector_lifecycle_and_manifest_trace(test_a_package):
    fake, result = rehearsal.run_cycle()
    assert result["decision"] == "TEST_A_PASS_FOR_REVIEW"
    assert [fake._normalized(call) for call in fake.calls] == test_a.command_plan()
    assert (fake.transfers, fake.executions, fake.cleanups) == (1, 2, 1)
    assert not fake.file_present and not fake.running


def test_fifty_fresh_full_collector_cycles(test_a_package):
    cycles = [rehearsal.run_cycle()[0] for _ in range(50)]
    assert len(cycles) == 50
    assert sum(fake.transfers for fake in cycles) == 50
    assert sum(fake.executions for fake in cycles) == 100
    assert sum(fake.cleanups for fake in cycles) == 50
    assert all(len(fake.calls) == 13 and not fake.file_present
               and not fake.running and fake.unknown_commands == 0 for fake in cycles)


def test_rehearsal_rejects_foreign_transport_or_out_of_order_command():
    fake = rehearsal.FakeADB()
    with pytest.raises(rehearsal.ContractFailure):
        fake(["adb", "devices"], capture_output=True, text=True,
             check=False, cwd=test_a.ROOT)
    with pytest.raises(rehearsal.ContractFailure):
        fake([rehearsal.FAKE_ADB, "devices"], capture_output=True, text=True,
             check=False, cwd=test_a.ROOT)
    assert fake.calls == []


@pytest.mark.parametrize("condition", ["empty_process_sentinel", "live_process", "procfs_unavailable"])
def test_simulated_uncertain_pid_state_stops_without_self_test_or_cleanup(
        test_a_package, condition):
    test_a_package.serial = rehearsal.SERIAL
    test_a_package.adb = rehearsal.FAKE_ADB
    fake = rehearsal.FakeADB(failure=condition)
    with pytest.raises(test_a.Blocked, match="TEST_A_PROCESS_STATE_UNCERTAIN"):
        test_a.execute(test_a_package, runner=fake, confirm_stock_state=lambda: True)
    assert len(fake.calls) == 9
    assert fake.transfers == 1 and fake.executions == 1 and fake.cleanups == 0
    assert fake.file_present
    assert bool(fake.running) is (condition == "live_process")
    assert fake.procfs_controls_available is (condition != "procfs_unavailable")


@pytest.mark.parametrize("stage,mutation", [
    (0, "wrong_version"), (0, "unexpected_stderr"), (0, "host_timeout"),
    (1, "offline"), (1, "multiple"), (1, "malformed"),
    (2, "wrong_parent_owner"), (2, "empty_parent"),
    (3, "ambiguous_enoent"), (3, "permission_denied"),
    (4, "wrong_push_bytes"), (4, "wrong_push_source"),
    (4, "duplicate_push_lines"), (4, "host_timeout"),
    (5, "wrong_remote_owner"), (5, "wrong_remote_group"),
    (5, "wrong_remote_basename"), (5, "remote_symlink"),
    (6, "wrong_md5_path"), (6, "duplicate_md5"), (6, "empty_md5"),
    (7, "missing_version"), (7, "wrong_api"), (7, "wrong_abi"),
    (7, "missing_supervisor_reap"), (7, "duplicate_status"),
    (8, "empty_process_sentinel"), (8, "host_timeout"),
    (9, "missing_self_test_pass"), (9, "nonzero_guest"), (9, "host_timeout"),
    (10, "duplicate_sentinel"), (11, "cleanup_failure"), (11, "host_timeout"),
    (12, "final_path_present"), (12, "host_timeout"),
])
def test_fault_matrix_rejects_mutated_stage_without_retry(test_a_package, stage, mutation):
    fake = LegacyFakeADB()
    injected = False

    def runner(argv, **kwargs):
        nonlocal injected
        if len(fake.calls) == stage and mutation == "host_timeout":
            fake.calls.append(argv.copy())
            injected = True
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        result = fake(argv, **kwargs)
        if len(fake.calls) - 1 != stage or injected:
            return result
        injected = True
        out, err, rc = result.stdout, result.stderr, result.returncode
        replacements = {
            "wrong_version": ("Version 0.0.0\n", err, rc),
            "unexpected_stderr": (out, "unexpected warning\n", rc),
            "offline": ("List of devices attached\nTESTSER\toffline\n", err, rc),
            "multiple": ("List of devices attached\nTESTSER\tdevice\nOTHER\tdevice\n", err, rc),
            "malformed": ("List of devices attached\nmalformed row\n", err, rc),
            "wrong_parent_owner": (out.replace("shell    shell", "root     shell"), err, rc),
            "empty_parent": ("", err, rc),
            "ambiguous_enoent": (out + "extra\n", err, rc),
            "permission_denied": ("Permission denied\n", err, 1),
            "wrong_push_bytes": (out, err.replace(f"({test_a.SIZE} bytes", "(1 bytes"), rc),
            "wrong_push_source": (out, err.replace("build/r7e6/test-a/claritylink-target-diag", "other"), rc),
            "duplicate_push_lines": (out, err + err, rc),
            "wrong_remote_owner": (out.replace("shell shell", "root shell"), err, rc),
            "wrong_remote_group": (out.replace("shell shell", "shell root"), err, rc),
            "wrong_remote_basename": (out.replace(Path(test_a.REMOTE).name, "other"), err, rc),
            "remote_symlink": (out.replace("-r-xr-xr-x", "lrwxrwxrwx"), err, rc),
            "wrong_md5_path": (out.replace(test_a.REMOTE, "/data/local/tmp/other"), err, rc),
            "duplicate_md5": (out + out, err, rc),
            "empty_md5": ("", err, rc),
            "missing_version": (out.replace("CLARITYLINK_DIAG_VERSION=1.0.0\n", ""), err, rc),
            "wrong_api": (out.replace("API_TARGET=17", "API_TARGET=18"), err, rc),
            "wrong_abi": (out.replace("ABI=armeabi-v7a", "ABI=x86"), err, rc),
            "missing_supervisor_reap": (out.replace("SUPERVISOR_CHILD_REAPED", "NO_REAP"), err, rc),
            "duplicate_status": (out + "__R7E6_STATUS:0\n", err, rc),
            "empty_process_sentinel": ("", err, rc),
            "missing_self_test_pass": (out.replace("SELF_TEST_PASS\n", ""), err, rc),
            "nonzero_guest": (out.replace("__R7E6_STATUS:0", "__R7E6_STATUS:1"), err, rc),
            "duplicate_sentinel": (out + out, err, rc),
            "cleanup_failure": (out, err, 1),
            "final_path_present": (f"-r-xr-xr-x shell shell {test_a.SIZE} 2026-10-11 {Path(test_a.REMOTE).name}\n", err, rc),
        }
        new_out, new_err, new_rc = replacements[mutation]
        return subprocess.CompletedProcess(argv, new_rc, new_out, new_err)

    with pytest.raises(test_a.Blocked) as blocked:
        test_a.execute(test_a_package, runner=runner, confirm_stock_state=lambda: True)
    assert injected
    plan = test_a.command_plan()
    normalized = []
    for call in fake.calls:
        row = call[1:].copy()
        if row[:2] == ["-s", "TESTSER"]:
            row[1] = "<EXACT_SERIAL>"
        if row and "R7E6_PIDS_ABSENT:" in row[-1]:
            row[-1] = re.sub(r"(?<!\d)42(?!\d)", "<CHILD_PID>", row[-1])
            row[-1] = re.sub(r"(?<!\d)41(?!\d)", "<PARENT_PID>", row[-1])
        normalized.append(row)
    if stage <= 3 or mutation == "host_timeout" or stage >= 10:
        expected = plan[:stage + 1]
    elif stage <= 6:
        expected = plan[:stage + 1] + plan[11:13]
    elif stage == 7:
        expected = (plan[:8] if mutation == "missing_supervisor_reap"
                    else plan[:9] + plan[11:13])
    elif stage == 8:
        expected = plan[:9]
    else:
        expected = plan[:11] + plan[11:13]
    assert normalized == expected
    if mutation == "host_timeout":
        assert "WATCHDOG_OR_TRANSPORT_ANOMALY" in str(blocked.value)
    elif stage in (8, 10):
        assert "TEST_A_PROCESS_STATE_UNCERTAIN" in str(blocked.value)
    assert sum("push" in call for call in fake.calls) <= 1
    assert sum("/system/bin/rm" in call for call in fake.calls) <= 1
    if mutation == "host_timeout" and stage < 11:
        assert not any("/system/bin/rm" in call for call in fake.calls)


@pytest.mark.parametrize("mutation", [
    "collector_auth_sha", "manifest_auth_sha", "artifact_sha", "artifact_md5",
    "artifact_size", "staging_mode", "symlink_staging", "manifest_version",
    "manifest_command_plan",
])
def test_package_fault_matrix_makes_zero_adb_calls(test_a_package, monkeypatch, mutation):
    fake = LegacyFakeADB()
    if mutation == "collector_auth_sha":
        test_a_package.authorized_collector_sha256 = "0" * 64
    elif mutation == "manifest_auth_sha":
        test_a_package.authorized_manifest_sha256 = "0" * 64
    elif mutation == "artifact_sha":
        monkeypatch.setattr(test_a, "SHA256", "0" * 64)
    elif mutation == "artifact_md5":
        monkeypatch.setattr(test_a, "MD5", "0" * 32)
    elif mutation == "artifact_size":
        monkeypatch.setattr(test_a, "SIZE", test_a.SIZE + 1)
    elif mutation == "staging_mode":
        test_a.ARTIFACT.chmod(0o755)
    elif mutation == "symlink_staging":
        original = test_a.ARTIFACT
        link = original.parent / "symlink-artifact"
        link.symlink_to(original)
        monkeypatch.setattr(test_a, "ARTIFACT", link)
    else:
        manifest = json.loads(test_a.MANIFEST.read_text())
        if mutation == "manifest_version":
            manifest["manifest_version"] = "WRONG"
        else:
            manifest["commands"][0] = ["extra"]
        test_a.MANIFEST.write_text(json.dumps(manifest))
    with pytest.raises(test_a.Blocked):
        test_a.execute(test_a_package, runner=fake, confirm_stock_state=lambda: True)
    assert fake.calls == []


class PhaseRFake:
    def __init__(self, file_line: str | None = None, digest: str | None = None,
                 inventory: str | None = None, parent: str | None = None,
                 timeout_at: int | None = None) -> None:
        self.file_line = file_line
        self.digest = digest
        self.inventory = inventory
        self.parent = parent
        self.timeout_at = timeout_at
        self.calls: list[list[str]] = []

    def __call__(self, argv: list[str], **kwargs):
        expected = phase_r.command_plan()
        normalized = argv[1:].copy()
        if normalized[:2] == ["-s", "TESTSER"]:
            normalized[1] = "<EXACT_SERIAL>"
        assert argv[0] == "FAKE_ADB_ONLY"
        assert len(self.calls) < len(expected) and normalized == expected[len(self.calls)]
        self.calls.append(argv.copy())
        if self.timeout_at == len(self.calls):
            raise subprocess.TimeoutExpired(argv, kwargs["timeout"])
        if argv[-1] == "version":
            out = f"Android Debug Bridge version 1.0.41\nVersion {test_a.ADB_VERSION}\n"
        elif argv[-1] == "devices":
            out = self.inventory if self.inventory is not None else "List of devices attached\nTESTSER\tdevice\n"
        elif argv[-1] == test_a.PARENT:
            out = self.parent if self.parent is not None else "drwxrwx--x shell shell 2026-10-11 09:20 tmp\r\n"
        elif argv[-2:] == ["ls", "-ld"]:
            raise AssertionError("unexpected command")
        elif argv[-1] == test_a.REMOTE and argv[-2] == "-ld":
            out = (self.file_line if self.file_line is not None
                   else f"{test_a.REMOTE}: No such file or directory\n")
        elif argv[-2:] == ["/system/bin/md5", test_a.REMOTE]:
            out = (self.digest if self.digest is not None
                   else f"{test_a.MD5}  {test_a.REMOTE}\n")
        else:
            raise AssertionError(f"unapproved Phase R command: {argv}")
        assert "push" not in argv and "/system/bin/rm" not in argv
        return subprocess.CompletedProcess(argv, 0, out, "")


@pytest.fixture
def phase_r_package(tmp_path, monkeypatch):
    monkeypatch.setattr(phase_r, "ROOT", tmp_path)
    manifest = tmp_path / "research/runtime/r7e7g-phase-r-manifest.json"
    manifest.parent.mkdir(parents=True)
    manifest.write_bytes(phase_r.MANIFEST.read_bytes())
    monkeypatch.setattr(phase_r, "MANIFEST", manifest)
    return phase_r.parser().parse_args([
        "--execute-authorized-phase-r", "--authorized-collector-sha256",
        test_a.sha(Path(phase_r.__file__).resolve()),
        "--authorized-manifest-sha256", test_a.sha(manifest),
        "--serial", "TESTSER", "--adb", "FAKE_ADB_ONLY", "--stationary",
        "--parked", "--display-booted", "--cluster-normal", "--no-warnings",
        "--exclusive-adb-window",
    ])


def test_phase_r_default_and_dry_run_never_invoke_adb(monkeypatch, capsys):
    monkeypatch.setattr(phase_r.subprocess, "run", lambda *_a, **_k: pytest.fail("ADB called"))
    assert phase_r.main([]) == 0
    assert capsys.readouterr().out.strip() == "PHASE_R_NOT_AUTHORIZED"
    assert phase_r.main(["--dry-run"]) == 0
    assert json.loads(capsys.readouterr().out)["adb_operations"] == 0


def test_phase_r_imported_helper_identity_mismatch_makes_zero_adb_calls(
        phase_r_package, monkeypatch):
    monkeypatch.setattr(phase_r, "EXPECTED_TEST_A_COLLECTOR_SHA256", "0" * 64)
    fake = PhaseRFake()
    with pytest.raises(phase_r.PhaseRStop, match="IMPORTED_TEST_A_COLLECTOR_IDENTITY_MISMATCH"):
        phase_r.execute(phase_r_package, runner=fake)
    assert fake.calls == []


def test_phase_r_exact_absence_stops_without_hash(phase_r_package, capsys):
    fake = PhaseRFake()
    assert phase_r.execute(phase_r_package, runner=fake) == "EXACT_PATH_ABSENT"
    result = json.loads(capsys.readouterr().out)
    assert result["commands"] == 4
    assert all("/system/bin/md5" not in call for call in fake.calls)
    assert all("/system/bin/rm" not in call for call in fake.calls)
    assert [call[1:2] + (["<EXACT_SERIAL>"] if call[1:2] == ["-s"] else [])
            + call[3:] if call[1:2] == ["-s"] else call[1:] for call in fake.calls] == phase_r.command_plan()[:4]


def test_phase_r_expected_present_hashes_once_and_stops(phase_r_package, capsys):
    line = f"-r-xr-xr-x shell shell {test_a.SIZE} 2026-10-11 {Path(test_a.REMOTE).name}\r\n"
    fake = PhaseRFake(file_line=line)
    assert phase_r.execute(phase_r_package, runner=fake) == "EXPECTED_REGULAR_FILE_PRESENT"
    assert json.loads(capsys.readouterr().out)["commands"] == 5
    assert sum("/system/bin/md5" in call for call in fake.calls) == 1
    assert len(fake.calls) == len(phase_r.command_plan())


@pytest.mark.parametrize("line", [
    "", "Permission denied\n", "unexpected output\n",
    f"lrwxrwxrwx shell shell {test_a.SIZE} 2026-10-11 {Path(test_a.REMOTE).name} -> other\n",
    f"drwxr-xr-x shell shell {test_a.SIZE} 2026-10-11 {Path(test_a.REMOTE).name}\n",
    f"-rwxr-xr-x shell shell {test_a.SIZE} 2026-10-11 {Path(test_a.REMOTE).name}\n",
    f"-r-xr-xr-x root shell {test_a.SIZE} 2026-10-11 {Path(test_a.REMOTE).name}\n",
    f"-r-xr-xr-x shell root {test_a.SIZE} 2026-10-11 {Path(test_a.REMOTE).name}\n",
    f"-r-xr-xr-x shell shell 1 2026-10-11 {Path(test_a.REMOTE).name}\n",
    "/data/local/tmp/other: No such file or directory\n",
])
def test_phase_r_rejects_unexpected_path_state_without_hash(phase_r_package, line, capsys):
    fake = PhaseRFake(file_line=line)
    assert phase_r.execute(phase_r_package, runner=fake) != "EXPECTED_REGULAR_FILE_PRESENT"
    capsys.readouterr()
    assert len(fake.calls) == 4


def test_phase_r_mismatched_digest_never_deletes(phase_r_package, capsys):
    line = f"-r-xr-xr-x shell shell {test_a.SIZE} 2026-10-11 {Path(test_a.REMOTE).name}\n"
    fake = PhaseRFake(file_line=line, digest=f"{'0' * 32}  {test_a.REMOTE}\n")
    assert phase_r.execute(phase_r_package, runner=fake) == "UNEXPECTED_FILE_STATE"
    capsys.readouterr()
    assert len(fake.calls) == 5


def test_phase_r_wrong_identity_and_timeout_stop(phase_r_package, capsys):
    fake = PhaseRFake(inventory="List of devices attached\nOTHER\tdevice\n")
    assert phase_r.execute(phase_r_package, runner=fake) == "TARGET_IDENTITY_UNCERTAIN"
    capsys.readouterr()
    assert len(fake.calls) == 2
    fake = PhaseRFake(timeout_at=3)
    assert phase_r.execute(phase_r_package, runner=fake) == "TIMEOUT_OR_TRANSPORT_UNKNOWN"
    capsys.readouterr()
    assert len(fake.calls) == 3


def test_recovery_decision_tree_requires_separate_current_process_basis():
    wrong = recovery.SimulatedRecovery("EXACT_PATH_ABSENT", exact_path="/wrong",
                                       target_identity_confirmed=False)
    assert wrong.run() == "RECOVERY_STOP_TARGET_OR_PATH_IDENTITY_UNKNOWN"
    absent = recovery.SimulatedRecovery("EXACT_PATH_ABSENT")
    assert absent.run() == "PHASE_R_EXACT_PATH_ABSENT_NO_CLEANUP"
    assert absent.removals == 0
    present = recovery.SimulatedRecovery("EXPECTED_REGULAR_FILE_PRESENT", file_present=True)
    assert present.run() == "PHASE_C_NO_GO"
    assert present.removals == 0
    unexpected = recovery.SimulatedRecovery("UNEXPECTED_FILE_STATE", file_present=True)
    assert unexpected.run() == "RECOVERY_STOP_UNEXPECTED_OR_UNKNOWN_STATE"
    assert unexpected.removals == 0
    present.current_process_safety_independently_reviewed = True
    assert present.run() == "PHASE_C_AWAITING_SEPARATE_AUTHORIZATION"
    present.phase_c_separately_authorized = True
    assert present.run() == "PHASE_C_SIMULATED_EXACT_REMOVAL_AND_ABSENCE"
    assert present.removals == 1 and not present.file_present
    assert present.run() == "PHASE_C_NO_GO_STATE_CHANGED"
    assert present.removals == 1
