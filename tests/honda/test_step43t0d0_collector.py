"""Offline fake-runner proof for the executable 43T0-D collector."""

import ast
import hashlib
import json
import os
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import step43t0c_identity_delta_dry_run as approved  # noqa: E402
import step43t0d3_netcfg_plan as revised  # noqa: E402
import step43t0d0_collector as collector  # noqa: E402


ENDPOINT = "synthetic-endpoint"
ADB = "adb"
SHELL_ID = "uid=2000(shell) gid=2000(shell) groups=2000(shell)"
KERNEL = "synthetic kernel"
DEV = b"Inter-|   Receive |  Transmit\n face |bytes packets errs drop fifo frame compressed multicast|bytes packets errs drop fifo colls carrier compressed\neth0: 1 2 0 0 0 0 0 0 3 4 0 0 0 0 0 0\n"
ROUTE = b"Iface\tDestination\tGateway\tFlags\tRefCnt\tUse\tMetric\tMask\tMTU\tWindow\tIRTT\neth0\t00000000\t00000000\t0001\t0\t0\t0\t00000000\t0\t0\t0\n"
IPV6_ROUTE = (b"0" * 32 + b" 00 " + b"0" * 32 + b" 00 " + b"0" * 32 + b" 00000001 00000000 00000000 00000001 eth0\n")
IF_INET6 = b"00000000000000000000000000000001 01 80 10 80 eth0\n"
NETCFG = b"eth0     UP  192.0.2.1/24  0x00000001 02:00:00:00:00:01\n"


@pytest.fixture(autouse=True)
def synthetic_reference(monkeypatch):
    shell_hash = hashlib.sha256(SHELL_ID.encode()).hexdigest()
    kernel_hash = hashlib.sha256(KERNEL.encode()).hexdigest()
    monkeypatch.setattr(approved, "SHELL_ID_SHA256", shell_hash)
    monkeypatch.setattr(approved, "KERNEL_SHA256", kernel_hash)
    monkeypatch.setattr(collector, "SHELL_ID_SHA256", shell_hash)
    monkeypatch.setattr(collector, "KERNEL_SHA256", kernel_hash)


class FakeRunner:
    def __init__(self, *, devices=None, override=None, fail_at=None):
        self.calls = []
        self.devices = devices if devices is not None else f"List of devices attached\n{ENDPOINT}\tdevice\n".encode()
        self.override = override or {}
        self.fail_at = fail_at

    def run(self, argv, timeout, cap):
        self.calls.append(argv)
        assert timeout == 5 and cap == 65536
        if self.fail_at and len(self.calls) == self.fail_at[0]:
            return collector.CommandResult(self.fail_at[1], started_utc="start", finished_utc="end")
        suffix = argv[3:] if len(argv) > 2 else ("devices",)
        outputs = {
            ("devices",): self.devices,
            ("shell", "id"): (SHELL_ID + "\r\n").encode(),
            ("shell", "cat", "/proc/version"): (KERNEL + "\r\n").encode(),
            ("shell", "cat", "/proc/net/dev"): DEV,
            ("shell", "cat", "/proc/net/route"): ROUTE,
            ("shell", "cat", "/proc/net/ipv6_route"): IPV6_ROUTE,
            ("shell", "cat", "/proc/net/if_inet6"): IF_INET6,
            ("shell", "netcfg"): NETCFG,
        }
        outputs.update({("shell", "getprop", key): (value + "\r\n").encode()
                        for key, value, _ in approved.PROPERTIES})
        outputs.update(self.override)
        return collector.CommandResult("SUCCESS", outputs[suffix], returncode=0,
                                       started_utc="start", finished_utc="end")


def run_case(tmp_path, runner=None, answers=None, endpoint=ENDPOINT):
    runner = runner or FakeRunner()
    asked = []

    def confirm(key):
        asked.append(key)
        return (answers or {}).get(key, True)

    store = collector.CaptureStore(tmp_path / "private", ROOT)
    result = collector.collect(runner, confirm, store, endpoint)
    manifest = json.loads((store.root / "manifest.json").read_text())
    return result, runner, asked, store, manifest


