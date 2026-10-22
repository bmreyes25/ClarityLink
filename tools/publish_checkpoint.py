#!/usr/bin/env python3
"""Explicit-scope, safety-gated GitHub checkpoint publisher for ClarityLink."""
from __future__ import annotations

import argparse
import re
import subprocess
import sys
import time
from pathlib import Path

REPO = "bmreyes25/ClarityLink"
REMOTE = "https://github.com/bmreyes25/ClarityLink.git"
FORBIDDEN_SUFFIXES = {".apk", ".dex", ".odex", ".so", ".img", ".bin", ".tar", ".gz", ".zip", ".pcap", ".pcapng", ".dump", ".raw", ".keystore", ".jks", ".p12", ".pem", ".key", ".mp4", ".mov"}
RESTRICTED_PATH_PARTS = {"captures", "private-captures", "acquisition", "extracted", "decompiled", "decompiled-clean", "deodexed", "firmware", "vendor-dumps", "raw-evidence", "evidence"}
SHARED_STATUS_PATHS = {"NEXT_ACTION.md", "docs/status/current.md", "docs/status/milestones.json", "docs/status/blockers.md", "docs/status/capabilities.md"}
SECRET_PATTERNS = [re.compile(x, re.I) for x in (
    r"gh[pousr]_[A-Za-z0-9_]{20,}", r"github_pat_[A-Za-z0-9_]{20,}",
    r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----", r"AKIA[0-9A-Z]{16}",
    r"(?:password|passwd|secret|token)\s*[:=]\s*['\"]?[^\s'\"]{8,}",
)]


class Failure(RuntimeError):
    pass


class UnsafeContent(Failure):
    pass


class PushRejected(Failure):
    pass


class AuthenticationFailure(Failure):
    pass


def git(root: Path, *args: str, check: bool = True, timeout: int = 30) -> str:
    p = subprocess.run(["git", "-C", str(root), *args], text=True, capture_output=True, timeout=timeout)
    if check and p.returncode:
        raise Failure((p.stderr or p.stdout).strip() or f"git {args[0]} failed")
    return p.stdout.strip()


def safe_scope(root: Path, files: list[str]) -> list[str]:
    if not files:
        raise Failure("at least one explicit --file is required; repository-wide staging is disabled")
    normalized = []
    for value in files:
        path = Path(value)
        if path.is_absolute() or ".." in path.parts or not value.strip() or value.startswith(":") or any(char in value for char in "*?[]"):
            raise Failure(f"invalid scoped path: {value}")
        full = (root / path).resolve()
        if root.resolve() not in full.parents:
            raise Failure(f"path escapes repository: {value}")
        tracked_missing = subprocess.run(["git", "-C", str(root), "ls-files", "--error-unmatch", "--", value], capture_output=True).returncode == 0
        if not full.exists() and not tracked_missing:
            raise Failure(f"scoped file does not exist: {value}")
        if full.exists() and full.is_dir():
            raise Failure(f"directories are not accepted; enumerate files explicitly: {value}")
        if full.suffix.lower() in FORBIDDEN_SUFFIXES or any(part.lower() in RESTRICTED_PATH_PARTS for part in path.parts):
            raise UnsafeContent(f"blocked artifact or restricted path: {value}")
        ignored = subprocess.run(["git", "-C", str(root), "check-ignore", "-q", "--", value]).returncode == 0
        if ignored:
            raise UnsafeContent(f"scoped file is ignored by Git: {value}")
        normalized.append(path.as_posix())
    if len(set(normalized)) != len(normalized):
        raise Failure("duplicate scoped paths are not allowed")
    return normalized


