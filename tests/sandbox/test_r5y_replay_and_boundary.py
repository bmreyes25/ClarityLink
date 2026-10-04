"""R5Y fixture corpus, replay determinism and scoped static firewall."""

import json
import sys
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parents[2]
FIXTURES = ROOT / "tests" / "fixtures" / "r5y"
sys.path.insert(0, str(ROOT / "src" / "claritylink-sandbox"))
sys.path.insert(0, str(ROOT / "tools"))

from r5y_receiver_core import ReceiverError, replay_document  # noqa: E402
from check_r5y_sandbox_boundary import check_source, check_tree  # noqa: E402


@pytest.mark.parametrize("path", sorted(FIXTURES.glob("*.json")), ids=lambda path: path.stem)
def test_synthetic_fixture_replay_matches_expectations(path):
    document = json.loads(path.read_text(encoding="utf-8"))
    actual = replay_document(document)
    assert actual["final_state"] == document["expect"]["final_state"]
    assert actual["primary_preserved"] is document["expect"]["primary_preserved"]
    assert sum(actual["resources"][name] for name in (
        "secondary_streams", "listeners", "security_contexts", "decoders",
        "display_sinks", "pending_transactions", "unresolved_bundles",
    )) == document["expect"]["secondary_total"]
    assert actual["resources"]["sessions"] == 0
    assert actual == replay_document(document)
    assert [event["index"] for event in actual["events"]] == list(range(1, len(actual["events"]) + 1))


def test_replay_rejects_non_model_fixture():
    with pytest.raises(ReceiverError, match="synthetic_fixture_required"):
        replay_document({"evidence": "HONDA_STATIC", "steps": []})


@pytest.mark.parametrize("source", [
    "import socket", "from ctypes import CDLL", "import subprocess",
    "import os", "from usb import core", "import can", "import android",
    "open('fixture')", "Path('x').write_bytes(b'x')", "client.connect('x')",
    "'/dev/fb0'", "'/system/bin/target'", "import importlib", "getattr(x, 'open')",
])
def test_firewall_rejects_forbidden_source(source):
    assert check_source(source)


def test_firewall_accepts_pure_model_source():
    assert check_source("from dataclasses import dataclass\n@dataclass\nclass Value:\n    name: str") == []


@pytest.mark.parametrize("suffix", [".so", ".apk", ".bin", ".img", ".patch", ".ips"])
def test_firewall_rejects_deployable_artifact_extension(tmp_path, suffix):
    (tmp_path / f"mock{suffix}").write_text("invented")
    assert any("deployable-looking artifact" in item for item in check_tree(tmp_path))


def test_actual_sandbox_passes_firewall():
    assert check_tree() == []


def test_firewall_rejects_symlink(tmp_path):
    target = tmp_path / "target.txt"
    target.write_text("invented")
    (tmp_path / "link.py").symlink_to(target)
    assert any("symlink" in item for item in check_tree(tmp_path))


def test_fixture_corpus_has_required_cases():
    required = {
        "primary_only", "primary_plus_secondary", "secondary_disabled",
        "secondary_setup_failure", "listener_failure", "security_failure",
        "decoder_failure", "display_failure", "normal_stream", "stale_frame",
        "future_generation_frame", "duplicate_teardown", "session_reconnect",
        "rapid_reconnect", "partial_initialization_failure",
        "secondary_failure_primary_survives",
    }
    assert {path.stem for path in FIXTURES.glob("*.json")} == required
