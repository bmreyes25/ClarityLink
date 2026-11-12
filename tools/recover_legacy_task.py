#!/usr/bin/env python3
"""Prepare and commit an audited transfer from a legacy Studio task.

The source worktree is never changed. The target must be a clean feature
worktree at the exact live base. Recovery copies only the source task's
reserved tree delta, records private provenance in the shared Git directory,
and transfers reservations while holding the Studio scope lock.
"""
from __future__ import annotations

import argparse
from contextlib import ExitStack, contextmanager
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import uuid
import fcntl

GUARD_PATH = Path(__file__).with_name("task_worktree_guard.py")
SPEC = importlib.util.spec_from_file_location("task_worktree_guard", GUARD_PATH)
guard = importlib.util.module_from_spec(SPEC)
assert SPEC.loader is not None
SPEC.loader.exec_module(guard)


def fail(message: str) -> None:
    raise guard.GuardError(message)


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def authorization_statement(receipt: dict, receipt_sha256: str) -> str:
    return (f"I AUTHORIZE TRANSFER {receipt['source_task_id']} TO {receipt['target_task_id']} "
            f"TRANSACTION {receipt['transaction_id']} TARGET {receipt['target_branch']}@"
            f"{receipt['target_starting_sha']} RECEIPT {receipt_sha256}")


def text_sha(root: Path, *args: str) -> str:
    return sha256_bytes(guard.git(root, *args).encode())


def private_store(root: Path) -> Path:
    _manifest, _locks = guard.layout(root)
    common = Path(guard.git(root, "rev-parse", "--git-common-dir"))
    if not common.is_absolute():
        common = (root / common).resolve()
    store = common / "claritylink-legacy-recovery"
    if store.is_symlink():
        fail("private recovery store is a symlink")
    try:
        store.mkdir(mode=0o700)
    except FileExistsError:
        pass
    store_stat = store.stat()
    if (not store.is_dir() or store_stat.st_uid != os.geteuid() or store_stat.st_mode & 0o077):
        fail("private recovery store must be a private directory owned by this user")
    return store


@contextmanager
def recovery_lock(store: Path):
    lock_path = store / ".operation.lock"
    fd = os.open(lock_path, os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "r+") as stream:
        stat = os.fstat(stream.fileno())
        if (not os.path.isfile(lock_path) or stat.st_uid != os.geteuid() or
                stat.st_mode & 0o077 or stat.st_nlink != 1):
            fail("recovery operation lock must be a private singly-linked regular file")
        fcntl.flock(stream.fileno(), fcntl.LOCK_EX)
        try:
            yield
        finally:
            fcntl.flock(stream.fileno(), fcntl.LOCK_UN)


@contextmanager
def manifest_locks(*roots: Path):
    with ExitStack() as stack:
        for root in sorted({Path(value).resolve() for value in roots}, key=str):
            stack.enter_context(guard.manifest_transaction(root))
        yield


def private_write(path: Path, data: bytes, *, exclusive: bool = False) -> None:
    if path.is_symlink():
        fail("recovery receipt path is a symlink")
    flags = os.O_WRONLY | os.O_CREAT | (os.O_EXCL if exclusive else os.O_TRUNC)
    fd = os.open(path, flags | getattr(os, "O_NOFOLLOW", 0), 0o600)
    with os.fdopen(fd, "wb") as stream:
        stream.write(data)
        stream.flush()
        os.fsync(stream.fileno())


def private_update_json(path: Path, data: dict) -> None:
    temp = path.with_name(path.name + f".{os.getpid()}.tmp")
    if temp.exists() or temp.is_symlink():
        fail("private recovery state temp path already exists")
    private_write(temp, (json.dumps(data, sort_keys=True, indent=2) + "\n").encode(), exclusive=True)
    os.replace(temp, path)
    fd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(fd)
    finally:
        os.close(fd)


