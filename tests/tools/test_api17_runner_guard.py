from pathlib import Path
import ast
import os
import subprocess
import sys

import pytest

from tests.tools.local_tool_gate import LOCAL_ONLY_TEST_TOOLS, require_local_tools
from tools.api17_runner_guard import (
    GuardError,
    assert_avd_absent,
    cleanup_owned_avd,
    create_run_dir,
    emulator_inventory_is_safe,
    is_owned_adb_child,
    is_owned_adb_logcat_child,
    mark_avd_owned,
    parse_adb_inventory,
    resolve_build_dir,
)


REPO = Path(__file__).resolve().parents[2]
RUNNER = REPO / "tools/run_cl_imp_03_emulator.sh"


def _build_root(root: Path) -> tuple[Path, Path]:
    repo = root / "repo"
    build = repo / "build" / "cl-imp-03"
    build.mkdir(parents=True)
    (build / ".claritylink-build-root").write_text(str(repo.resolve()) + "\n")
    return repo, build


def test_build_output_must_be_a_marked_campaign_directory(tmp_path):
    repo, build = _build_root(tmp_path)
    assert resolve_build_dir(repo, build) == build.resolve()
    with pytest.raises(GuardError, match="direct child"):
        resolve_build_dir(repo, build.parent)


def test_build_output_symlink_and_unapproved_parent_are_rejected(tmp_path):
    repo, build = _build_root(tmp_path)
    alias = repo / "build" / "cl-imp-03-alias"
    alias.symlink_to(build, target_is_directory=True)
    with pytest.raises(GuardError, match="non-symlink"):
        resolve_build_dir(repo, alias)
    external = tmp_path / "external" / "cl-imp-03"
    external.mkdir(parents=True)
    (external / ".claritylink-build-root").write_text(str(repo.resolve()) + "\n")
    with pytest.raises(GuardError, match="direct child"):
        resolve_build_dir(repo, external)


def test_avd_collision_is_rejected_without_touching_existing_files(tmp_path):
    repo, build = _build_root(tmp_path)
    run_dir = create_run_dir(repo, build)
    avd_home = run_dir / "avd"
    avd_home.mkdir()
    name = "climp03_api17_123"
    avd = avd_home / (name + ".avd")
    avd.mkdir()
    sentinel = avd / "keep-user-data"
    sentinel.write_text("preserve")
    ini = avd_home / (name + ".ini")
    ini.write_text("existing-index")
    with pytest.raises(GuardError, match="refusing to overwrite"):
        assert_avd_absent(run_dir, name)
    assert sentinel.read_text() == "preserve"
    assert ini.read_text() == "existing-index"


def test_cleanup_removes_only_avd_marked_by_its_run(tmp_path):
    repo, build = _build_root(tmp_path)
    run_dir = create_run_dir(repo, build)
    avd_home = run_dir / "avd"
    avd_home.mkdir()
    name = "climp03_api17_456"
    assert_avd_absent(run_dir, name)
    avd = avd_home / (name + ".avd")
    avd.mkdir()
    (avd_home / (name + ".ini")).write_text("campaign AVD")
    (avd / "data").write_text("synthetic")
    mark_avd_owned(run_dir, name)
    assert cleanup_owned_avd(run_dir, name)
    assert not avd.exists()
    assert not (avd_home / (name + ".ini")).exists()

    avd.mkdir()
    (avd_home / (name + ".ini")).write_text("unowned")
    (avd / ".claritylink-avd-owner").write_text("wrong-run\n")
    (avd / "data").write_text("preserve")
    assert not cleanup_owned_avd(run_dir, name)
    assert (avd / "data").read_text() == "preserve"
    assert (avd_home / (name + ".ini")).read_text() == "unowned"


