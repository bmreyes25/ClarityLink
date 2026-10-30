#!/usr/bin/env python3
"""Explicit-scope task transaction guard for ClarityLink Git worktrees.

The guard stores its manifest and reservations in Git's administrative area,
not the source tree. It never stages, commits, pushes, or deletes source files.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import time

REPO_URLS = {
    "https://github.com/bmreyes25/ClarityLink.git",
    "git@github.com:bmreyes25/ClarityLink.git",
    "ssh://git@github.com/bmreyes25/ClarityLink.git",
}
PRIVATE_PARTS = {
    "captures", "private-captures", "acquisition", "extracted", "decompiled",
    "decompiled-clean", "deodexed", "firmware", "vendor-dumps", "raw-evidence",
    "evidence", "handoff", "private", "private-research", "restricted",
    ".local-backups", ".local-artifacts", "raw-data", "vehicle-data",
}
PRIVATE_SUFFIXES = {
    ".apk", ".dex", ".odex", ".so", ".img", ".bin", ".tar", ".gz", ".zip",
    ".pcap", ".pcapng", ".dump", ".raw", ".keystore", ".jks", ".p12", ".pem",
    ".key", ".mp4", ".mov", ".elf",
}


class GuardError(RuntimeError):
    pass


def git(root: Path, *args: str, check: bool = True) -> str:
    proc = subprocess.run(["git", "-C", str(root), *args], text=True,
                          capture_output=True, timeout=10)
    if check and proc.returncode:
        raise GuardError((proc.stderr or proc.stdout).strip() or f"git {args[0]} failed")
    return proc.stdout.strip()


def layout(root: Path) -> tuple[Path, Path]:
    root = Path(git(root, "rev-parse", "--show-toplevel")).resolve()
    git_dir = Path(git(root, "rev-parse", "--git-dir"))
    if not git_dir.is_absolute():
        git_dir = (root / git_dir).resolve()
    common = Path(git(root, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = (root / common).resolve()
    return git_dir / "claritylink-task.json", common / "claritylink-task-scopes"


def porcelain(root: Path) -> list[str]:
    return git(root, "status", "--porcelain=v2", "--untracked-files=all").splitlines()


def changed_paths(root: Path) -> set[str]:
    proc = subprocess.run(["git", "-C", str(root), "status", "--porcelain=v2", "-z",
                           "--untracked-files=all"], capture_output=True, timeout=10)
    if proc.returncode:
        raise GuardError((proc.stderr.decode(errors="replace")).strip())
    records = proc.stdout.decode(errors="surrogateescape").split("\0")
    found: set[str] = set()
    index = 0
    while index < len(records):
        record = records[index]
        index += 1
        if not record:
            continue
        if record.startswith("1 "):
            fields = record.split(" ", 8)
            if len(fields) == 9:
                found.add(fields[8])
        elif record.startswith("u "):
            fields = record.split(" ", 10)
            if len(fields) == 11:
                found.add(fields[10])
        elif record.startswith("2 "):
            fields = record.split(" ", 9)
            if len(fields) == 10:
                found.add(fields[9])
            if index < len(records) and records[index]:
                found.add(records[index])
                index += 1
        elif record.startswith("? "):
            found.add(record[2:])
    return found


def branch_and_owner(root: Path) -> str:
    branch = git(root, "branch", "--show-current")
    if not branch or branch in {"main", "master"}:
        raise GuardError("task work must use an owned feature branch")
    records = git(root, "worktree", "list", "--porcelain").split("\n\n")
    owners = []
    for record in records:
        lines = record.splitlines()
        path = next((line[9:] for line in lines if line.startswith("worktree ")), "")
        ref = next((line[7:] for line in lines if line.startswith("branch ")), "")
        if ref == f"refs/heads/{branch}":
            owners.append(Path(path).resolve())
    if owners != [root.resolve()]:
        raise GuardError("branch ownership is ambiguous; another worktree may own this branch")
    return branch


def canonical_origin(root: Path) -> None:
    if git(root, "remote", "get-url", "origin") not in REPO_URLS:
        raise GuardError("origin is absent or not canonical bmreyes25/ClarityLink")


def validate_paths(root: Path, values: list[str]) -> list[str]:
    if not values:
        raise GuardError("provide one or more exact --file paths")
    result = []
    for value in values:
        rel = Path(value)
        if rel.is_absolute() or ".." in rel.parts or not value or any(x in value for x in "*?[]"):
            raise GuardError(f"invalid scoped path: {value}")
        candidate = root / rel
        cursor = root
        for part in rel.parts:
            cursor = cursor / part
            if cursor.is_symlink():
                raise GuardError(f"symlink paths cannot be reserved for publication: {value}")
        resolved = candidate.resolve()
        if root.resolve() not in resolved.parents:
            raise GuardError(f"path escapes the worktree: {value}")
        if any(part.lower() in PRIVATE_PARTS for part in rel.parts) or rel.suffix.lower() in PRIVATE_SUFFIXES:
            raise GuardError(f"restricted path cannot be reserved for a task: {value}")
        ignored = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", "--", value]).returncode == 0
        if ignored:
            raise GuardError(f"ignored path cannot be reserved for a task: {value}")
        if resolved.exists() and resolved.is_dir():
            raise GuardError(f"scope must name files, not directories: {value}")
        if resolved.is_file() and b"\0" in resolved.read_bytes()[:8192]:
            raise GuardError(f"binary files are not accepted in a source task scope: {value}")
        result.append(rel.as_posix())
    if len(set(result)) != len(result):
        raise GuardError("duplicate scope paths are not allowed")
    return result


def path_key(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


@contextmanager
def scope_transaction(lock_dir: Path):
    lock_dir.mkdir(parents=True, exist_ok=True)
    lock_dir.chmod(0o700)
    fd = os.open(lock_dir / ".transaction.lock", os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "r+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@contextmanager
def manifest_transaction(root: Path):
    manifest_file, _lock_dir = layout(root)
    path = manifest_file.with_suffix(".transaction.lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    fd = os.open(path, os.O_RDWR | os.O_CREAT, 0o600)
    with os.fdopen(fd, "r+") as stream:
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


def atomic_manifest_write(file: Path, data: dict) -> None:
    temp = file.with_name(file.name + f".{os.getpid()}.tmp")
    fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "w") as stream:
        json.dump(data, stream, indent=2, sort_keys=True)
        stream.write("\n")
    temp.replace(file)


def reserve(lock_dir: Path, paths: list[str], owner: dict) -> None:
    with scope_transaction(lock_dir):
        created: list[Path] = []
        try:
            for value in paths:
                lock = lock_dir / path_key(value)
                fd = os.open(lock, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
                with os.fdopen(fd, "w") as stream:
                    json.dump({**owner, "path": value}, stream, sort_keys=True)
                    stream.write("\n")
                created.append(lock)
        except FileExistsError as exc:
            for lock in created:
                lock.unlink(missing_ok=True)
            try:
                holder = json.loads(exc.filename and Path(exc.filename).read_text())
            except Exception:
                holder = {"owner": "unknown; inspect Git metadata before resolving"}
            raise GuardError(f"scope reservation is already held ({holder})") from exc
        except Exception:
            for lock in created:
                lock.unlink(missing_ok=True)
            raise


def manifest(root: Path) -> tuple[Path, Path, dict]:
    file, lock_dir = layout(root)
    if not file.is_file():
        raise GuardError("no active task scope; begin a task with explicit --file paths")
    data = json.loads(file.read_text())
    if not isinstance(data, dict) or not isinstance(data.get("files"), list) or not data["files"]:
        raise GuardError("task manifest is malformed; preserve its reservations for manual inspection")
    if (not isinstance(data.get("worktree"), str) or not isinstance(data.get("branch"), str)
            or not isinstance(data.get("task_id"), str) or not isinstance(data.get("starting_sha"), str)
            or any(not isinstance(path, str) for path in data["files"])):
        raise GuardError("task manifest identity is malformed; preserve its reservations")
    if data["worktree"] != str(Path(git(root, "rev-parse", "--show-toplevel")).resolve()):
        raise GuardError("task manifest belongs to a different worktree; preserve its reservations")
    if data["branch"] != branch_and_owner(Path(data["worktree"])):
        raise GuardError("task manifest belongs to a different branch; preserve its reservations")
    if len(set(data["files"])) != len(data["files"]):
        raise GuardError("task manifest contains duplicate paths; preserve its reservations")
    return file, lock_dir, data


def release_reservations(lock_dir: Path, data: dict) -> None:
    expected = {"task_id": data["task_id"], "branch": data["branch"],
                "worktree": data["worktree"]}
    with scope_transaction(lock_dir):
        locks: list[Path] = []
        for path in data["files"]:
            lock = lock_dir / path_key(path)
            if not lock.is_file():
                raise GuardError(f"scope reservation is missing for {path}; preserve remaining state")
            owner = json.loads(lock.read_text())
            if any(owner.get(key) != value for key, value in expected.items()) or owner.get("path") != path:
                raise GuardError(f"scope reservation ownership mismatch for {path}; preserve remaining state")
            locks.append(lock)
        for lock in locks:
            lock.unlink()


def begin(root: Path, task: str, files: list[str]) -> dict:
    root = Path(git(root, "rev-parse", "--show-toplevel")).resolve()
    canonical_origin(root)
    branch = branch_and_owner(root)
    dirty = porcelain(root)
    if dirty:
        raise GuardError("task start requires a clean worktree; preserve and reconcile existing changes first")
    git(root, "fetch", "--quiet", "origin", "main")
    head = git(root, "rev-parse", "HEAD")
    main = git(root, "rev-parse", "refs/remotes/origin/main")
    if head != main:
        raise GuardError(f"task branch must start at fetched origin/main ({main}); current HEAD is {head}")
    paths = validate_paths(root, files)
    file, lock_dir = layout(root)
    owner = {"task_id": task, "branch": branch, "worktree": str(root),
             "started_at": int(time.time())}
    data = {**owner, "starting_sha": head, "files": paths}
    with manifest_transaction(root):
        temp = file.with_name(file.name + f".{os.getpid()}.tmp")
        fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        try:
            with os.fdopen(fd, "w") as stream:
                json.dump(data, stream, indent=2, sort_keys=True)
                stream.write("\n")
            try:
                os.link(temp, file)
            except FileExistsError as exc:
                raise GuardError("this worktree already has an active task manifest") from exc
            reserve(lock_dir, paths, owner)
        except Exception:
            try:
                if file.is_file() and json.loads(file.read_text()) == data:
                    file.unlink()
            except Exception:
                pass
            raise
        finally:
            temp.unlink(missing_ok=True)
    return data


def extend(root: Path, files: list[str]) -> dict:
    with manifest_transaction(root):
        file, lock_dir, data = manifest(root)
        paths = validate_paths(Path(data["worktree"]), files)
        additions = [path for path in paths if path not in data["files"]]
        if not additions:
            raise GuardError("no new scope paths were provided")
        reserve(lock_dir, additions, {k: data[k] for k in ("task_id", "branch", "worktree", "started_at")})
        data["files"].extend(additions)
        atomic_manifest_write(file, data)
        return data


def classify(root: Path) -> dict:
    file, _lock_dir, data = manifest(root)
    status = porcelain(root)
    owned = set(data["files"])
    changed = changed_paths(Path(data["worktree"]))
    return {"manifest": str(file), "task_id": data["task_id"], "branch": data["branch"],
            "worktree": data["worktree"], "status": status,
            "scoped_pending": sorted(changed & owned), "outside_scope": sorted(changed - owned),
            "scope": data["files"]}


def finish(root: Path, pr: int) -> dict:
    with manifest_transaction(root):
        file, lock_dir, data = manifest(root)
        state = classify(root)
        if state["status"]:
            raise GuardError("task completion requires a clean worktree; status=" + json.dumps(state["status"]))
        result = subprocess.run([sys.executable, str(Path(__file__).with_name("verify_remote_publication.py")),
                                 "--repo", str(root), "--pr", str(pr)],
                                text=True, capture_output=True, timeout=15)
        try:
            receipt = json.loads(result.stdout)
        except ValueError:
            receipt = {"result": "VERIFY_FAILED", "reason": result.stderr[-500:]}
        if result.returncode or receipt.get("result") != "REMOTE_VERIFIED":
            raise GuardError("remote branch/PR is not verified; scope remains reserved: " + json.dumps(receipt))
        release_reservations(lock_dir, data)
        file.unlink()
        return {"result": "TASK_COMPLETE", "task_id": data["task_id"], "branch": data["branch"],
                "head": receipt.get("head"), "pr": receipt.get("pr")}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("begin", "extend", "status", "finish", "preflight", "postflight"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--task")
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--pr", type=int)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        root = Path(git(args.repo, "rev-parse", "--show-toplevel")).resolve()
        if args.command == "begin":
            if not args.task:
                raise GuardError("begin requires --task")
            data = begin(root, args.task, args.file)
            result = {"result": "TASK_STARTED", **data}
        elif args.command == "extend":
            result = {"result": "SCOPE_EXTENDED", **extend(root, args.file)}
        elif args.command in ("status", "postflight"):
            try:
                result = {"result": "TASK_STATUS", **classify(root)}
            except GuardError as exc:
                if args.command == "postflight" and "no active task scope" in str(exc):
                    result = {"result": "NO_ACTIVE_TASK", "status": porcelain(root)}
                else:
                    raise
        elif args.command == "preflight":
            status = porcelain(root)
            result = {"result": "READY" if not status else "DIRTY_WORKTREE", "status": status,
                      "instruction": "begin with an exact scope before editing" if not status else "preserve and reconcile; do not enter"}
        else:
            if not args.pr:
                raise GuardError("finish requires --pr for live remote and PR verification")
            result = finish(root, args.pr)
        if args.command == "postflight" and result.get("result") == "TASK_STATUS":
            if not result.get("status"):
                result["next_step"] = "run tools/task_worktree_guard.py finish --pr <open-pr-number> after the published branch and PR SHA verify"
            else:
                result["next_step"] = "review every listed path; publish the explicit reviewed scope or preserve and resolve it"
        print(json.dumps(result, sort_keys=True) if args.json else json.dumps(result, indent=2, sort_keys=True))
        if args.command == "postflight" and result.get("result") == "TASK_STATUS":
            return 1
        return 0
    except (GuardError, OSError, subprocess.SubprocessError, ValueError) as exc:
        error = {"result": "BLOCKED", "reason": str(exc)}
        print(json.dumps(error, sort_keys=True) if args.json else json.dumps(error, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
