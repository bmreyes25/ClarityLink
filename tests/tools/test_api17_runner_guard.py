from pathlib import Path
import ast

import pytest

from tests.tools.local_tool_gate import LOCAL_ONLY_TEST_TOOLS, require_local_tools
from tools.api17_runner_guard import (
    GuardError,
    assert_avd_absent,
    cleanup_owned_avd,
    create_run_dir,
    is_owned_adb_child,
    mark_avd_owned,
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
    assert 'check-adb-child' in source
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