def read_json(path: Path) -> dict:
    if path.is_symlink() or not path.is_file():
        fail("recovery transaction receipt is missing or unsafe")
    stat = path.stat()
    if stat.st_uid != os.geteuid() or stat.st_mode & 0o077 or stat.st_nlink != 1:
        fail("recovery transaction receipt must be private and owned by this user")
    try:
        data = json.loads(path.read_text())
    except (OSError, ValueError) as exc:
        raise guard.GuardError("recovery transaction receipt is unreadable") from exc
    if not isinstance(data, dict):
        fail("recovery transaction receipt is malformed")
    return data


def manifest_for(root: Path) -> tuple[Path, Path, dict]:
    file, locks = guard.layout(root)
    if not file.is_file():
        fail("legacy source has no Studio task manifest")
    stat = file.stat()
    if file.is_symlink() or stat.st_uid != os.geteuid() or stat.st_mode & 0o077 or stat.st_nlink != 1:
        fail("legacy source task manifest is not private, singly linked, and owner-controlled")
    data = json.loads(file.read_text())
    required = ("task_id", "branch", "worktree", "starting_sha", "files")
    if any(not isinstance(data.get(key), str if key != "files" else list) for key in required):
        fail("legacy source task manifest has incomplete identity")
    if data["worktree"] != str(root.resolve()) or guard.branch_and_owner(root) != data["branch"]:
        fail("legacy source worktree or branch ownership is ambiguous")
    if len(data["files"]) != len(set(data["files"])) or not data["files"]:
        fail("legacy source task scope is empty or ambiguous")
    if not isinstance(data.get("started_at"), int):
        fail("legacy source task manifest lacks its reservation ownership timestamp")
    if guard.validate_paths(root, data["files"]) != data["files"]:
        fail("legacy source scope differs from its validated exact paths")
    return file, locks, data


def verify_source_reservations(lock_dir: Path, data: dict) -> None:
    for path in data["files"]:
        lock = lock_dir / guard.path_key(path)
        if not lock.is_file() or lock.is_symlink():
            fail(f"legacy source reservation is missing or unsafe for {path}")
        try:
            owner = json.loads(lock.read_text())
        except (OSError, ValueError) as exc:
            raise guard.GuardError(f"legacy source reservation is unreadable for {path}") from exc
        expected = {"task_id": data["task_id"], "branch": data["branch"],
                    "worktree": data["worktree"], "started_at": data["started_at"],
                    "path": path}
        if owner != expected:
            fail(f"legacy source reservation ownership mismatch for {path}")


