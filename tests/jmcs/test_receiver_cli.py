"""CLI replay confirms sanitized traces and no external endpoint requirement."""
from __future__ import annotations

import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
TOOL = ROOT / "tools" / "r5z_receiver_lab.py"
FIXTURE = ROOT / "tests" / "fixtures" / "r5z" / "sanitized-setup.json"


def test_cli_replay_and_synthetic_client() -> None:
    for mode in ("replay", "captured-setup", "synthetic-client"):
        command = [sys.executable, str(TOOL), mode]
        if mode != "synthetic-client":
            command += ["--setup-json", str(FIXTURE)]
        result = subprocess.run(command, capture_output=True, text=True, timeout=10, check=True)
        payload = json.loads(result.stdout)
        assert payload["after_teardown"]["secondary_listeners"] == 0
        assert payload["response_stream_types"] in ([111, 110], [110, 111])
        assert "1111" not in result.stdout
        if mode == "synthetic-client":
            assert payload["frames"] == 1
