#!/usr/bin/env python3
"""Fail-closed filesystem ownership helpers for the isolated API17 runner."""
from __future__ import annotations

import argparse
import fcntl
import os
from pathlib import Path
import re
import secrets
import shutil
import sys
import tempfile
import time


OWNER_FILE = ".claritylink-run-owner"
AVD_OWNER_FILE = ".claritylink-avd-owner"
AVD_NAME = re.compile(r"climp03_api17_[0-9]+\Z")


class GuardError(ValueError):
    pass


def resolve_build_dir(repo: Path, candidate: Path) -> Path:
    repo = repo.resolve(strict=True)
    candidate = candidate if candidate.is_absolute() else repo / candidate
    if candidate.is_symlink() or not candidate.is_dir():
        raise GuardError("build directory must be an existing, non-symlink directory")
    parent = candidate.parent.resolve(strict=True)
    if (repo / "build").is_symlink():
        raise GuardError("repository build root must not be a symlink")
    repo_build = (repo / "build").resolve(strict=True) if (repo / "build").exists() else None
    if parent not in {repo_build, Path("/tmp"), Path("/private/tmp")}:
        raise GuardError("build directory must be a direct child of repo/build or /tmp")
    if not (candidate.name == "cl-imp-03" or candidate.name.startswith(("cl-imp-03-", "cl-r"))):
        raise GuardError("build directory name is not a ClarityLink campaign path")
    marker = candidate / ".claritylink-build-root"
    if marker.is_symlink() or not marker.is_file() or marker.read_text().strip() != str(repo):
        raise GuardError("build directory ownership marker is absent or mismatched")
    return candidate.resolve(strict=True)