def verify_source(root: Path, *, verify_locks: bool = True) -> tuple[Path, Path, dict, str, str, bytes, set[str]]:
    root = Path(guard.git(root, "rev-parse", "--show-toplevel")).resolve()
    guard.canonical_origin(root)
    manifest_path, lock_dir, data = manifest_for(root)
    if verify_locks:
        with guard.scope_transaction(lock_dir):
            verify_source_reservations(lock_dir, data)
    start = data["starting_sha"]
    head = guard.git(root, "rev-parse", "HEAD")
    remote = guard.guard_run(["git", "-C", str(root), "ls-remote", "--heads", "origin",
                              f"refs/heads/{data['branch']}"])
    if remote.returncode:
        fail("could not verify whether the legacy branch has a published remote head")
    if remote.stdout.strip():
        fail("legacy branch already has a remote head; use the published-branch continuation workflow")
    if guard.git(root, "cat-file", "-t", start, check=False) != "commit":
        fail("recorded task starting SHA is not a local commit")
    if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", start, head],
                      capture_output=True).returncode:
        fail("recorded task starting SHA is not an ancestor of the owner branch")
    if guard.git(root, "rev-list", "--merges", f"{start}..{head}"):
        fail("legacy task contains merge history; per-commit source attribution is ambiguous")
    committed = subprocess.run(["git", "-C", str(root), "log", "--format=", "--name-only", "-z",
                                "--no-renames", f"{start}..{head}"], text=True,
                               capture_output=True, timeout=20)
    if committed.returncode:
        fail("could not enumerate legacy task commit paths")
    committed_paths = {value for value in committed.stdout.split("\0") if value}
    working_paths = guard.changed_paths(root)
    untracked = subprocess.run(["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "-z"],
                               capture_output=True, timeout=10)
    if untracked.returncode or untracked.stdout:
        fail("legacy recovery refuses untracked source files; add them through a separately reviewed scope")
    all_paths = committed_paths | working_paths
    scope = set(data["files"])
    outside = sorted(all_paths - scope)
    if outside:
        fail("legacy task contains paths outside its recorded reservations: " + ", ".join(outside))
    patch = subprocess.run(["git", "-C", str(root), "diff", "--binary", "--full-index", start,
                            "--", *data["files"]], capture_output=True, timeout=30)
    if patch.returncode:
        fail("could not capture the exact reserved source delta")
    return manifest_path, lock_dir, data, head, guard.git(root, "rev-parse", "HEAD^{tree}"), patch.stdout, all_paths


def verify_target(root: Path, base: str) -> tuple[str, str]:
    root = Path(guard.git(root, "rev-parse", "--show-toplevel")).resolve()
    guard.canonical_origin(root)
    branch = guard.branch_and_owner(root)
    if guard.porcelain(root):
        fail("recovery target must be a clean worktree")
    target_manifest, _locks = guard.layout(root)
    if target_manifest.exists() or target_manifest.is_symlink():
        fail("recovery target already has a task manifest")
    if (base.startswith("-") or "@{" in base or base == branch or
            subprocess.run(["git", "check-ref-format", f"refs/heads/{base}"],
                           capture_output=True).returncode):
        fail("recovery target base is invalid or self-referential")
    guard.git(root, "fetch", "--quiet", "origin", base)
    target_head = guard.git(root, "rev-parse", "HEAD")
    base_sha = guard.git(root, "rev-parse", f"refs/remotes/origin/{base}")
    if target_head != base_sha:
        fail(f"target must start at exact fetched origin/{base} ({base_sha}); current HEAD is {target_head}")
    guard.verify_publishable_base(root, branch, base, base_sha)
    return branch, target_head


def _blob(root: Path, revision: str, path: str) -> bytes | None:
    result = subprocess.run(["git", "-C", str(root), "show", f"{revision}:{path}"],
                            capture_output=True, timeout=15)
    if result.returncode:
        if "does not exist" in result.stderr.decode(errors="replace") or "exists on disk" in result.stderr.decode(errors="replace"):
            return None
        if "Path '" in result.stderr.decode(errors="replace") and "not in" in result.stderr.decode(errors="replace"):
            return None
        fail(f"could not read tracked source blob {path} at {revision}")
    return result.stdout


def _mode(root: Path, revision: str, path: str) -> str | None:
    result = subprocess.run(["git", "-C", str(root), "ls-tree", revision, "--", path],
                            capture_output=True, text=True, timeout=15)
    if result.returncode:
        fail(f"could not inspect file mode for {path}")
    if not result.stdout.strip():
        return None
    return result.stdout.split(" ", 1)[0]


def merge_scoped_files(source: Path, source_start: str, target: Path,
                       target_head: str, paths: list[str]) -> dict[str, tuple[bytes | None, str | None]]:
    """Three-way merge the exact task paths, refusing textual conflicts."""
    merged: dict[str, tuple[bytes | None, str | None]] = {}
    with tempfile.TemporaryDirectory(prefix="claritylink-legacy-merge-") as temp:
        temp_root = Path(temp)
        for index, path in enumerate(paths):
            base = _blob(source, source_start, path)
            target_bytes = _blob(target, target_head, path)
            source_file = source / path
            source_bytes = source_file.read_bytes() if source_file.is_file() and not source_file.is_symlink() else None
            if source_file.is_symlink():
                fail(f"legacy source path became a symlink: {path}")
            if source_bytes is None and base is None:
                fail(f"reserved source path is neither tracked nor present: {path}")
            for candidate in (base, target_bytes, source_bytes):
                if candidate is not None and b"\0" in candidate:
                    fail(f"binary content cannot be reconstructed automatically: {path}")
            if base is None:
                if target_bytes is not None and source_bytes != target_bytes:
                    fail(f"both source and target added different content at {path}")
                merged_bytes = source_bytes
            elif source_bytes is None:
                if target_bytes != base:
                    fail(f"source deletion overlaps target edits at {path}")
                merged_bytes = None
            elif target_bytes is None:
                if source_bytes != base:
                    fail(f"target deletion overlaps source edits at {path}")
                merged_bytes = None
            elif source_bytes == base:
                merged_bytes = target_bytes
            elif target_bytes == base or source_bytes == target_bytes:
                merged_bytes = source_bytes
            else:
                base_file = temp_root / f"{index}.base"
                target_file = temp_root / f"{index}.target"
                source_file_copy = temp_root / f"{index}.source"
                base_file.write_bytes(base)
                target_file.write_bytes(target_bytes)
                source_file_copy.write_bytes(source_bytes)
                result = subprocess.run(["git", "merge-file", "-p", str(target_file),
                                         str(base_file), str(source_file_copy)],
                                        capture_output=True, timeout=15)
                if result.returncode:
                    fail(f"source and target overlap requires semantic conflict resolution at {path}")
                merged_bytes = result.stdout
            base_mode = _mode(source, source_start, path)
            target_mode = _mode(target, target_head, path)
            source_mode = ("100755" if os.stat(source / path).st_mode & 0o111 else "100644") \
                if source_bytes is not None else None
            if (base_mode and target_mode and source_mode and
                    target_mode != base_mode and source_mode != base_mode and target_mode != source_mode):
                fail(f"source and target changed executable mode differently at {path}")
            merged_mode = source_mode if target_mode == base_mode else target_mode
            if merged_bytes != target_bytes or merged_mode != target_mode:
                merged[path] = (merged_bytes, merged_mode)
    return merged


def apply_merged_files(root: Path, merged: dict[str, tuple[bytes | None, str | None]]) -> None:
    for path, (content, mode) in merged.items():
        guard.validate_paths(root, [path])
        destination = root / path
        if destination.is_symlink():
            fail(f"target path became a symlink: {path}")
        if content is None:
            destination.unlink(missing_ok=True)
        else:
            destination.parent.mkdir(parents=True, exist_ok=True)
            temp = destination.with_name(destination.name + f".recovery-{os.getpid()}.tmp")
            if temp.exists() or temp.is_symlink():
                fail(f"recovery temp path already exists for {path}")
            fd = os.open(temp, os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0), 0o600)
            try:
                with os.fdopen(fd, "wb") as stream:
                    stream.write(content)
                    stream.flush()
                    os.fsync(stream.fileno())
                if mode:
                    os.chmod(temp, 0o755 if mode == "100755" else 0o644)
                os.replace(temp, destination)
                parent_fd = os.open(destination.parent, os.O_RDONLY)
                try:
                    os.fsync(parent_fd)
                finally:
                    os.close(parent_fd)
            finally:
                temp.unlink(missing_ok=True)
    if merged:
        result = subprocess.run(["git", "-C", str(root), "add", "-A", "--", *merged.keys()],
                                capture_output=True, text=True, timeout=30)
        if result.returncode:
            fail("could not stage the validated recovered paths")


