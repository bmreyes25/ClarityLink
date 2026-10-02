"""Offline tests for the non-executing 43T0-C plan and identity gate."""

import ast
import hashlib
import importlib.util
import sys
from pathlib import Path

import pytest


SOURCE = Path(__file__).resolve().parents[2] / "tools/step43t0c_identity_delta_dry_run.py"
SPEC = importlib.util.spec_from_file_location("step43t0c_dry_run", SOURCE)
assert SPEC and SPEC.loader
MODULE = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = MODULE
SPEC.loader.exec_module(MODULE)


def matching_results(monkeypatch):
    monkeypatch.setattr(MODULE, "KERNEL_SHA256", hashlib.sha256(b"synthetic kernel").hexdigest())
    synthetic_id = "uid=2000(shell) gid=2000(shell) groups=2000(shell)"
    monkeypatch.setattr(MODULE, "SHELL_ID_SHA256", hashlib.sha256(synthetic_id.encode()).hexdigest())
    return {
        "id": synthetic_id + "\r\n",
        "kernel": "synthetic kernel\r\n",
        **{key: expected + "\r\n" for key, expected, _ in MODULE.PROPERTIES},
    }


def test_dry_run_is_physically_nonexecuting_and_fixed():
    tree = ast.parse(SOURCE.read_text())
    imports = [node for node in tree.body if isinstance(node, (ast.Import, ast.ImportFrom))]
    assert not any(
        name.name in {"subprocess", "socket", "os", "pty"}
        for node in imports for name in node.names
    )
    rows = MODULE.plan(Path("/private-host/proposed"))
    assert [row["step"] for row in rows[:2]] == ["enumerate", "human_confirmation"]
    assert rows[0]["argv"] == ["adb", "devices"]
    assert [row["key"] for row in rows if row["step"] == "identity"] == list(MODULE.IDENTITY_KEYS)
    assert len([row for row in rows if row["step"] == "identity"]) == 7
    assert [row for row in rows if row["step"] == "host_capture"][0]["manifest"] == "/private-host/proposed/manifest.json"
    network = [row for row in rows if row["step"] == "network"]
    assert len(network) == 15
    assert [row["phase"] for row in network] == [phase for phase in MODULE.PHASES for _ in range(5)]
    assert [row["argv"][4:] for row in network] == [
        list(command) for _phase in MODULE.PHASES for command, _name in MODULE.NETWORK_READS
    ]
    assert all(row["only_if"] == "IDENTITY_MATCH" for row in network)
    assert all(row["timeout_seconds"] == 5 and row["max_output_bytes"] == 65536 for row in network)
    assert all(row["argv"][2] == MODULE.CURRENT_TARGET for row in network)
    assert network[-1]["argv"] == ["adb", "-s", MODULE.CURRENT_TARGET, "shell", "ifconfig"]


def test_matching_identity_allows_only_fixed_network_argv(monkeypatch):
    results = matching_results(monkeypatch)
    decision = MODULE.assess_identity([("synthetic-endpoint", "device")], True, "synthetic-endpoint", results)
    assert decision.state == "IDENTITY_MATCH"
    commands = MODULE.network_argv(decision, "synthetic-endpoint")
    assert len(commands) == 15
    assert commands[0] == ("adb", "-s", "synthetic-endpoint", "shell", "cat", "/proc/net/dev")
    assert commands[-1] == ("adb", "-s", "synthetic-endpoint", "shell", "ifconfig")


@pytest.mark.parametrize(
    "targets,human,endpoint,change,expected_state",
    [
        (None, True, "synthetic-endpoint", None, "IDENTITY_NOT_CHECKED"),
        ([], True, "synthetic-endpoint", None, "IDENTITY_INCOMPLETE"),
        ([("synthetic-endpoint", "offline")], True, "synthetic-endpoint", None, "IDENTITY_INCOMPLETE"),
        ([("synthetic-endpoint", "unauthorized")], True, "synthetic-endpoint", None, "IDENTITY_INCOMPLETE"),
        ([("a", "device"), ("b", "device")], True, "a", None, "IDENTITY_INCOMPLETE"),
        ([("synthetic-endpoint", "device")], False, "synthetic-endpoint", None, "IDENTITY_INCOMPLETE"),
        ([("synthetic-endpoint", "device")], True, "old-endpoint", None, "IDENTITY_MISMATCH"),
        ([("synthetic-endpoint", "device")], True, "synthetic-endpoint", ("id", "uid=0(root) gid=0(root)"), "IDENTITY_MISMATCH"),
        ([("synthetic-endpoint", "device")], True, "synthetic-endpoint", ("id", "uid=2000(shell) gid=2000(shell) groups=0(root)"), "IDENTITY_MISMATCH"),
        ([("synthetic-endpoint", "device")], True, "synthetic-endpoint", ("kernel", "different kernel"), "IDENTITY_MISMATCH"),
        ([("synthetic-endpoint", "device")], True, "synthetic-endpoint", ("kernel", "synthetic kernel extra"), "IDENTITY_MISMATCH"),
        ([("synthetic-endpoint", "device")], True, "synthetic-endpoint", ("ro.hardware", "other"), "IDENTITY_MISMATCH"),
        ([("synthetic-endpoint", "device")], True, "synthetic-endpoint", ("ro.hardware", ""), "IDENTITY_INCOMPLETE"),
    ],
)
def test_every_nonmatch_blocks_network(monkeypatch, targets, human, endpoint, change, expected_state):
    results = matching_results(monkeypatch)
    if change:
        results[change[0]] = change[1]
    decision = MODULE.assess_identity(targets, human, endpoint, results)
    assert decision.state == expected_state
    with pytest.raises(ValueError):
        MODULE.network_argv(decision, "synthetic-endpoint")