def scan_staged(root: Path) -> None:
    names = git(root, "diff", "--cached", "--name-only").splitlines()
    deleted = set(git(root, "diff", "--cached", "--diff-filter=D", "--name-only").splitlines())
    if not names:
        raise Failure("no staged changes")
    for name in names:
        if Path(name).suffix.lower() in FORBIDDEN_SUFFIXES:
            raise UnsafeContent(f"blocked binary or sensitive artifact: {name}")
        if any(part.lower() in RESTRICTED_PATH_PARTS for part in Path(name).parts):
            raise UnsafeContent(f"restricted path blocked: {name}")
        if name in deleted:
            continue
        blob = subprocess.run(["git", "-C", str(root), "show", f":{name}"], capture_output=True)
        if blob.returncode:
            raise Failure(f"cannot inspect staged content: {name}")
        if b"\0" in blob.stdout:
            raise UnsafeContent(f"binary content is blocked by default: {name}")
        content = blob.stdout.decode("utf-8", "replace")
        if any(rx.search(content) for rx in SECRET_PATTERNS):
            raise UnsafeContent(f"credential-like content blocked: {name}")


def split_pr_message(message: str) -> tuple[str, str]:
    """A PR title is one short line; everything else belongs in the body."""
    lines = message.strip().splitlines() or [""]
    title = lines[0].strip()[:100]
    if not title:
        raise Failure("commit message needs a non-empty first line to use as the PR title")
    return title, "\n".join(lines[1:]).strip()


def run_public_safety_gate(root: Path) -> None:
    """Run the CI public-safety gate on the staged content. Its absence is allowed only in a
    checkout that predates it; where it exists it is mandatory."""
    gate = root / "tools" / "check_public_safety.py"
    if not gate.is_file():
        return
    p = subprocess.run([sys.executable, str(gate), "--root", str(root), "--staged"], text=True, capture_output=True)
    if p.returncode:
        raise UnsafeContent("public-safety gate failed:\n" + (p.stdout + p.stderr).strip())


def ensure_branch(root: Path, intended: str) -> str:
    check = subprocess.run(["git", "-C", str(root), "check-ref-format", "--branch", intended], capture_output=True, text=True)
    if check.returncode:
        raise Failure(f"invalid feature branch name: {intended}")
    current = git(root, "branch", "--show-current", check=False)
    if not current:
        if intended == "main" or intended.startswith("main/"):
            raise Failure("protected main cannot be used as a checkpoint branch")
        git(root, "switch", "-c", intended)
        return intended
    if current != intended:
        raise Failure(f"current branch {current} differs from requested branch {intended}; refusing branch switching")
    return current


def live_remote_branch_sha(root: Path, branch: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(root), "ls-remote", "--heads", "origin", f"refs/heads/{branch}"],
        text=True, capture_output=True, timeout=30,
    )
    if result.returncode:
        detail = (result.stderr or result.stdout).strip()
        raise Failure(f"could not verify live origin/{branch}; refusing publication: {detail}")
    lines = result.stdout.strip().splitlines()
    if not lines:
        return ""
    return lines[0].split()[0]


def fetch_parent_pr(number: int) -> dict:
    """Read the parent PR live. Nothing about the parent is taken from local state."""
    import json
    p = subprocess.run(
        ["gh", "pr", "view", str(number), "-R", REPO, "--json",
         "number,state,baseRefName,headRefName,headRefOid,isCrossRepository,mergeStateStatus,commits"],
        text=True, capture_output=True, timeout=60)
    if p.returncode:
        raise Failure(f"could not read parent PR #{number}: {(p.stderr or p.stdout).strip()}")
    data = json.loads(p.stdout)
    data["commit_oids"] = [c["oid"] for c in data.get("commits", [])]
    return data