def create_run_dir(repo: Path, candidate: Path) -> Path:
    build = resolve_build_dir(repo, candidate)
    runs = build / "runs"
    if runs.is_symlink():
        raise GuardError("run output directory must not be a symlink")
    runs.mkdir(mode=0o700, exist_ok=True)
    if runs.is_symlink() or not runs.is_dir():
        raise GuardError("run output directory is not an owned directory")
    run_dir = Path(tempfile.mkdtemp(prefix="cl-imp-03-run-", dir=str(runs)))
    os.chmod(run_dir, 0o700)
    token = secrets.token_hex(24)
    fd = os.open(str(run_dir / OWNER_FILE), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as handle:
        handle.write(token + "\n")
    return run_dir


def _run_root(path: Path) -> tuple[Path, str]:
    if path.is_symlink() or not path.is_dir() or not path.name.startswith("cl-imp-03-run-"):
        raise GuardError("run directory is not an owned campaign directory")
    root = path.resolve(strict=True)
    if root.parent.name != "runs" or root.parent.is_symlink():
        raise GuardError("run directory is outside its campaign output root")
    owner = root / OWNER_FILE
    if owner.is_symlink() or not owner.is_file():
        raise GuardError("run ownership marker is absent")
    token = owner.read_text(encoding="ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{48}", token):
        raise GuardError("run ownership marker is invalid")
    return root, token


def _avd_paths(run_dir: Path, name: str) -> tuple[Path, Path, Path]:
    if not AVD_NAME.fullmatch(name):
        raise GuardError("AVD name is not a campaign-generated name")
    root, _ = _run_root(run_dir)
    home = root / "avd"
    if home.is_symlink() or not home.is_dir() or home.resolve(strict=True) != home:
        raise GuardError("AVD home is not a real campaign-owned directory")
    return home, home / (name + ".avd"), home / (name + ".ini")


def assert_avd_absent(run_dir: Path, name: str) -> None:
    _, avd, ini = _avd_paths(run_dir, name)
    if avd.exists() or avd.is_symlink() or ini.exists() or ini.is_symlink():
        raise GuardError("refusing to overwrite an existing AVD or AVD index")


def mark_avd_owned(run_dir: Path, name: str) -> None:
    _, avd, ini = _avd_paths(run_dir, name)
    if avd.is_symlink() or not avd.is_dir() or ini.is_symlink() or not ini.is_file():
        raise GuardError("new AVD paths are incomplete or unsafe")
    _, token = _run_root(run_dir)
    marker = avd / AVD_OWNER_FILE
    fd = os.open(str(marker), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w", encoding="ascii") as handle:
        handle.write(token + "\n")


def cleanup_owned_avd(run_dir: Path, name: str) -> bool:
    _, avd, ini = _avd_paths(run_dir, name)
    _, token = _run_root(run_dir)
    marker = avd / AVD_OWNER_FILE
    if avd.is_symlink() or not avd.is_dir() or marker.is_symlink() or not marker.is_file():
        return False
    if marker.read_text(encoding="ascii").strip() != token:
        return False
    if ini.is_symlink() or (ini.exists() and not ini.is_file()):
        return False
    if avd.resolve(strict=True).parent != avd.parent.resolve(strict=True):
        return False
    shutil.rmtree(avd)
    if ini.exists():
        ini.unlink()
    return True


def is_owned_adb_child(
    expected_pid: int,
    shell_pid: int,
    observed_pid: int,
    observed_parent_pid: int,
    observed_executable: str,
    expected_executable: str,
    command_line: str,
    port: int,
) -> bool:
    """Accept cleanup ownership only for the exact foreground child we launched."""
    return (
        expected_pid > 0
        and expected_pid == observed_pid
        and observed_parent_pid == shell_pid
        and observed_executable == expected_executable
        and f"-P {port}" in command_line
        and "server nodaemon" in command_line
    )


def is_owned_adb_logcat_child(
    expected_pid: int,
    shell_pid: int,
    observed_pid: int,
    observed_parent_pid: int,
    observed_executable: str,
    expected_executable: str,
    command_line: str,
    port: int,
    serial: str,
) -> bool:
    """Accept cleanup only for this shell's exact isolated-device logcat child."""
    return (
        expected_pid > 0
        and expected_pid == observed_pid
        and observed_parent_pid == shell_pid
        and observed_executable == expected_executable
        and f"-P {port}" in command_line
        and f"-s {serial}" in command_line
        and "logcat -s ClarityLinkCLIMP03:I *:S" in command_line
    )


def parse_adb_inventory(output: str) -> list[tuple[str, str]]:
    """Retain every actual ADB serial/status pair, including offline/unauthorized."""
    rows: list[tuple[str, str]] = []
    for line in output.splitlines():
        fields = line.split()
        if len(fields) >= 2 and fields[0] != "List" and not fields[0].startswith("*"):
            rows.append((fields[0], fields[1]))
    return rows


def emulator_inventory_is_safe(rows: list[tuple[str, str]], serial: str,
                               exact_process_owned: bool) -> bool:
    if not rows:
        return True
    return exact_process_owned and rows in [[(serial, "offline")], [(serial, "device")]]


def hold_runner_lock(lock_path: Path, ready_path: Path, parent_pid: int) -> None:
    """Serialize runs and exit if the owning shell dies, releasing the OS lock."""
    lock_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    with lock_path.open("a+") as handle:
        fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
        ready_path.write_text(f"pid={os.getpid()} parent_pid={parent_pid} acquired_at={time.time():.6f}\n")
        os.chmod(ready_path, 0o600)
        while True:
            try:
                if os.getppid() != parent_pid:
                    return
                os.kill(parent_pid, 0)
            except ProcessLookupError:
                return
            time.sleep(0.25)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    commands = parser.add_subparsers(dest="command", required=True)
    resolve = commands.add_parser("resolve-build")
    resolve.add_argument("repo", type=Path)
    resolve.add_argument("build_dir", type=Path)
    create = commands.add_parser("create-run")
    create.add_argument("repo", type=Path)
    create.add_argument("build_dir", type=Path)
    run = commands.add_parser("check-avd")
    run.add_argument("run_dir", type=Path)
    run.add_argument("name")
    mark = commands.add_parser("mark-avd")
    mark.add_argument("run_dir", type=Path)
    mark.add_argument("name")
    cleanup = commands.add_parser("cleanup-avd")
    cleanup.add_argument("run_dir", type=Path)
    cleanup.add_argument("name")
    child = commands.add_parser("check-adb-child")
    child.add_argument("expected_pid", type=int)
    child.add_argument("shell_pid", type=int)
    child.add_argument("observed_pid", type=int)
    child.add_argument("observed_parent_pid", type=int)
    child.add_argument("observed_executable")
    child.add_argument("expected_executable")
    child.add_argument("command_line")
    child.add_argument("port", type=int)
    logcat_child = commands.add_parser("check-adb-logcat-child")
    logcat_child.add_argument("expected_pid", type=int)
    logcat_child.add_argument("shell_pid", type=int)
    logcat_child.add_argument("observed_pid", type=int)
    logcat_child.add_argument("observed_parent_pid", type=int)
    logcat_child.add_argument("observed_executable")
    logcat_child.add_argument("expected_executable")
    logcat_child.add_argument("command_line")
    logcat_child.add_argument("port", type=int)
    logcat_child.add_argument("serial")
    inventory = commands.add_parser("parse-inventory")
    inventory.add_argument("output", help="ADB devices output as one argument")
    target = commands.add_parser("check-emulator-inventory")
    target.add_argument("serial")
    target.add_argument("output")
    target.add_argument("--process-owned", action="store_true")
    lock = commands.add_parser("hold-lock")
    lock.add_argument("lock_path", type=Path)
    lock.add_argument("ready_path", type=Path)
    lock.add_argument("parent_pid", type=int)
    args = parser.parse_args(argv)
    try:
        if args.command == "resolve-build":
            print(resolve_build_dir(args.repo, args.build_dir))
        elif args.command == "create-run":
            print(create_run_dir(args.repo, args.build_dir))
        elif args.command == "check-avd":
            assert_avd_absent(args.run_dir, args.name)
        elif args.command == "mark-avd":
            mark_avd_owned(args.run_dir, args.name)
        elif args.command == "cleanup-avd":
            if not cleanup_owned_avd(args.run_dir, args.name):
                raise GuardError("AVD ownership could not be proven; leaving files untouched")
        elif args.command == "check-adb-child":
            if not is_owned_adb_child(
                args.expected_pid, args.shell_pid, args.observed_pid,
                args.observed_parent_pid, args.observed_executable,
                args.expected_executable, args.command_line, args.port,
            ):
                raise GuardError("ADB process is not this run's direct foreground child")
        elif args.command == "check-adb-logcat-child":
            if not is_owned_adb_logcat_child(
                args.expected_pid, args.shell_pid, args.observed_pid,
                args.observed_parent_pid, args.observed_executable,
                args.expected_executable, args.command_line, args.port, args.serial,
            ):
                raise GuardError("logcat process is not this run's direct isolated-ADB child")
        elif args.command == "parse-inventory":
            for serial, status in parse_adb_inventory(args.output):
                print(f"{serial} {status}")
        elif args.command == "check-emulator-inventory":
            rows = parse_adb_inventory(args.output)
            if not emulator_inventory_is_safe(rows, args.serial, args.process_owned):
                raise GuardError("ADB inventory contains an unexpected or unowned target")
        elif args.command == "hold-lock":
            hold_runner_lock(args.lock_path, args.ready_path, args.parent_pid)
        return 0
    except (OSError, GuardError) as error:
        print("API17 runner safety guard: " + str(error), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
