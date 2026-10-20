from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
import subprocess

import pytest

from tests.tools.local_tool_gate import require_local_tools

require_local_tools(__file__, "r7e6_test_a_collector.py")

from tools import r7e6_test_a_collector as collector


class FakeADB:
    def __init__(self, failure: str | None = None, devices: str | None = None) -> None:
        self.failure = failure
        self.devices = devices or "List of devices attached\nTESTSER\tdevice\n"
        self.calls: list[list[str]] = []
        self.existing = failure in {"existing", "existing_symlink", "existing_directory"}

    def __call__(self, argv, **kwargs):
        self.calls.append(argv)
        out = ""
        code = 0
        if argv[-1:] == ["version"]:
            out = "Android Debug Bridge version 1.0.41\nVersion 37.0.1-15733141\n"
        elif argv[-1:] == ["devices"]:
            out = self.devices
        elif "push" in argv:
            if self.failure == "push":
                code = 1
            else:
                self.existing = True
                artifact_source = str(collector.ARTIFACT.relative_to(collector.ROOT))
                return subprocess.CompletedProcess(
                    argv, 0, "", f"{artifact_source}: 1 file pushed, 0 skipped. "
                    f"1 MB/s ({collector.SIZE} bytes in 0.01s)\n")
        elif argv[-3:] == ["ls", "-ld", collector.PARENT]:
            out = ("drwxrwx--x shell    shell             2026-10-11 09:20 tmp\r\n"
                   if self.failure != "destination" else "drwx------ root root 2026-10-11 09:20 tmp\n")
            if self.failure == "destination_extra":
                out += "unexpected extra line\n"
        elif argv[-3:] == ["ls", "-ld", collector.REMOTE]:
            if not self.existing:
                code = 0 if self.failure != "absence_status_1" else 1
                out = f"{collector.REMOTE}: No such file or directory\n"
                if self.failure == "absence_empty":
                    out = ""
                elif self.failure == "absence_permission":
                    out = "Permission denied\n"
                elif self.failure == "absence_command_missing":
                    out = "/system/bin/sh: ls: not found\n"
                elif self.failure == "absence_ambiguous":
                    out += "warning: extra response\n"
                elif self.failure == "absence_other_path":
                    out = "/data/local/tmp/other: No such file or directory\n"
                elif self.failure == "absence_prefixed":
                    out = f"ls: {collector.REMOTE}: No such file or directory\n"
                elif self.failure == "absence_stderr":
                    return subprocess.CompletedProcess(argv, 0, "", "permission denied\n")
                elif self.failure == "absence_extra_blank":
                    out += "\n"
                elif self.failure == "absence_whitespace":
                    out = " " + out
            elif self.failure == "existing_symlink":
                out = f"lrwxrwxrwx shell shell 1 2026-10-11 {Path(collector.REMOTE).name} -> marker\n"
            elif self.failure == "existing_directory":
                out = f"drwxr-xr-x shell shell 0 2026-10-11 {Path(collector.REMOTE).name}\n"
            else:
                out = f"-r--r--r-- shell shell {collector.SIZE} 2026-10-11 {Path(collector.REMOTE).name}\n"
        elif argv[-3:] == ["ls", "-l", collector.REMOTE]:
            mode = "-r-xr-xr-x"
            if self.failure in {"mode", "writable"}:
                mode = "-rwxr-xr-x"
            elif self.failure == "nonexecutable":
                mode = "-rw-r--r--"
            size = 42 if self.failure == "size" else collector.SIZE
            out = f"{mode} shell shell {size} 2026-10-11 {Path(collector.REMOTE).name}\n"
            if self.failure == "metadata_warning":
                out += "warning: unexpected output\n"
        elif argv[-2:] == ["/system/bin/md5", collector.REMOTE]:
            out = ("00000000000000000000000000000000\n" if self.failure == "md5"
                   else f"{collector.MD5}  {collector.REMOTE}\n")
        elif argv[-1:] == ["/system/bin/rm"] or argv[-2:] == ["/system/bin/rm", collector.REMOTE]:
            if self.failure == "rm":
                code = 1
            elif self.failure == "final_absent":
                pass
            else:
                self.existing = False
        elif argv[-1:] and "R7E6_PIDS_ABSENT" in argv[-1] and "test -d /proc/$$" in argv[-1]:
            assert argv[-2] == "shell"
            assert "sh" not in argv[-3:]
            match = re.search(r"R7E6_PIDS_ABSENT:(\d+):(\d+)", argv[-1])
            assert match
            assert "test -r /proc/$$/stat" in argv[-1]
            assert "test -r /proc/self/stat" in argv[-1]
            if self.failure in {"process_present", "procfs_unavailable",
                                "procfs_self_unreadable", "procfs_shell_stat_unreadable"}:
                out = "PROCESS_REMAINS\n"
            elif self.failure == "process_extra":
                out = f"R7E6_PIDS_ABSENT:{match.group(1)}:{match.group(2)}\nEXTRA\n"
            elif self.failure == "process_duplicate":
                out = (f"R7E6_PIDS_ABSENT:{match.group(1)}:{match.group(2)}\n"
                       f"R7E6_PIDS_ABSENT:{match.group(1)}:{match.group(2)}\n")
            elif self.failure == "process_empty":
                out = ""
            elif self.failure == "process_bad_sentinel":
                out = f"R7E6_PIDS_ABSENT:{match.group(1)}:999\n"
            else:
                out = f"R7E6_PIDS_ABSENT:{match.group(1)}:{match.group(2)}\n"
            if self.failure == "process_stderr":
                return subprocess.CompletedProcess(argv, 0, "", "remote shell warning\n")
        elif argv[-1:] and collector.REMOTE in argv[-1]:
            mode = "--version" if "--version" in argv[-1] else "--self-test"
            if self.failure == f"{mode}_timeout":
                raise subprocess.TimeoutExpired(argv, kwargs.get("timeout"))
            status = "1" if self.failure == mode else "0"
            out = ("SUPERVISOR_CHILD_STARTED parent_pid=41 child_pid=42\n"
                   "CLARITYLINK_DIAG_VERSION=1.0.0\nBUILD_SHA=cd1d47b51f84e7f0c79a28f079f620fcd4ee0631\n"
                   "API_TARGET=17\nABI=armeabi-v7a\n")
            if mode == "--self-test":
                out += "RESOURCE_COUNTS final=0\nSELF_TEST_PASS\n"
            out += "SUPERVISOR_CHILD_REAPED parent_pid=41 child_pid=42\n"
            if self.failure == "ambiguous_process":
                out += "SUPERVISOR_CHILD_STARTED parent_pid=43 child_pid=44\n"
                out += "SUPERVISOR_CHILD_REAPED parent_pid=43 child_pid=44\n"
            out += f"__R7E6_STATUS:{status}\n"
        return subprocess.CompletedProcess(argv, code, out, "")


