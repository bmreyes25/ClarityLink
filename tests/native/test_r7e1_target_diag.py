from __future__ import annotations

import os
from pathlib import Path
import shutil
import subprocess
import sys


def test_target_diag_modes_and_100_bounded_lifecycles(tmp_path: Path) -> None:
    compiler = os.environ.get("CC") or shutil.which("clang") or shutil.which("cc")
    assert compiler is not None, "C compiler required for R7E1 native diagnostic test"
    repo = Path(__file__).resolve().parents[2]
    source = repo / "native/diagnostic/claritylink_target_diag.c"
    binary = tmp_path / "claritylink-target-diag"
    subprocess.run(
        [compiler, "-std=c11", "-O1", "-Wall", "-Wextra", "-Werror", str(source), "-o", str(binary)],
        check=True,
    )
    result = subprocess.run(
        [sys.executable, str(repo / "tools/test_r7e1_target_diag_modes.py"), str(binary), "--cycles", "100"],
        text=True,
        capture_output=True,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert "R7E1_DIAGNOSTIC_MODES_PASS cycles=100" in result.stdout