def test_dry_run_default_spawns_no_process(monkeypatch, capsys, tmp_path):
    def forbidden(*_args, **_kwargs):
        raise AssertionError("dry run attempted process execution")

    monkeypatch.setattr(collector.subprocess, "Popen", forbidden)
    monkeypatch.setattr(sys, "argv", ["collector", "--host-output", str(tmp_path / "proposed")])
    collector.main()
    rows = [json.loads(line) for line in capsys.readouterr().out.splitlines()]
    assert [row["argv"] for row in rows if "argv" in row] == [row["argv"] for row in revised.plan(tmp_path / "proposed") if "argv" in row]
    assert not (tmp_path / "proposed").exists()


def test_canonical_command_equivalence_and_success(tmp_path):
    result, runner, asked, store, manifest = run_case(tmp_path)
    assert result == "SUCCESS"
    assert len(runner.calls) == 23  # enumeration + seven identity + fifteen network
    assert runner.calls[0] == (ADB, "devices")
    planned = [row for row in revised.plan(store.root) if row["step"] in ("identity", "network")]
    assert runner.calls[1:] == [
        tuple(ENDPOINT if part == revised.TARGET else part for part in row["argv"])
        for row in planned
    ]
    assert collector.ALLOWED_SUFFIXES == {tuple(row["argv"][3:]) for row in planned}
    assert len(collector.ALLOWED_SUFFIXES) == 12
    assert asked == ["parked_honda", "baseline_disconnected",
                     "connected_stock_center_audio_cluster_normal",
                     "disconnected_stock_center_audio_cluster_normal",
                     "final_stock_center_audio_cluster_normal"]
    assert manifest["final_status"] == "SUCCESS"
    assert manifest["project_commit"] == collector.read_git_commit(ROOT)
    assert manifest["collector_source_sha256"] == hashlib.sha256(
        (ROOT / "tools/step43t0d0_collector.py").read_bytes()
    ).hexdigest()
    assert len(manifest["commands"]) == 23
    assert (store.root.stat().st_mode & 0o777) == 0o700
    assert (store.root / "identity" / "id.raw").stat().st_mode & 0o777 == 0o600
    assert (store.root / "post-disconnect" / "netcfg.raw").exists()
    assert manifest["revised_plan_sha256"] == collector.D3_PLAN_SHA256


@pytest.mark.parametrize("devices", [
    b"List of devices attached\n",
    f"List of devices attached\n{ENDPOINT}\tdevice\nother\tdevice\n".encode(),
    f"List of devices attached\n{ENDPOINT}\toffline\n".encode(),
    f"List of devices attached\n{ENDPOINT}\tunauthorized\n".encode(),
])
def test_target_ambiguity_stops_before_target_read(tmp_path, devices):
    result, runner, _asked, _store, _manifest = run_case(tmp_path, FakeRunner(devices=devices))
    assert result == "AMBIGUOUS_ADB_TARGET"
    assert len(runner.calls) == 1


def test_endpoint_mismatch_and_user_abort_stop(tmp_path):
    (tmp_path / "a").mkdir()
    (tmp_path / "b").mkdir()
    result, runner, _asked, _store, _manifest = run_case(tmp_path / "a", endpoint="old-endpoint")
    assert result == "IDENTITY_MISMATCH" and len(runner.calls) == 1
    result, runner, _asked, _store, _manifest = run_case(tmp_path / "b", answers={"parked_honda": False})
    assert result == "USER_ABORT" and len(runner.calls) == 1


@pytest.mark.parametrize("suffix,data", [
    (("shell", "id"), b"uid=0(root) gid=0(root)\n"),
    (("shell", "id"), b"uid=2000(shell) gid=2000(shell) groups=0(root)\n"),
    (("shell", "cat", "/proc/version"), b"different kernel\n"),
    *((l, b"wrong\n") for l in [("shell", "getprop", key) for key, _, _ in approved.PROPERTIES]),
    (("shell", "getprop", "ro.hardware"), b""),
])
def test_identity_mismatch_never_reaches_network(tmp_path, suffix, data):
    result, runner, _asked, _store, _manifest = run_case(tmp_path, FakeRunner(override={suffix: data}))
    assert result in {"IDENTITY_MISMATCH", "IDENTITY_INCOMPLETE", "UNEXPECTED_PRIVILEGE"}
    assert all("/proc/net/" not in " ".join(call) and "netcfg" not in call for call in runner.calls)