@pytest.fixture
def package(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "ROOT", tmp_path)
    artifact = tmp_path / "build/r7e6/test-a/claritylink-target-diag"
    artifact.parent.mkdir(parents=True)
    artifact.write_bytes(b"fake diagnostic bytes for collector fixture")
    artifact.chmod(0o555)
    monkeypatch.setattr(collector, "ARTIFACT", artifact)
    monkeypatch.setattr(collector, "SIZE", artifact.stat().st_size)
    monkeypatch.setattr(collector, "SHA256", hashlib.sha256(artifact.read_bytes()).hexdigest())
    monkeypatch.setattr(collector, "MD5", hashlib.md5(artifact.read_bytes(), usedforsecurity=False).hexdigest())
    manifest = tmp_path / "research/runtime/r7e6-test-a-plan-manifest.json"
    manifest.parent.mkdir(parents=True)
    template = collector.manifest_template()
    source = Path(collector.__file__).resolve()
    template["collector_source_sha256"] = hashlib.sha256(source.read_bytes()).hexdigest()
    manifest.write_text(json.dumps(template, indent=2, sort_keys=True) + "\n")
    monkeypatch.setattr(collector, "MANIFEST", manifest)
    args = collector.parser().parse_args([
        "--execute-authorized-test-a", "--authorized-collector-sha256", template["collector_source_sha256"],
        "--authorized-manifest-sha256", hashlib.sha256(manifest.read_bytes()).hexdigest(),
        "--serial", "TESTSER", "--stationary", "--parked", "--display-booted",
        "--cluster-normal", "--no-warnings", "--power-state", "ACC observed",
        "--audio-state", "muted observed",
        "--exclusive-adb-window",
    ])
    return args


def test_default_is_not_authorized_and_dry_run_is_zero_adb(monkeypatch, capsys):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("ADB must not run")
    monkeypatch.setattr(collector.subprocess, "run", forbidden)
    assert collector.main([]) == 0
    assert capsys.readouterr().out.strip() == "NOT_AUTHORIZED"
    assert collector.main(["--dry-run"]) == 0
    dry = json.loads(capsys.readouterr().out)
    assert dry["decision"] == "DRY_RUN_NO_ADB"
    assert dry["adb_operations"] == 0


