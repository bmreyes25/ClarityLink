#!/usr/bin/env python3
"""Static scope guard for src/claritylink-sandbox only; no target inspection."""

from __future__ import annotations

import ast
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SANDBOX = ROOT / "src" / "claritylink-sandbox"
FORBIDDEN_IMPORTS = {
    "socket", "ctypes", "subprocess", "os", "asyncio", "multiprocessing",
    "serial", "usb", "can", "android", "jnius", "frida", "paramiko",
    "requests", "urllib", "ftplib", "telnetlib", "ssl", "builtins", "importlib",
}
FORBIDDEN_CALLS = {
    "open", "exec", "eval", "compile", "__import__", "Popen", "system",
    "popen", "connect", "bind", "listen", "send", "recv", "ioctl",
    "write_bytes", "write_text", "read_bytes", "read_text", "getattr", "setattr",
}
FORBIDDEN_SUFFIXES = {".so", ".apk", ".bin", ".img", ".patch", ".ips", ".bspatch"}
FORBIDDEN_PATH_MARKERS = ("/dev/", "/system/", "/vendor/", "/proc/")


def check_source(source: str, name: str = "<synthetic>") -> list[str]:
    try:
        tree = ast.parse(source, filename=name)
    except SyntaxError:
        return [f"{name}: invalid Python source"]
    violations: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imports = [alias.name.split(".", 1)[0] for alias in node.names]
            for imported in imports:
                if imported in FORBIDDEN_IMPORTS:
                    violations.append(f"{name}:{node.lineno}: forbidden import {imported}")
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported = node.module.split(".", 1)[0]
            if imported in FORBIDDEN_IMPORTS:
                violations.append(f"{name}:{node.lineno}: forbidden import {imported}")
        elif isinstance(node, ast.Call):
            called = node.func.id if isinstance(node.func, ast.Name) else (
                node.func.attr if isinstance(node.func, ast.Attribute) else ""
            )
            if called in FORBIDDEN_CALLS:
                violations.append(f"{name}:{node.lineno}: forbidden call {called}")
        elif isinstance(node, ast.Constant) and isinstance(node.value, str):
            if any(marker in node.value for marker in FORBIDDEN_PATH_MARKERS):
                violations.append(f"{name}:{node.lineno}: target path literal")
    return violations


def check_tree(root: Path = SANDBOX) -> list[str]:
    failures: list[str] = []
    for path in sorted(root.rglob("*")):
        if path.is_symlink():
            failures.append(f"{path.relative_to(root)}: sandbox symlink excluded")
            continue
        if not path.is_file():
            continue
        if path.suffix.lower() in FORBIDDEN_SUFFIXES:
            failures.append(f"{path.relative_to(root)}: deployable-looking artifact")
        if path.suffix == ".py":
            failures.extend(check_source(path.read_text(encoding="utf-8"), str(path.relative_to(root))))
    return failures


def main() -> int:
    failures = check_tree()
    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print("R5Y sandbox boundary: PASS (host-only scoped source and artifacts)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
