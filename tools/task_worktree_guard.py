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
import stat
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


def guard_run(command: list[str], *, timeout: int = 15) -> subprocess.CompletedProcess:
    try:
        return subprocess.run(command, text=True, capture_output=True, timeout=timeout)
    except subprocess.TimeoutExpired as exc:
        raise GuardError(f"command timed out after {timeout} seconds: {command[0]}") from exc


def git(root: Path, *args: str, check: bool = True) -> str:
    try:
        proc = subprocess.run(["git", "-C", str(root), *args], text=True,
                              capture_output=True, timeout=10)
    except subprocess.TimeoutExpired as exc:
        raise GuardError(f"git {args[0]} timed out after 10 seconds") from exc
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
    with scope_transaction(lock_dir):
        locks = _owned_reservation_locks(lock_dir, data)
        for lock in locks:
            lock.unlink()


def _owned_reservation_locks(lock_dir: Path, data: dict) -> list[Path]:
    expected = {"task_id": data["task_id"], "branch": data["branch"],
                "worktree": data["worktree"]}
    locks: list[Path] = []
    for path in data["files"]:
        lock = lock_dir / path_key(path)
        if not lock.is_file():
            raise GuardError(f"scope reservation is missing for {path}; preserve remaining state")
        owner = json.loads(lock.read_text())
        if any(owner.get(key) != value for key, value in expected.items()) or owner.get("path") != path:
            raise GuardError(f"scope reservation ownership mismatch for {path}; preserve remaining state")
        locks.append(lock)
    return locks


def verify_reservation_ownership(lock_dir: Path, data: dict) -> list[Path]:
    with scope_transaction(lock_dir):
        return _owned_reservation_locks(lock_dir, data)


def begin(root: Path, task: str, files: list[str], base: str = "main") -> dict:
    root = Path(git(root, "rev-parse", "--show-toplevel")).resolve()
    canonical_origin(root)
    branch = branch_and_owner(root)
    if base.startswith("-") or "@{" in base or subprocess.run(
            ["git", "check-ref-format", f"refs/heads/{base}"], capture_output=True).returncode:
        raise GuardError(f"invalid task base branch: {base}")
    dirty = porcelain(root)
    if dirty:
        raise GuardError("task start requires a clean worktree; preserve and reconcile existing changes first")
    git(root, "fetch", "--quiet", "origin", base)
    head = git(root, "rev-parse", "HEAD")
    base_sha = git(root, "rev-parse", f"refs/remotes/origin/{base}")
    if head != base_sha:
        raise GuardError(f"task branch must start at fetched origin/{base} ({base_sha}); current HEAD is {head}")
    paths = validate_paths(root, files)
    file, lock_dir = layout(root)
    owner = {"task_id": task, "branch": branch, "worktree": str(root),
             "started_at": int(time.time())}
    data = {**owner, "starting_sha": head, "base": base, "files": paths}
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