@pytest.mark.parametrize("output,expected", [
    ("drwxrwx--x shell    shell             2026-10-11 09:20 tmp\\r\\n", True),
    ("drwxrwx--x shell shell 2048 2026-10-11 /data/local/tmp\\n", True),
    ("drwx------ shell shell 2026-10-11 09:20 tmp\\n", False),
    ("drwxrwx--x root shell 2026-10-11 09:20 tmp\\n", False),
    ("drwxrwx--x shell root 2026-10-11 09:20 tmp\\n", False),
    ("drwxrwx--x shell shell 2026-10-11 09:20 other\\n", False),
    ("drwxrwx--x shell shell 2026-10-11 09:20 tmp\\nextra\\n", False),
    ("", False),
])
def test_parent_metadata_accepts_legacy_android_format_without_weakening_identity(output, expected):
    assert collector._valid_parent_metadata(output.replace("\\r", "").replace("\\n", "\n")) is expected


def test_remote_regular_file_parser_accepts_captured_a0wr_toolbox_spacing_and_crlf():
    observed = ("-r--r--r-- shell    shell          59 2026-10-11 08:48 "
                "claritylink_a0wr_r7e5c_5d73b2c42a7e19f0.probe\\r\\n")
    parsed = collector._mode(observed.replace("\\r", "").replace("\\n", "\n"))
    assert parsed == ("-r--r--r--", "shell", "shell", 59,
                      "claritylink_a0wr_r7e5c_5d73b2c42a7e19f0.probe")


@pytest.mark.parametrize("output", [
    "lrwxrwxrwx shell shell 59 2026-10-11 08:48 marker -> target\\n",
    "drwxr-xr-x shell shell 59 2026-10-11 08:48 marker\\n",
    "-r-sr-xr-x shell shell 59 2026-10-11 08:48 marker\\n",
    "-r--r--r-- shell shell 2026-10-11 08:48 marker\\n",
    "-r--r--r-- shell shell 59 2026-10-11 08:48 marker\\nextra\\n",
    "",
])
def test_remote_regular_file_parser_rejects_ambiguous_or_unrecognized_metadata(output):
    assert collector._mode(output.replace("\\n", "\n")) is None


def test_push_parser_accepts_historical_a0wr_stderr_transfer_format():
    stderr = ("build/r7e5c/a0wr/claritylink-a0wr-marker.txt: 1 file pushed, "
              "0 skipped. 0.6 MB/s (59 bytes in 0.000s)\\n")
    assert collector._push_succeeded(
        "", stderr.replace("\\n", "\n"),
        "build/r7e5c/a0wr/claritylink-a0wr-marker.txt", 59)


@pytest.mark.parametrize("stdout,stderr", [
    ("", "build/r7e5c/a0wr/marker: 1 file pushed, 1 skipped. 0.6 MB/s (59 bytes in 0.1s)\\n"),
    ("", "build/r7e5c/a0wr/other: 1 file pushed, 0 skipped. 0.6 MB/s (59 bytes in 0.1s)\\n"),
    ("", "build/r7e5c/a0wr/marker: 1 file pushed, 0 skipped. 0.6 MB/s (58 bytes in 0.1s)\\n"),
    ("unexpected\\n", "build/r7e5c/a0wr/marker: 1 file pushed, 0 skipped. 0.6 MB/s (59 bytes in 0.1s)\\n"),
])
def test_push_parser_rejects_skips_wrong_source_size_or_extra_output(stdout, stderr):
    assert not collector._push_succeeded(
        stdout.replace("\\n", "\n"), stderr.replace("\\n", "\n"),
        "build/r7e5c/a0wr/marker.txt", 59)


def test_complete_fake_lifecycle_is_exact_and_no_retry_or_fallback(package, capsys):
    fake = FakeADB()
    assert collector.execute(package, runner=fake, confirm_stock_state=lambda: True) == 0
    result = json.loads(capsys.readouterr().out)
    assert result["decision"] == "TEST_A_PASS_FOR_REVIEW"
    assert sum("push" in call for call in fake.calls) == 1
    flattened = " ".join(" ".join(call) for call in fake.calls)
    for forbidden in ("chmod", "ps", "killall", "pkill", "Display1", "CarPlay", "Test B"):
        assert forbidden not in flattened
    assert all("*" not in token for call in fake.calls for token in call)