@pytest.mark.parametrize("number,status", [
    (2, "ADB_TRANSPORT_FAILURE"), (9, "ADB_TRANSPORT_FAILURE"),
    (14, "ADB_TRANSPORT_FAILURE"), (19, "ADB_TRANSPORT_FAILURE"),
    (9, "COMMAND_UNAVAILABLE"), (9, "PERMISSION_DENIED"),
    (9, "TIMEOUT"), (9, "OUTPUT_LIMIT_EXCEEDED"),
    (13, "COMMAND_UNAVAILABLE"),
])
def test_command_failures_stop_without_retry(tmp_path, number, status):
    result, runner, _asked, _store, manifest = run_case(tmp_path, FakeRunner(fail_at=(number, status)))
    assert result == status and len(runner.calls) == number
    assert manifest["final_status"] == status


@pytest.mark.parametrize("suffix,output", [
    (("shell", "cat", "/proc/net/dev"), b"garbage"),
    (("shell", "cat", "/proc/net/route"), b"garbage"),
    (("shell", "cat", "/proc/net/ipv6_route"), b"garbage"),
    (("shell", "cat", "/proc/net/if_inet6"), b"garbage"),
    (("shell", "netcfg"), b"usage: netcfg [interface]"),
])
def test_malformed_network_output_stops(tmp_path, suffix, output):
    result, runner, _asked, _store, manifest = run_case(tmp_path, FakeRunner(override={suffix: output}))
    assert result == "UNEXPECTED_FORMAT"
    assert manifest["commands"][-1]["result_class"] == "UNEXPECTED_FORMAT"
    assert len(runner.calls) <= 13


@pytest.mark.parametrize("gate,status", [
    ("baseline_disconnected", "USER_ABORT"),
    ("connected_stock_center_audio_cluster_normal", "STOCK_SANITY_FAILURE"),
    ("disconnected_stock_center_audio_cluster_normal", "STOCK_SANITY_FAILURE"),
    ("final_stock_center_audio_cluster_normal", "STOCK_SANITY_FAILURE"),
])
def test_human_phase_gates_stop(tmp_path, gate, status):
    result, runner, asked, _store, _manifest = run_case(tmp_path, answers={gate: False})
    assert result == status and gate in asked
    if gate == "connected_stock_center_audio_cluster_normal":
        assert len(runner.calls) == 13  # enumeration + identity + baseline only
    if gate == "disconnected_stock_center_audio_cluster_normal":
        assert len(runner.calls) == 18


def test_fixed_allowlist_rejects_writes_and_shell_metacharacters():
    allowed = (ADB, "-s", ENDPOINT, "shell", "netcfg")
    assert collector.allowed_argv(allowed, ENDPOINT)
    for extra in ("wlan0", "up", "1.2.3.4", ">", ">>", "|", ";", "&&", "||", "$()", "`bad`"):
        assert not collector.allowed_argv(allowed + (extra,), ENDPOINT)
    for command in ("su", "root", "run-as", "mount", "setprop", "settings", "pm", "am", "svc",
                    "ip", "route", "iptables", "nft", "chmod", "chown", "touch", "mkdir", "rm",
                    "mv", "cp", "dd", "tee", "reboot", "stop", "start", "kill", "pkill", "ptrace",
                    "tcpdump", "nc", "netcat", "socat"):
        assert not collector.allowed_argv((ADB, "-s", ENDPOINT, "shell", command), ENDPOINT)
    for command in ("push", "pull", "root", "connect"):
        assert not collector.allowed_argv((ADB, command), ENDPOINT)
    assert not collector.allowed_argv((ADB, "-s", ENDPOINT, "shell", "cat", "/proc/42/mem"), ENDPOINT)
    assert not collector.allowed_argv((ADB, "-s", ENDPOINT, "shell", "ifconfig"), ENDPOINT)