def validate_stack_parent(root: Path, parent: dict, *, live_parent_sha: str, main_sha: str, head: str) -> str:
    """Return the verified parent head SHA, or raise. Stacking is allowed only on an exact, open,
    reviewable parent so a stacked branch can never smuggle in history that no PR shows."""
    if parent.get("state") != "OPEN":
        raise Failure(f"parent PR #{parent.get('number')} is {parent.get('state')}, not OPEN")
    if parent.get("isCrossRepository"):
        raise Failure("parent PR comes from a fork; refusing to stack on it")
    if parent.get("baseRefName") != "main":
        raise Failure("stacking is limited to one level: the parent PR must be based on main")
    if parent.get("mergeStateStatus") == "DIRTY":
        raise Failure("parent PR has merge conflicts with its base; resolve it before stacking")
    parent_sha = parent.get("headRefOid", "")
    if not parent_sha or live_parent_sha != parent_sha:
        raise Failure(f"parent branch live SHA {live_parent_sha or 'missing'} differs from the PR head {parent_sha or 'missing'}")
    if subprocess.run(["git", "-C", str(root), "cat-file", "-e", f"{parent_sha}^{{commit}}"], capture_output=True).returncode:
        raise Failure("parent head commit is not present locally; fetch the parent branch first")
    if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", main_sha, parent_sha], capture_output=True).returncode:
        raise Failure("parent head does not descend from the fetched origin/main; it must be brought up to date first")
    local = git(root, "rev-list", "--reverse", f"{main_sha}..{parent_sha}").split()
    if local != parent.get("commit_oids"):
        raise Failure("commits between origin/main and the parent head differ from the commits the parent PR shows; "
                      "refusing to import history that is not reviewed there")
    if head != parent_sha:
        raise Failure("a stacked checkpoint branch must start exactly at the parent PR head")
    return parent_sha


def ensure_no_unpublished_history(root: Path, branch: str, stack_parent: dict | None = None) -> str | None:
    """Refuse to push commits other than the scoped checkpoint created below. Returns the
    verified parent head when the branch is stacked."""
    git(root, "fetch", "--quiet", "origin", "main", timeout=60)
    remote_sha = live_remote_branch_sha(root, branch)
    head = git(root, "rev-parse", "HEAD")
    if remote_sha:
        if head != remote_sha:
            raise Failure(
                f"branch has unpublished commits or is not synchronized with origin/{branch}; "
                "publish only from a clean checkpoint branch"
            )
        if stack_parent is not None:
            parent_sha = stack_parent.get("headRefOid", "")
            live = live_remote_branch_sha(root, stack_parent.get("headRefName", ""))
            if live != parent_sha:
                raise Failure("parent branch moved since this stack was created; rebase the stack deliberately")
            if subprocess.run(["git", "-C", str(root), "merge-base", "--is-ancestor", parent_sha, head], capture_output=True).returncode:
                raise Failure("this branch no longer contains the parent PR head")
            return parent_sha
        return None
    main = git(root, "rev-parse", "refs/remotes/origin/main", check=False)
    if main and head == main:
        return None
    if stack_parent is not None:
        live = live_remote_branch_sha(root, stack_parent.get("headRefName", ""))
        return validate_stack_parent(root, stack_parent, live_parent_sha=live, main_sha=main, head=head)
    raise Failure(
        "new checkpoint branches must start exactly at the fetched origin/main; "
        "unpublished historical commits are blocked (use --stack-parent-pr N to stack on an open parent PR)"
    )


def reject_staged_outside_scope(root: Path, scope: list[str]) -> None:
    staged = set(git(root, "diff", "--cached", "--name-only").splitlines())
    outside = sorted(staged - set(scope))
    if outside:
        raise Failure("unrelated files were already staged; preserve them and publish only after resolving the index: " + ", ".join(outside))