@pytest.mark.parametrize("devices", [
    "List of devices attached\n",
    "List of devices attached\nTESTSER\tdevice\nOTHER\tdevice\n",
    "List of devices attached\nOTHER\tdevice\n",
    "List of devices attached\nTESTSER\tdevice\nwarning: extra row\n",
    "TESTSER\tdevice\n",
])
def test_target_zero_multiple_or_mismatch_fails_closed(package, devices):
    fake = FakeADB(devices=devices)
    with pytest.raises(collector.Blocked):
        collector.execute(package, runner=fake, confirm_stock_state=lambda: True)
    assert not any("push" in call for call in fake.calls)


@pytest.mark.parametrize("failure", ["destination", "destination_extra", "existing", "push", "size", "mode", "writable",
                                      "nonexecutable", "metadata_warning", "md5", "--version", "--version_timeout",
                                      "--self-test", "--self-test_timeout", "process_present",
                                      "procfs_unavailable", "procfs_self_unreadable",
                                      "procfs_shell_stat_unreadable", "process_empty",
                                      "process_stderr",
                                      "process_bad_sentinel", "process_duplicate", "process_extra",
                                      "ambiguous_process", "rm", "final_absent"])
def test_fault_fixture_stops_or_cleans_exactly_once(package, failure):
    fake = FakeADB(failure=failure)
    with pytest.raises(collector.Blocked):
        collector.execute(package, runner=fake, confirm_stock_state=lambda: True)
    if failure in {"destination", "destination_extra", "existing", "existing_symlink", "existing_directory"}:
        assert not any("push" in call for call in fake.calls)
    if failure.endswith("_timeout"):
        # Host timeout anomaly must issue no rollback or subsequent target command.
        target_calls = [c for c in fake.calls if "shell" in c]
        assert target_calls and "rm" not in target_calls[-1]
    if failure in {"rm", "final_absent"}:
        assert sum("/system/bin/rm" in call for call in fake.calls) == 1


@pytest.mark.parametrize("failure", ["absence_empty", "absence_permission", "absence_command_missing",
                                      "absence_ambiguous", "absence_other_path", "absence_stderr",
                                      "absence_extra_blank", "absence_whitespace", "existing",
                                      "absence_prefixed", "existing_symlink", "existing_directory"])
def test_legacy_absence_gate_requires_exact_enoent_before_push(package, failure):
    fake = FakeADB(failure=failure)
    with pytest.raises(collector.Blocked, match="TEST_A_REMOTE_PATH_STATE_UNCERTAIN"):
        collector.execute(package, runner=fake, confirm_stock_state=lambda: True)
    assert not any("push" in call for call in fake.calls)


def test_legacy_remote_failure_with_host_zero_and_exact_enoent_is_accepted(package):
    fake = FakeADB()
    result = subprocess.CompletedProcess(["adb"], 0,
        f"{collector.REMOTE}: No such file or directory\n", "")
    assert collector._is_exact_enoent(result.stdout, collector.REMOTE, result.stderr, result.returncode)


def test_host_zero_and_empty_remote_failure_is_not_absence():
    assert not collector._is_exact_enoent("", collector.REMOTE, "", 0)


@pytest.mark.parametrize("output", [
    f"{collector.MD5} /data/local/tmp/another-file\n",
    f"{collector.MD5} {collector.REMOTE}\n{collector.MD5} {collector.REMOTE}\n",
    f"{collector.MD5[:20]} {collector.REMOTE}\n",
    f"{collector.MD5} {collector.REMOTE}\nwarning\n",
    f"prefix {collector.MD5} {collector.REMOTE}\n",
])
def test_md5_requires_one_exact_digest_and_remote_path(output):
    assert collector._digest(output) is None


def test_md5_accepts_historical_android_two_space_separator():
    observed = f"{collector.MD5}  {collector.REMOTE}\r\n"
    assert collector._digest(observed) == collector.MD5


def test_frozen_push_plan_matches_actual_relative_source_argument(package, capsys):
    fake = FakeADB()
    assert collector.execute(package, runner=fake, confirm_stock_state=lambda: True) == 0
    capsys.readouterr()
    push_call = next(call for call in fake.calls if "push" in call)
    assert push_call[1:] == ["-s", "TESTSER", "push",
                             str(collector.ARTIFACT.relative_to(collector.ROOT)), collector.REMOTE]
    assert collector.command_plan()[3:5] == [
        ["-s", "<EXACT_SERIAL>", "shell", "ls", "-ld", collector.REMOTE],
        ["-s", "<EXACT_SERIAL>", "push", str(collector.ARTIFACT.relative_to(collector.ROOT)), collector.REMOTE],
    ]


