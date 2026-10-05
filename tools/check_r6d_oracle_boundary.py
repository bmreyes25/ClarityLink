#!/usr/bin/env python3
"""Reject device-opening and process-launching APIs in R6D oracle code."""
from __future__ import annotations

import ast
from pathlib import Path
import sys


TARGET = Path(__file__).resolve().parents[1] / "src/claritylink-jmcs/claritylink_jmcs/mfi_oracle.py"
FORBIDDEN_IMPORTS = {"os", "fcntl", "smbus", "smbus2", "periphery", "subprocess", "io", "ctypes"}
FORBIDDEN_CALLS = {"open", "exec", "eval", "__import__"}


def check(path: Path = TARGET) -> list[str]:
    tree = ast.parse(path.read_text(), filename=str(path))
    errors: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name.split(".")[0] in FORBIDDEN_IMPORTS:
                    errors.append(f"line {node.lineno}: forbidden import {alias.name}")
        elif isinstance(node, ast.ImportFrom) and (node.module or "").split(".")[0] in FORBIDDEN_IMPORTS:
            errors.append(f"line {node.lineno}: forbidden import {node.module}")
        elif isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
            errors.append(f"line {node.lineno}: forbidden call {node.func.id}")
    return errors


if __name__ == "__main__":
    failures = check()
    if failures:
        print("\n".join(failures), file=sys.stderr)
        raise SystemExit(1)
    print("R6D oracle boundary: PASS")