def verify_resumable_target(root: Path, target_head: str,
                            merged: dict[str, tuple[bytes | None, str | None]],
                            scope: list[str]) -> None:
    changed = guard.changed_paths(root)
    if changed - set(scope):
        fail("target changed outside the recovered scope during an interrupted application")
    untracked = subprocess.run(["git", "-C", str(root), "ls-files", "--others", "--exclude-standard", "-z"],
                               capture_output=True, timeout=10)
    if untracked.returncode or untracked.stdout:
        fail("target has untracked files during interrupted recovery")
    for path in scope:
        file = root / path
        if file.is_symlink():
            fail(f"target path became a symlink during recovery: {path}")
        current = file.read_bytes() if file.is_file() else None
        current_mode = ("100755" if file.stat().st_mode & 0o111 else "100644") if file.is_file() else None
        expected_current = _blob(root, target_head, path)
        expected_current_mode = _mode(root, target_head, path)
        expected_merged = merged.get(path, (expected_current, expected_current_mode))
        current_state = (current, current_mode)
        if current_state not in {(expected_current, expected_current_mode), expected_merged}:
            fail(f"target content or mode is neither the prepared base nor recovery output at {path}")


def run_probe(repo: Path, target_head: str, merged: dict[str, tuple[bytes | None, str | None]]) -> str:
    """Verify the reconstructed merge tree in a disposable private clone."""
    with tempfile.TemporaryDirectory(prefix="claritylink-recovery-probe-") as temp:
        probe = Path(temp) / "repo"
        clone = subprocess.run(["git", "clone", "--quiet", "--shared", "--no-hardlinks",
                                "--no-checkout", str(repo), str(probe)],
                              capture_output=True, text=True, timeout=60)
        if clone.returncode:
            fail("could not create isolated recovery conflict probe")
        checkout = subprocess.run(["git", "-C", str(probe), "checkout", "--quiet", "--detach", target_head],
                                  capture_output=True, text=True, timeout=30)
        if checkout.returncode:
            fail("could not check out verified recovery target for conflict probe")
        apply_merged_files(probe, merged)
        changed = guard.changed_paths(probe)
        if changed - set(guard.git(probe, "diff", "--cached", "--name-only").splitlines()):
            fail("recovery conflict probe produced untracked or unstaged paths")
        return guard.git(probe, "write-tree")