def publish(args: argparse.Namespace) -> dict:
    root = Path(git(args.repo, "rev-parse", "--show-toplevel")).resolve()
    if git(root, "remote", "get-url", "origin") not in (REMOTE, "git@github.com:bmreyes25/ClarityLink.git", "ssh://git@github.com/bmreyes25/ClarityLink.git"):
        raise Failure("origin does not identify the canonical GitHub repository")
    branch = ensure_branch(root, args.branch)
    if branch == "main" or branch.startswith("main/"):
        raise Failure("direct publication to protected main is forbidden")
    stack_parent = fetch_parent_pr(args.stack_parent_pr) if getattr(args, "stack_parent_pr", None) else None
    stacked_on = (ensure_no_unpublished_history(root, branch, stack_parent) if stack_parent
                  else ensure_no_unpublished_history(root, branch))
    if args.verification == "VERIFIED" and not args.verify_command:
        raise Failure("VERIFIED requires an explicit --verify-command")
    scope = safe_scope(root, args.file)
    shared = set(scope) & SHARED_STATUS_PATHS
    shared |= {path for path in scope if path.startswith("docs/status/")}
    if shared and not args.maintenance_owner:
        raise Failure("shared roadmap/status files require the designated maintenance workflow: " + ", ".join(sorted(shared)))
    if not args.public_safe_reviewed:
        raise Failure("publication requires --public-safe-reviewed after reviewing the exact explicit scope")
    dirty = git(root, "status", "--porcelain", "--", *scope)
    if not dirty:
        raise Failure("explicit scope has no changes")
    reject_staged_outside_scope(root, scope)
    git(root, "add", "--", *scope)
    staged = set(git(root, "diff", "--cached", "--name-only").splitlines())
    if staged - set(scope):
        raise Failure("staging changed paths outside explicit scope")
    scan_staged(root)
    run_public_safety_gate(root)
    git(root, "diff", "--cached", "--check")
    if args.verify_command:
        p = subprocess.run(args.verify_command, cwd=root, shell=True, text=True)
        if p.returncode and args.verification == "VERIFIED":
            raise Failure(f"verification command failed with exit {p.returncode}")
        if p.returncode:
            print(f"WIP verification command failed with exit {p.returncode}; preserving status honestly", file=sys.stderr)
    if args.verification == "WIP_UNVERIFIED" and not args.wip_notes:
        raise Failure("WIP_UNVERIFIED requires --wip-notes describing incomplete work and known failing checks")
    commit_title = ("WIP_UNVERIFIED: " if args.verification == "WIP_UNVERIFIED" else "") + args.message
    commit_body = f"Task: {args.task}\nVerification level: {args.verification}"
    if stacked_on:
        commit_body += f"\nStacked-On: PR #{args.stack_parent_pr} at {stacked_on}"
    if args.verification == "WIP_UNVERIFIED":
        commit_body += f"\nIncomplete work / known failures: {args.wip_notes}"
    elif args.verify_command:
        commit_body += f"\nVerification command: {args.verify_command}"
    git(root, "commit", "-m", commit_title, "-m", commit_body)
    local_sha = git(root, "rev-parse", "HEAD")
    for attempt in range(3):
        p = subprocess.run(["git", "-C", str(root), "push", "--set-upstream", "origin", f"HEAD:refs/heads/{branch}"], text=True, capture_output=True)
        if not p.returncode:
            break
        reason = (p.stderr or p.stdout).strip()
        if "authentication failed" in reason.lower() or "permission denied" in reason.lower():
            raise AuthenticationFailure(f"GitHub authentication/authorization failed; local commit {local_sha} preserved: {reason}")
        if any(word in reason.lower() for word in ("protected branch", "non-fast-forward", "rejected")):
            raise PushRejected(f"push rejected; local commit {local_sha} preserved: {reason}")
        if attempt == 2:
            raise PushRejected(f"push failed after 3 attempts; local commit {local_sha} preserved: {reason}")
        time.sleep(attempt + 1)
    remote_sha = git(root, "ls-remote", "--heads", "origin", f"refs/heads/{branch}").split()[0]
    if remote_sha != local_sha:
        raise Failure(f"REMOTE_SHA_MISMATCH local={local_sha} remote={remote_sha}")
    pr_url = None
    pr_number = args.pr
    if not pr_number:
        existing = subprocess.run(["gh", "pr", "list", "-R", REPO, "--head", branch, "--state", "open", "--json", "number,url"], text=True, capture_output=True)
        if existing.returncode == 0:
            import json
            rows = json.loads(existing.stdout)
            if rows:
                pr_number = rows[0]["number"]
                pr_url = rows[0]["url"]
    if pr_number:
        info = subprocess.run(["gh", "pr", "view", str(pr_number), "-R", REPO, "--json", "headRefName,url"], text=True, capture_output=True)
        if info.returncode:
            raise Failure(f"could not verify existing PR #{pr_number}: {info.stderr.strip()}")
        import json
        data = json.loads(info.stdout)
        if data.get("headRefName") != branch:
            raise Failure("existing PR head does not match this feature branch")
        pr_url = data["url"]
    elif args.verification == "VERIFIED":
        title, details = split_pr_message(args.message)
        base = stack_parent["headRefName"] if stack_parent else "main"
        body = f"Task: {args.task}\n\nVerification: VERIFIED.\nRemote SHA verified: {remote_sha}."
        if stack_parent:
            body += f"\nStacked on PR #{args.stack_parent_pr} at {stacked_on}; base is that PR's branch."
        if details:
            body += "\n\n" + details
        p = subprocess.run(["gh", "pr", "create", "-R", REPO, "--base", base, "--head", branch,
                            "--title", title, "--body", body],
                           text=True, capture_output=True)
        if p.returncode:
            raise Failure(f"push verified, but PR creation failed: {p.stderr.strip()}")
        pr_url = p.stdout.strip().splitlines()[-1]
    if pr_url:
        check = subprocess.run(["gh", "pr", "view", pr_url, "-R", REPO, "--json", "headRefName,url"], text=True, capture_output=True)
        if check.returncode:
            raise Failure(f"branch push verified, but PR reference check failed: {check.stderr.strip()}")
        import json
        pr_data = json.loads(check.stdout)
        if pr_data.get("headRefName") != branch:
            raise Failure("PR does not reference the published feature branch")
        pr_url = pr_data["url"]
    result = subprocess.run([sys.executable, str(root / "tools/verify_remote_publication.py"), "--repo", str(root), "--branch", branch], text=True, capture_output=True)
    if result.returncode:
        raise Failure(f"post-publication verification failed: {result.stdout.strip()} {result.stderr.strip()}")
    print(f"REMOTE_VERIFIED task={args.task} branch={branch} local_sha={local_sha} remote_sha={remote_sha}")
    print(f"commit=https://github.com/{REPO}/commit/{remote_sha}")
    print(f"pr={pr_url or 'none (WIP checkpoints do not open a PR)'}")
    print(f"remaining_status={git(root, 'status', '--short').replace(chr(10), ';') or 'clean'}")
    return {"sha": remote_sha, "pr": pr_url}


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--repo", type=Path, default=Path.cwd())
    p.add_argument("--task", required=True)
    p.add_argument("--branch", required=True)
    p.add_argument("--file", action="append", default=[], help="explicit file path; repeat per file")
    p.add_argument("--message", required=True)
    p.add_argument("--verification", choices=("VERIFIED", "WIP_UNVERIFIED"), required=True)
    p.add_argument("--verify-command", help="shell command to run before a VERIFIED commit")
    p.add_argument("--wip-notes", help="required WIP record of incomplete work and known failures")
    p.add_argument("--pr", type=int, help="existing PR to reuse")
    p.add_argument("--stack-parent-pr", type=int, help="stack this new branch on an open parent PR (verified live; one level)")
    p.add_argument("--public-safe-reviewed", action="store_true", required=True,
                   help="attest that every explicit scoped file is approved for this public repository")
    p.add_argument("--maintenance-owner", action="store_true",
                   help="attest this task is the designated workflow for shared status/roadmap reconciliation")
    args = p.parse_args()
    try:
        publish(args)
        return 0
    except (Failure, subprocess.TimeoutExpired, OSError) as e:
        code = "UNSAFE_CONTENT_BLOCKED" if isinstance(e, UnsafeContent) else "PUSH_REJECTED" if isinstance(e, PushRejected) else "AUTHENTICATION_FAILURE" if isinstance(e, AuthenticationFailure) else "LOCAL_CHANGES_PENDING"
        print(f"{code}: {e}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