def test_stock_state_mismatch_fails_after_cleanup(package):
    fake = FakeADB()
    with pytest.raises(collector.Blocked):
        collector.execute(package, runner=fake, confirm_stock_state=lambda: False)
    assert sum("/system/bin/rm" in call for call in fake.calls) == 1


def test_hash_binding_mismatch_makes_zero_adb_calls(package):
    package.authorized_manifest_sha256 = "0" * 64
    fake = FakeADB()
    with pytest.raises(collector.Blocked):
        collector.execute(package, runner=fake, confirm_stock_state=lambda: True)
    assert fake.calls == []


@pytest.mark.parametrize("child,parent", [("0", "42"), ("1", "42"), ("42", "42"),
                                           ("2147483648", "42"), ("+42", "43"),
                                           ("42;echo BAD", "43"), ("00042", "43")])
def test_process_absence_rejects_invalid_or_unbounded_pid_input(child, parent):
    with pytest.raises(collector.Blocked):
        collector.process_absence_command(child, parent)


def test_process_absence_builds_one_remote_command_argument_and_keeps_remote_dollar_expansion():
    command = collector.process_absence_command(42, 41)
    assert command == (
        "test -d /proc/$$ && test -r /proc/$$/stat && test -r /proc/self/stat && "
        "test ! -e /proc/42 && test ! -e /proc/41 && echo R7E6_PIDS_ABSENT:42:41")
    argv = ["adb", "-s", "SERIAL", "shell", command]
    assert argv[-2:] == ["shell", command]
    assert "sh" not in argv[-2:]
    assert "$$" in argv[-1]


def test_posix_reproduction_of_adb_argument_joining_shows_nested_c_shell_short_circuit():
    expression = collector.process_absence_command(2000000001, 2000000002)
    malformed_remote_command = " ".join(("sh", "-c", expression))
    result = subprocess.run(["/bin/sh", "-c", malformed_remote_command],
                            capture_output=True, text=True, check=False)
    assert result.returncode != 0
    assert result.stdout == ""
    assert result.stderr == ""


def test_process_absence_manifest_plan_has_no_nested_shell():
    plan = collector.command_plan()
    absence = plan[8]
    assert absence[:3] == ["-s", "<EXACT_SERIAL>", "shell"]
    assert len(absence) == 4
    assert "$$" in absence[3]
    assert "sh" not in absence
    assert "<CHILD_PID>" in absence[3] and "<PARENT_PID>" in absence[3]


def test_process_absence_uncertain_after_version_does_not_run_self_test_or_cleanup(package, tmp_path):
    fake = FakeADB(failure="process_empty")
    with pytest.raises(collector.Blocked, match="TEST_A_PROCESS_STATE_UNCERTAIN"):
        collector.execute(package, runner=fake, confirm_stock_state=lambda: True)
    diagnostic_calls = [call for call in fake.calls if call[-1:]
                        and collector.REMOTE in call[-1]
                        and ("--version" in call[-1] or "--self-test" in call[-1])]
    assert len(diagnostic_calls) == 1
    assert "--version" in diagnostic_calls[0][-1]
    assert not any("/system/bin/rm" in call for call in fake.calls)
    evidence_files = list((tmp_path / "build/r7e6a/test-a/evidence").glob("collector-failure-*.json"))
    assert len(evidence_files) == 1
    evidence = json.loads(evidence_files[0].read_text())
    assert evidence["decision"] == "TEST_A_PROCESS_STATE_UNCERTAIN"
    diagnostic = next(row for row in evidence["command_results"]
                      if row["operation"] == "DIAGNOSTIC_VERSION")
    assert "SUPERVISOR_CHILD_STARTED" in diagnostic["stdout_raw_bounded"]
    assert diagnostic["guest_status_reported"] == "0"
    assert diagnostic["guest_exit_zero_confirmed"] is False
    assert diagnostic["process_absence_confirmed"] is False
    assert diagnostic["parent_pid"] == 41 and diagnostic["child_pid"] == 42
    absent = next(row for row in evidence["command_results"]
                  if row["operation"] == "EXACT_PROCESS_ABSENCE")
    assert absent["stdout_raw_bounded"] == ""
    assert absent["parent_child_absence"] == "NOT_CONFIRMED"
    assert absent["argv_redacted"][2] == "<REDACTED_SERIAL>"