def prepare(source: Path, target: Path, task: str, base: str) -> dict:
    source = Path(guard.git(source, "rev-parse", "--show-toplevel")).resolve()
    target = Path(guard.git(target, "rev-parse", "--show-toplevel")).resolve()
    source_manifest, source_locks, source_data, source_head, source_tree, patch, paths = verify_source(source)
    target_branch, target_head = verify_target(target, base)
    if source.resolve() == target.resolve():
        fail("source and target must be distinct worktrees")
    if task == source_data["task_id"]:
        fail("recovery task must have a new task identity")
    if not patch:
        fail("legacy task has no source delta to recover")
    source_base = source_data["starting_sha"]
    if subprocess.run(["git", "-C", str(target), "merge-base", "--is-ancestor", source_base, target_head],
                      capture_output=True).returncode:
        fail("recorded source start is not an ancestor of the proposed target")
    merged = merge_scoped_files(source, source_data["starting_sha"], target,
                                target_head, source_data["files"])
    applied_tree = run_probe(source, target_head, merged)
    store = private_store(target)
    transaction_id = str(uuid.uuid4())
    transaction = store / transaction_id
    transaction.mkdir(mode=0o700)
    os.chmod(transaction, 0o700)
    patch_path = transaction / "source.patch"
    private_write(patch_path, patch, exclusive=True)
    receipt = {
        "schema": 1, "transaction_id": transaction_id,
        "source_task_id": source_data["task_id"], "source_branch": source_data["branch"],
        "source_worktree": str(source), "source_manifest": str(source_manifest),
        "source_manifest_sha256": sha256_bytes(source_manifest.read_bytes()),
        "source_starting_sha": source_data["starting_sha"], "source_head": source_head,
        "source_tree": source_tree, "source_scope": source_data["files"],
        "source_paths": sorted(paths), "source_patch_sha256": sha256_bytes(patch),
        "merged_path_hashes": {path: (sha256_bytes(content) if content is not None else None)
                               for path, (content, _mode_value) in merged.items()},
        "target_task_id": task, "target_branch": target_branch,
        "target_worktree": str(target), "target_base": base, "target_starting_sha": target_head,
        "target_applied_tree": applied_tree,
        "target_pr": None, "prepared_at": int(time.time()),
        "overlap_paths": sorted(set(paths) & set(guard.git(
            target, "diff", "--name-only", source_base, target_head).splitlines())),
    }
    receipt_path = transaction / "receipt.json"
    receipt_bytes = (json.dumps(receipt, sort_keys=True, indent=2) + "\n").encode()
    private_write(receipt_path, receipt_bytes, exclusive=True)
    os.chmod(receipt_path, 0o400)
    private_write(transaction / "state.json",
                  (json.dumps({"state": "PREPARED", "authorization": None,
                               "receipt_sha256": sha256_bytes(receipt_bytes)},
                              sort_keys=True, indent=2) + "\n").encode(), exclusive=True)
    return {"result": "RECOVERY_PREPARED", "transaction_id": transaction_id,
            "source_task_id": source_data["task_id"], "target_task_id": task,
            "target_branch": target_branch, "target_head": target_head,
            "paths": receipt["source_paths"], "overlap_paths": receipt["overlap_paths"],
            "owner_authorization": authorization_statement(receipt, sha256_bytes(receipt_bytes)),
            "receipt": str(receipt_path)}