def bind_pull_request(root: Path, pr: int, base: str) -> dict:
    """Bind a continuation task to its published starting SHA's open stacked PR."""
    with manifest_transaction(root):
        file, _lock_dir, data = manifest(root)
        root = Path(data["worktree"])
        branch = data["branch"]
        changed = changed_paths(root)
        outside_scope = sorted(changed - set(data["files"]))
        if outside_scope:
            raise GuardError("PR binding found changes outside the task scope: " + ", ".join(outside_scope))
        if (not isinstance(base, str) or base.startswith("-") or "@{" in base or base == branch
                or subprocess.run(["git", "check-ref-format", f"refs/heads/{base}"],
                                  capture_output=True).returncode):
            raise GuardError("PR target base must be a literal branch distinct from the task branch")
        head = git(root, "rev-parse", "HEAD")
        if head != data["starting_sha"]:
            raise GuardError("PR binding must happen before task edits at the recorded starting SHA")
        remote = guard_run(["git", "-C", str(root), "ls-remote", "--heads", "origin",
                            f"refs/heads/{branch}"])
        remote_sha = remote.stdout.split()[0] if remote.returncode == 0 and remote.stdout.split() else ""
        if remote.returncode or remote_sha != head:
            raise GuardError("PR binding requires the recorded starting SHA to match the live branch")
        result = guard_run(["gh", "pr", "view", str(pr), "-R", "bmreyes25/ClarityLink",
                            "--json", "headRefName,headRefOid,baseRefName,state,isCrossRepository"])
        if result.returncode:
            raise GuardError("PR binding could not read the remote publication receipt: "
                             + (result.stderr or result.stdout).strip())
        try:
            receipt = json.loads(result.stdout)
        except (TypeError, ValueError) as exc:
            raise GuardError("PR binding could not parse the remote publication receipt") from exc
        if (result.returncode or not isinstance(receipt, dict)
                or receipt.get("headRefName") != branch
                or receipt.get("headRefOid") != head or receipt.get("baseRefName") != base
                or receipt.get("state") != "OPEN" or receipt.get("isCrossRepository") is not False):
            raise GuardError("PR binding requires an open PR matching the exact live task head and base")
        if base != "main":
            base_pr = guard_run(["gh", "pr", "list", "-R", "bmreyes25/ClarityLink",
                                 "--head", base, "--state", "open", "--json",
                                 "headRefName,isCrossRepository"])
            if base_pr.returncode:
                raise GuardError("PR binding could not inspect the stacked base PR: "
                                 + (base_pr.stderr or base_pr.stdout).strip())
            try:
                base_rows = json.loads(base_pr.stdout)
            except (TypeError, ValueError) as exc:
                raise GuardError("PR binding could not inspect the stacked base PR") from exc
            if (base_pr.returncode or not isinstance(base_rows, list)
                    or not any(isinstance(row, dict) and row.get("headRefName") == base
                               and row.get("isCrossRepository") is False
                               for row in base_rows)):
                raise GuardError("a stacked task base must itself be the head of an open PR")
        try:
            git(root, "fetch", "--quiet", "origin", base)
            ancestry = guard_run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                                  f"refs/remotes/origin/{base}", head], timeout=10)
        except subprocess.TimeoutExpired as exc:
            raise GuardError("base fetch or ancestry verification timed out") from exc
        if ancestry.returncode:
            raise GuardError("the live PR base is not an ancestor of the task branch")
        updated = {**data, "base": base, "pull_request": pr}
        atomic_manifest_write(file, updated)
        return updated


def classify(root: Path) -> dict:
    file, _lock_dir, data = manifest(root)
    status = porcelain(root)
    owned = set(data["files"])
    changed = changed_paths(Path(data["worktree"]))
    return {"manifest": str(file), "task_id": data["task_id"], "branch": data["branch"],
            "worktree": data["worktree"], "status": status,
            "scoped_pending": sorted(changed & owned), "outside_scope": sorted(changed - owned),
            "scope": data["files"]}


def finish(root: Path, pr: int, base: str | None = None) -> dict:
    with manifest_transaction(root):
        file, lock_dir, data = manifest(root)
        expected_base = data.get("base", "main")
        if (not isinstance(expected_base, str) or expected_base.startswith("-") or "@{" in expected_base
                or expected_base == data["branch"]
                or subprocess.run(["git", "check-ref-format", f"refs/heads/{expected_base}"],
                                  capture_output=True).returncode):
            raise GuardError("task manifest base branch is invalid; preserve its scope reservation")
        if base is not None and base != expected_base:
            raise GuardError(f"finish base {base} differs from task manifest base {expected_base}")
        base = expected_base
        state = classify(root)
        if state["status"]:
            raise GuardError("task completion requires a clean worktree; status=" + json.dumps(state["status"]))
        try:
            result = subprocess.run([sys.executable, str(Path(__file__).with_name("verify_remote_publication.py")),
                                     "--repo", str(root), "--pr", str(pr), "--base", base],
                                    text=True, capture_output=True, timeout=15)
        except subprocess.TimeoutExpired as exc:
            raise GuardError("remote verification timed out; preserve task scope reservations") from exc
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