def test_adb_cleanup_requires_exact_direct_child_not_same_binary_server():
    assert is_owned_adb_child(77, 12, 77, 12, "/sdk/adb", "/sdk/adb", "adb -P 9011 server nodaemon", 9011)
    assert not is_owned_adb_child(77, 12, 78, 12, "/sdk/adb", "/sdk/adb", "adb -P 9011 server nodaemon", 9011)
    assert not is_owned_adb_child(77, 12, 77, 1, "/sdk/adb", "/sdk/adb", "adb -P 9011 server nodaemon", 9011)
    assert not is_owned_adb_child(77, 12, 77, 12, "/sdk/adb", "/sdk/adb", "adb -P 9011 fork-server server", 9011)


def test_logcat_cleanup_requires_exact_isolated_adb_child_and_target():
    command = "/sdk/adb -P 61000 -s emulator-5580 logcat -s ClarityLinkCLIMP03:I *:S"
    assert is_owned_adb_logcat_child(77, 12, 77, 12, "/sdk/adb", "/sdk/adb", command,
                                     61000, "emulator-5580")
    assert not is_owned_adb_logcat_child(77, 12, 78, 12, "/sdk/adb", "/sdk/adb", command,
                                         61000, "emulator-5580")
    assert not is_owned_adb_logcat_child(77, 12, 77, 1, "/sdk/adb", "/sdk/adb", command,
                                         61000, "emulator-5580")
    assert not is_owned_adb_logcat_child(77, 12, 77, 12, "/sdk/other-adb", "/sdk/adb", command,
                                         61000, "emulator-5580")
    assert not is_owned_adb_logcat_child(77, 12, 77, 12, "/sdk/adb", "/sdk/adb", command,
                                         61001, "emulator-5580")
    assert not is_owned_adb_logcat_child(77, 12, 77, 12, "/sdk/adb", "/sdk/adb", command,
                                         61000, "emulator-5582")


def test_adb_inventory_keeps_unexpected_device_identity_and_state():
    output = """List of devices attached
emulator-5582 device product:sdk_gphone_x86 model:Android_SDK_built_for_x86
ZX1 unauthorized usb:1-2
192.0.2.2:5555 offline transport_id:8
* daemon started successfully
"""
    assert parse_adb_inventory(output) == [
        ("emulator-5582", "device"),
        ("ZX1", "unauthorized"),
        ("192.0.2.2:5555", "offline"),
    ]


def test_only_exact_owned_emulator_may_be_offline_during_its_boot_window():
    assert emulator_inventory_is_safe([], "emulator-5580", False)
    assert emulator_inventory_is_safe([("emulator-5580", "offline")], "emulator-5580", True)
    assert emulator_inventory_is_safe([("emulator-5580", "device")], "emulator-5580", True)
    assert not emulator_inventory_is_safe([("emulator-5580", "offline")], "emulator-5580", False)
    assert not emulator_inventory_is_safe([("emulator-5582", "offline")], "emulator-5580", True)
    assert not emulator_inventory_is_safe([("emulator-5580", "device"), ("ZX1", "device")],
                                          "emulator-5580", True)


def test_runner_lock_serializes_and_releases_after_holder_exit(tmp_path):
    lock_path = tmp_path / "runner.lock"
    ready_a = tmp_path / "a.ready"
    ready_b = tmp_path / "b.ready"
    guard = REPO / "tools/api17_runner_guard.py"
    parent_pid = str(os.getpid())
    first = subprocess.Popen([sys.executable, str(guard), "hold-lock", str(lock_path), str(ready_a), parent_pid])
    try:
        for _ in range(100):
            if ready_a.exists():
                break
            import time
            time.sleep(0.01)
        assert ready_a.exists()
        second = subprocess.Popen([sys.executable, str(guard), "hold-lock", str(lock_path), str(ready_b), parent_pid])
        try:
            import time
            time.sleep(0.1)
            assert not ready_b.exists()
        finally:
            first.terminate()
            first.wait(timeout=3)
        for _ in range(100):
            if ready_b.exists():
                break
            import time
            time.sleep(0.01)
        assert ready_b.exists()
    finally:
        if first.poll() is None:
            first.terminate()
            first.wait(timeout=3)
        if 'second' in locals() and second.poll() is None:
            second.terminate()
            second.wait(timeout=3)