def test_host_storage_rejects_inside_repo_and_existing_path(tmp_path):
    with pytest.raises(ValueError):
        collector.CaptureStore(ROOT / "private-output", ROOT)
    path = tmp_path / "private"
    path.mkdir()
    with pytest.raises(ValueError):
        collector.CaptureStore(path, ROOT)


def test_historical_manifest_is_checksum_pinned(tmp_path, monkeypatch):
    path = tmp_path / "manifest.json"
    raw = json.dumps({"adb_serial": ENDPOINT}).encode()
    path.write_bytes(raw)
    monkeypatch.setattr(collector, "MANIFEST_SHA256", hashlib.sha256(raw).hexdigest())
    assert collector.read_historical_endpoint(path) == ENDPOINT
    path.write_bytes(raw + b" ")
    with pytest.raises(ValueError):
        collector.read_historical_endpoint(path)


def test_adb_binary_requires_exact_path_and_checksum(tmp_path, monkeypatch):
    path = tmp_path / "adb"
    path.write_bytes(b"synthetic adb fixture")
    path.chmod(0o700)
    monkeypatch.setattr(collector, "EXPECTED_ADB_PATH", path)
    monkeypatch.setattr(collector, "EXPECTED_ADB_SHA256", hashlib.sha256(path.read_bytes()).hexdigest())
    assert collector.validate_adb_binary(path) == str(path)
    with pytest.raises(ValueError):
        collector.validate_adb_binary(tmp_path / "other")
    path.write_bytes(b"changed")
    with pytest.raises(ValueError):
        collector.validate_adb_binary(path)


def test_dry_run_rejects_output_inside_repo(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["collector", "--host-output", str(ROOT / "private-output")])
    with pytest.raises(SystemExit):
        collector.main()


def test_changed_approved_plan_stops_before_adb(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "APPROVED_PLAN_SHA256", "0" * 64)
    result, runner, _asked, _store, _manifest = run_case(tmp_path)
    assert result == "UNEXPECTED_FORMAT"
    assert runner.calls == []


def test_changed_d3_plan_stops_before_adb(tmp_path, monkeypatch):
    monkeypatch.setattr(collector, "D3_PLAN_SHA256", "0" * 64)
    result, runner, _asked, _store, _manifest = run_case(tmp_path)
    assert result == "UNEXPECTED_FORMAT"
    assert runner.calls == []


def test_source_has_one_subprocess_callsite_and_no_socket_or_eval():
    source = (ROOT / "tools/step43t0d0_collector.py").read_text()
    tree = ast.parse(source)
    calls = [node for node in ast.walk(tree) if isinstance(node, ast.Call)]
    popen = [node for node in calls if isinstance(node.func, ast.Attribute) and node.func.attr == "Popen"]
    assert len(popen) == 1
    assert any(keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is False
               for keyword in popen[0].keywords)
    assert not any(isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec"} for node in calls)
    assert "socket" not in [a.names[0].name for a in tree.body if isinstance(a, ast.Import)]


def test_bounded_runner_enforces_output_cap_without_adb():
    result = collector.BoundedRunner().run(
        (sys.executable, "-c", "import sys; sys.stdout.write('x' * 100000)"), 5, 1024
    )
    assert result.status == "OUTPUT_LIMIT_EXCEEDED"
    assert len(result.stdout) + len(result.stderr) <= 1024


def test_bounded_runner_caps_combined_streams_without_adb():
    result = collector.BoundedRunner().run(
        (sys.executable, "-c", "import sys; sys.stdout.write('x' * 700); sys.stdout.flush(); sys.stderr.write('y' * 700)"),
        5, 1024
    )
    assert result.status == "OUTPUT_LIMIT_EXCEEDED"
    assert len(result.stdout) + len(result.stderr) <= 1024


def test_bounded_runner_enforces_timeout_without_adb():
    result = collector.BoundedRunner().run(
        (sys.executable, "-c", "import time; time.sleep(2)"), 1, 1024
    )
    assert result.status == "TIMEOUT"


def test_runner_uses_pinned_executable_with_canonical_argv_token():
    result = collector.BoundedRunner(sys.executable).run(
        ("adb", "-c", "print('synthetic')"), 5, 1024
    )
    assert result.status == "SUCCESS"
    assert result.stdout == b"synthetic\n"