def append_recovery_audit(audit_file: Path, audit: dict) -> None:
    if audit_file.is_symlink():
        raise GuardError("recovery audit path is a symlink; preserve task metadata")
    fd = os.open(audit_file, os.O_WRONLY | os.O_APPEND | os.O_CREAT |
                 getattr(os, "O_NOFOLLOW", 0), 0o600)
    audit_stat = os.fstat(fd)
    if (not stat.S_ISREG(audit_stat.st_mode) or audit_stat.st_mode & 0o077 or
            audit_stat.st_nlink != 1 or audit_stat.st_uid != os.geteuid()):
        os.close(fd)
        raise GuardError("recovery audit file must be private, singly linked, and owned by this user")
    with os.fdopen(fd, "a") as stream:
        stream.write(json.dumps(audit, sort_keys=True) + "\n")
        stream.flush()
        os.fsync(stream.fileno())


def recover_self_base_and_finish(root: Path, pr: int) -> dict:
    """Repair only a verified self-base manifest, then use ordinary finish gates.

    This command never releases reservations itself. It verifies ownership, scope,
    remote branch, PR head/base, and ancestry; records an audit event; corrects the
    manifest base atomically; then delegates reservation release to ``finish``.
    """
    with manifest_transaction(root):
        file, lock_dir, data = manifest(root)
        root = Path(data["worktree"])
        branch = data["branch"]
        canonical_origin(root)
        if branch_and_owner(root) != branch:
            raise GuardError("task branch ownership changed; preserve its reservation")
        if porcelain(root):
            raise GuardError("recovery requires a clean worktree; preserve its reservation")
        verify_reservation_ownership(lock_dir, data)

        head = git(root, "rev-parse", "HEAD")
        remote = guard_run(["git", "ls-remote", "--heads", "origin", f"refs/heads/{branch}"])
        remote_sha = remote.stdout.split()[0] if remote.returncode == 0 and remote.stdout.split() else ""
        if remote.returncode or remote_sha != head:
            raise GuardError("remote task branch does not match exact local HEAD")

        pr_result = guard_run(["gh", "pr", "view", str(pr), "-R", "bmreyes25/ClarityLink",
                               "--json", "headRefName,headRefOid,baseRefName,state,isCrossRepository"])
        if pr_result.returncode:
            raise GuardError("recovery could not read the task PR: " +
                             (pr_result.stderr or pr_result.stdout).strip())
        try:
            receipt = json.loads(pr_result.stdout)
        except (TypeError, ValueError) as exc:
            raise GuardError("recovery could not parse the task PR receipt") from exc
        if (not isinstance(receipt, dict) or receipt.get("headRefName") != branch or
                receipt.get("headRefOid") != head or receipt.get("state") != "OPEN" or
                receipt.get("isCrossRepository") is not False):
            raise GuardError("recovery requires an open same-repository PR at exact task HEAD")
        base = receipt.get("baseRefName")
        if (not isinstance(base, str) or not base or base == branch or base.startswith("-") or
                "@{" in base or subprocess.run(["git", "check-ref-format", f"refs/heads/{base}"],
                                               capture_output=True).returncode):
            raise GuardError("verified PR base is invalid or not distinct from task branch")
        old_base = data.get("base", "main")
        if old_base not in (branch, base):
            raise GuardError("manifest base is not the known self-base corruption or verified PR base")

        if base != "main":
            base_pr_result = guard_run(["gh", "pr", "list", "-R", "bmreyes25/ClarityLink",
                                        "--head", base, "--state", "open", "--json",
                                        "headRefName,isCrossRepository"])
            if base_pr_result.returncode:
                raise GuardError("recovery could not inspect the stacked PR base")
            try:
                base_prs = json.loads(base_pr_result.stdout)
            except (TypeError, ValueError) as exc:
                raise GuardError("recovery could not parse the stacked PR base list") from exc
            if (not isinstance(base_prs, list) or not any(
                    isinstance(item, dict) and item.get("headRefName") == base and
                    item.get("isCrossRepository") is False for item in base_prs)):
                raise GuardError("stacked PR base is not the head of an open same-repository PR")

        git(root, "fetch", "--quiet", "origin", base)
        base_ancestor = guard_run(["git", "-C", str(root), "merge-base", "--is-ancestor",
                                  f"refs/remotes/origin/{base}", head], timeout=10)
        if base_ancestor.returncode:
            raise GuardError("verified PR base is not an ancestor of task HEAD")

        starting_sha = data["starting_sha"]
        actual_start = git(root, "merge-base", f"refs/remotes/origin/{base}", head)
        if starting_sha != actual_start:
            raise GuardError("recorded start is not the independently verified PR branch point")
        merges = git(root, "rev-list", "--merges", f"{starting_sha}..{head}")
        if merges:
            raise GuardError("recovery refuses merge history because exact per-commit scope is ambiguous")
        changed = guard_run(["git", "-C", str(root), "log", "--no-renames", "--format=", "--name-only", "-z",
                             f"{starting_sha}..{head}"])
        if changed.returncode:
            raise GuardError("could not verify every committed task path")
        changed_paths_from_start = {path for path in changed.stdout.split("\0") if path}
        outside_scope = sorted(changed_paths_from_start - set(data["files"]))
        if outside_scope:
            raise GuardError("task history contains paths outside its reservation: " +
                             ", ".join(outside_scope))

        verifier = Path(__file__).with_name("verify_remote_publication.py")
        verification = guard_run([sys.executable, str(verifier), "--repo", str(root),
                                  "--pr", str(pr), "--base", base], timeout=20)
        if verification.returncode:
            raise GuardError("ordinary publication verification failed; reservation remains held: " +
                             (verification.stderr or verification.stdout).strip())
        try:
            publication = json.loads(verification.stdout)
        except (TypeError, ValueError) as exc:
            raise GuardError("ordinary publication verification returned invalid JSON") from exc
        if publication.get("result") != "REMOTE_VERIFIED" or publication.get("remote_sha") != head:
            raise GuardError("ordinary publication verification did not confirm exact task HEAD")

        if old_base == branch:
            manifest_dir = file.parent
            audit_file = manifest_dir / "claritylink-task-recovery.jsonl"
            audit = {"event": "self_base_manifest_repair", "task_id": data["task_id"],
                     "branch": branch, "worktree": str(root), "starting_sha": starting_sha,
                     "head": head, "pr": pr, "old_base": old_base, "verified_base": base,
                     "verified_at": int(time.time())}
            append_recovery_audit(audit_file, audit)
            data = {**data, "base": base, "pull_request": pr}
            atomic_manifest_write(file, data)

    completion = finish(root, pr, base)
    return {"result": "TASK_RECOVERY_COMPLETE", "recovery": "self_base_manifest_repaired",
            "base": base, "head": head, "pr": pr, "completion": completion}


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("command", choices=("begin", "extend", "bind-pr", "status", "finish",
                                             "recover-finish", "preflight", "postflight"))
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--task")
    parser.add_argument("--file", action="append", default=[])
    parser.add_argument("--pr", type=int)
    parser.add_argument("--base", help="task or PR base branch; defaults to main on begin and task manifest on finish")
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    try:
        root = Path(git(args.repo, "rev-parse", "--show-toplevel")).resolve()
        if args.command == "begin":
            if not args.task:
                raise GuardError("begin requires --task")
            data = begin(root, args.task, args.file, args.base or "main")
            result = {"result": "TASK_STARTED", **data}
        elif args.command == "extend":
            result = {"result": "SCOPE_EXTENDED", **extend(root, args.file)}
        elif args.command == "bind-pr":
            if not args.pr or not args.base:
                raise GuardError("bind-pr requires --pr and --base")
            result = {"result": "TASK_BOUND_TO_PR", **bind_pull_request(root, args.pr, args.base)}
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
                raise GuardError(f"{args.command} requires --pr for live remote and PR verification")
            if args.command == "recover-finish":
                if args.base is not None:
                    raise GuardError("recover-finish derives its base from the verified PR; omit --base")
                result = recover_self_base_and_finish(root, args.pr)
            else:
                result = finish(root, args.pr, args.base)
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