def test_runner_lock_holder_exits_promptly_after_parent_crash(tmp_path):
    lock_path = tmp_path / "crash.lock"
    ready = tmp_path / "crash.ready"
    guard = REPO / "tools/api17_runner_guard.py"
    supervisor_code = (
        "import os,subprocess,sys,time; "
        "p=subprocess.Popen([sys.executable,sys.argv[1],'hold-lock',sys.argv[2],sys.argv[3],str(os.getpid())],"
        "stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL); "
        "print(p.pid,flush=True); time.sleep(30)"
    )
    supervisor = subprocess.Popen([sys.executable, "-c", supervisor_code, str(guard),
                                   str(lock_path), str(ready)], stdout=subprocess.PIPE, text=True)
    assert supervisor.stdout is not None
    holder_pid = int(supervisor.stdout.readline().strip())
    try:
        for _ in range(100):
            if ready.exists():
                break
            import time
            time.sleep(0.01)
        assert ready.exists()
        supervisor.kill()
        supervisor.wait(timeout=3)
        for _ in range(100):
            if subprocess.run(["kill", "-0", str(holder_pid)], check=False).returncode != 0:
                break
            import time
            time.sleep(0.02)
        assert subprocess.run(["kill", "-0", str(holder_pid)], check=False).returncode != 0
    finally:
        if supervisor.poll() is None:
            supervisor.kill()
            supervisor.wait(timeout=3)


def test_api17_runner_uses_owned_outputs_and_child_server_only():
    source = RUNNER.read_text()
    assert "research/vehicle/test6a-t7-integration/evidence" not in source
    assert 'campaign_evidence="$run_root/evidence"' in source
    assert 'resolve-build "$repo" "$out"' in source
    assert 'create-run "$repo" "$out"' in source
    assert 'check-avd "$run_root" "$avd"' in source
    assert 'mark-avd "$run_root" "$avd"' in source
    assert 'cleanup-avd "$run_root" "$avd"' in source
    assert 'server nodaemon' in source and "adb_server_pid=$!" in source
    assert 'hold-lock' in source and 'runner-lock' in source
    assert 'api17-unexpected-targets-' in source
    assert 'check-adb-child' in source
    assert 'check-adb-logcat-child' in source
    assert 'runtime_logcat_zombie_owned' in source
    assert 'api17-logcat-cleanup-identity-' in source
    assert "kill \"$runtime_logcat_pid\"" in source
    assert '"$adb" -P "$adb_port" -s "$serial" logcat -s ClarityLinkCLIMP03:I' in source
    assert 'adb_local -s "$serial" logcat -s ClarityLinkCLIMP03:I' not in source
    assert "start-server" not in source and "kill-server" not in source
    assert "--force" not in source
    assert 'run_label/evidence/api17-source-manifest.sha256' in source
    assert "toolchain/platform-tools/adb" in source


def test_local_only_skip_manifest_matches_all_declared_gates():
    observed = {}
    for path in sorted((REPO / "tests/tools").glob("test_*.py")):
        if path.name == Path(__file__).name:
            continue
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            if not isinstance(func, ast.Name) or func.id != "require_local_tools":
                continue
            names = tuple(arg.value for arg in node.args[1:] if isinstance(arg, ast.Constant))
            observed[path.name] = names
    assert observed == LOCAL_ONLY_TEST_TOOLS


def test_local_gate_skips_only_when_registered_local_tool_is_absent(tmp_path):
    name, tools = next(iter(LOCAL_ONLY_TEST_TOOLS.items()))
    test_path = tmp_path / "repo/tests/tools" / name
    test_path.parent.mkdir(parents=True)
    with pytest.raises(pytest.skip.Exception, match="local-only tool"):
        require_local_tools(str(test_path), *tools)
    for tool in tools:
        path = tmp_path / "repo/tools" / tool
        path.parent.mkdir(parents=True, exist_ok=True)
        path.touch()
    require_local_tools(str(test_path), *tools)