def _commit_locked(root: Path, transaction_id: str, owner_authorization: str) -> dict:
    root = Path(guard.git(root, "rev-parse", "--show-toplevel")).resolve()
    store = private_store(root)
    raw_transaction = store / transaction_id
    if raw_transaction.is_symlink():
        fail("recovery transaction directory is a symlink")
    transaction = raw_transaction.resolve()
    if transaction.parent != store.resolve() or not transaction.is_dir():
        fail("recovery transaction must be a directory directly inside the private store")
    transaction_stat = transaction.stat()
    if transaction_stat.st_uid != os.geteuid() or transaction_stat.st_mode & 0o077:
        fail("recovery transaction directory must be private and owned by this user")
    receipt_path = transaction / "receipt.json"
    receipt = read_json(receipt_path)
    state_path = transaction / "state.json"
    state = read_json(state_path)
    if sha256_bytes(receipt_path.read_bytes()) != state.get("receipt_sha256"):
        fail("immutable recovery provenance receipt hash differs from its recorded state")
    if receipt.get("transaction_id") != transaction_id:
        fail("recovery receipt transaction ID differs from the requested transaction")
    expected = authorization_statement(receipt, state.get("receipt_sha256", ""))
    if owner_authorization != expected:
        fail("owner authorization missing; provide the exact transfer statement for this transaction")
    if state.get("state") not in {"PREPARED", "TRANSFER_IN_PROGRESS", "TRANSFERRED"}:
        fail("legacy recovery transaction is not in a resumable state")
    target = Path(receipt["target_worktree"])
    source = Path(receipt["source_worktree"])
    if root != target:
        fail("commit must run from the exact target worktree recorded in the preparation receipt")
    if guard.branch_and_owner(target) != receipt["target_branch"]:
        fail("recovery target branch ownership changed after preparation")
    if (state.get("state") != "TRANSFERRED" and
            guard.git(target, "rev-parse", "HEAD") != receipt["target_starting_sha"]):
        fail("recovery target starting SHA changed after preparation")
    if state.get("state") == "TRANSFERRED":
        target_manifest, lock_dir = guard.layout(target)
        manifest_data = json.loads(target_manifest.read_text()) if target_manifest.is_file() else {}
        if manifest_data.get("recovered_from", {}).get("transaction_id") != transaction_id:
            fail("transferred task manifest is missing or belongs to another transaction")
        with guard.scope_transaction(lock_dir):
            for path in receipt["source_scope"]:
                lock = lock_dir / guard.path_key(path)
                owner = json.loads(lock.read_text()) if lock.is_file() else {}
                if (owner.get("task_id") != receipt["target_task_id"] or
                        owner.get("branch") != receipt["target_branch"] or
                        owner.get("worktree") != receipt["target_worktree"] or
                        owner.get("path") != path):
                    fail(f"transferred reservation is not owned by the target for {path}")
        return {"result": "RECOVERY_TRANSFERRED", "transaction_id": transaction_id,
                "target_task_id": receipt["target_task_id"], "target_branch": receipt["target_branch"],
                "paths": receipt["source_scope"], "target_worktree": str(target), "idempotent": True}
    guard.canonical_origin(target)
    guard.git(target, "fetch", "--quiet", "origin", receipt["target_base"])
    if guard.git(target, "rev-parse", f"refs/remotes/origin/{receipt['target_base']}") != receipt["target_starting_sha"]:
        fail("recovery target base advanced after preparation; preserve it and prepare from the new base")
    guard.verify_publishable_base(target, receipt["target_branch"], receipt["target_base"],
                                  receipt["target_starting_sha"])
    source_manifest, source_locks, source_data, source_head, source_tree, patch, _ = verify_source(
        source, verify_locks=state.get("state") == "PREPARED")
    source_manifest_hash = sha256_bytes(source_manifest.read_bytes())
    transferred = source_data.get("transferred_to")
    already_transferred = (source_data.get("transfer_status") == "TRANSFERRED" and
                           isinstance(transferred, dict) and
                           transferred.get("transaction_id") == transaction_id and
                           transferred.get("task_id") == receipt["target_task_id"] and
                           transferred.get("branch") == receipt["target_branch"])
    if (source_data["task_id"] != receipt["source_task_id"] or
            (source_manifest_hash != receipt["source_manifest_sha256"] and not already_transferred) or
            source_head != receipt["source_head"] or source_tree != receipt["source_tree"] or
            sha256_bytes(patch) != receipt["source_patch_sha256"]):
        fail("legacy source changed after preparation; preserve both worktrees and re-prepare")
    merged = merge_scoped_files(source, receipt["source_starting_sha"], target,
                                receipt["target_starting_sha"], receipt["source_scope"])
    merged_hashes = {path: (sha256_bytes(content) if content is not None else None)
                     for path, (content, _mode_value) in merged.items()}
    if merged_hashes != receipt["merged_path_hashes"]:
        fail("reconstructed target delta differs from the immutable preparation receipt")
    if state.get("state") == "PREPARED":
        patch_path = transaction / "source.patch"
        if sha256_bytes(patch_path.read_bytes()) != receipt["source_patch_sha256"]:
            fail("private source patch hash differs from the prepared receipt")
        if guard.porcelain(target):
            verify_resumable_target(target, receipt["target_starting_sha"], merged,
                                    receipt["source_scope"])
        apply_merged_files(target, merged)
        state["state"] = "TRANSFER_IN_PROGRESS"
        state["authorization"] = {"statement_sha256": sha256_bytes(owner_authorization.encode()),
                                   "authorized_at": int(time.time())}
        if guard.git(target, "write-tree") != receipt["target_applied_tree"]:
            fail("applied recovery tree differs from the isolated conflict probe")
        state["applied_target_tree"] = receipt["target_applied_tree"]
        private_update_json(state_path, state)

    if guard.git(target, "write-tree") != receipt["target_applied_tree"]:
        fail("target has an unexpected staged tree; preserve it and resume only after investigation")
    if guard.git(target, "diff", "--name-only"):
        fail("target has unstaged edits after recovery patch application")
    target_changes = guard.changed_paths(target)
    if target_changes - set(receipt["source_scope"]):
        fail("recovery target contains changes outside the transferred scope")
    untracked = subprocess.run(["git", "-C", str(target), "ls-files", "--others", "--exclude-standard", "-z"],
                               capture_output=True, timeout=10)
    if untracked.returncode or untracked.stdout:
        fail("recovery target contains untracked files")

    target_manifest, target_locks = guard.layout(target)
    owner = {"task_id": receipt["target_task_id"], "branch": receipt["target_branch"],
             "worktree": str(target), "started_at": int(time.time())}
    target_data = {**owner, "starting_sha": receipt["target_starting_sha"],
                   "base": receipt["target_base"], "files": receipt["source_scope"],
                   "recovered_from": {"transaction_id": transaction_id,
                                      "task_id": receipt["source_task_id"],
                                      "branch": receipt["source_branch"],
                                      "starting_sha": receipt["source_starting_sha"],
                                      "head": receipt["source_head"],
                                      "manifest": receipt["source_manifest"]}}
    lock_dir = target_locks
    with manifest_locks(target, source):
        with guard.scope_transaction(lock_dir):
            _source_manifest, _source_locks, latest_source, latest_head, latest_tree, latest_patch, _ = verify_source(
                source, verify_locks=False)
            latest_hash = sha256_bytes(_source_manifest.read_bytes())
            latest_transfer = latest_source.get("transferred_to")
            latest_transferred = (latest_source.get("transfer_status") == "TRANSFERRED" and
                                  isinstance(latest_transfer, dict) and
                                  latest_transfer.get("transaction_id") == transaction_id and
                                  latest_transfer.get("task_id") == receipt["target_task_id"] and
                                  latest_transfer.get("branch") == receipt["target_branch"])
            if (latest_source["task_id"] != receipt["source_task_id"] or
                    (latest_hash != receipt["source_manifest_sha256"] and not latest_transferred) or
                    latest_head != receipt["source_head"] or latest_tree != receipt["source_tree"] or
                    sha256_bytes(latest_patch) != receipt["source_patch_sha256"]):
                fail("legacy source changed while transferring; preserve the partial transaction")
            if target_manifest.exists():
                existing = json.loads(target_manifest.read_text())
                if existing.get("task_id") != receipt["target_task_id"]:
                    fail("another task manifest appeared in the target; reservation transfer stopped")
                if existing.get("recovered_from", {}).get("transaction_id") != transaction_id:
                    fail("target manifest is not owned by this recovery transaction")
                target_data = existing
            else:
                guard.atomic_manifest_write(target_manifest, target_data)
            source_manifest, source_locks, source_data = manifest_for(source)
            source_data = json.loads(source_manifest.read_text())
            for path in source_data["files"]:
                lock = lock_dir / guard.path_key(path)
                if not lock.is_file():
                    fail(f"source reservation missing during transfer for {path}")
                reservation = json.loads(lock.read_text())
                source_owner = {"task_id": receipt["source_task_id"],
                                "branch": receipt["source_branch"],
                                "worktree": receipt["source_worktree"],
                                "started_at": source_data["started_at"], "path": path}
                target_owner = {"task_id": receipt["target_task_id"],
                                "branch": receipt["target_branch"],
                                "worktree": receipt["target_worktree"],
                                "started_at": target_data["started_at"], "path": path}
                if reservation == source_owner:
                    guard.atomic_manifest_write(lock, target_owner)
                elif reservation != target_owner:
                    fail(f"reservation ownership changed during transfer for {path}")
            source_data["transfer_status"] = "TRANSFERRED"
            source_data["transferred_to"] = {"transaction_id": transaction_id,
                                                "task_id": receipt["target_task_id"],
                                                "branch": receipt["target_branch"]}
            guard.atomic_manifest_write(source_manifest, source_data)
            state["state"] = "TRANSFERRED"
            state["transferred_at"] = int(time.time())
            private_update_json(state_path, state)
    return {"result": "RECOVERY_TRANSFERRED", "transaction_id": transaction_id,
            "target_task_id": receipt["target_task_id"], "target_branch": receipt["target_branch"],
            "paths": receipt["source_scope"], "target_worktree": str(target)}


def commit(root: Path, transaction_id: str, owner_authorization: str) -> dict:
    try:
        if str(uuid.UUID(transaction_id)) != transaction_id:
            raise ValueError("non-canonical transaction id")
    except (ValueError, AttributeError) as exc:
        raise guard.GuardError("invalid recovery transaction ID") from exc
    root = Path(guard.git(root, "rev-parse", "--show-toplevel")).resolve()
    with recovery_lock(private_store(root)):
        return _commit_locked(root, transaction_id, owner_authorization)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    prep = commands.add_parser("prepare")
    prep.add_argument("--source-worktree", type=Path, required=True)
    prep.add_argument("--target-worktree", type=Path, required=True)
    prep.add_argument("--target-task", required=True)
    prep.add_argument("--base", required=True)
    transfer = commands.add_parser("commit")
    transfer.add_argument("--repo", type=Path, default=Path.cwd())
    transfer.add_argument("--transaction", required=True)
    transfer.add_argument("--owner-authorization", required=True)
    args = parser.parse_args()
    try:
        if args.command == "prepare":
            result = prepare(args.source_worktree, args.target_worktree, args.target_task, args.base)
        else:
            result = commit(args.repo, args.transaction, args.owner_authorization)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (guard.GuardError, OSError, subprocess.SubprocessError, ValueError) as exc:
        print(json.dumps({"result": "BLOCKED", "reason": str(exc)}, sort_keys=True), file=sys.stderr)
        return 2


if __name__ == "__main__":
    sys.exit(main())
