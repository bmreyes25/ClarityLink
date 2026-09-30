#!/usr/bin/env python3
"""One-invocation, three-phase read-only runtime capture using existing su."""

from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path
import sys

from collector import Capture, FixedAdb, SafetyStop, REPO_ROOT
from privileged import PrivilegedRead, validate_su_fingerprint
from session import collect_privileged_phase, run_three_phase_session, ABORT_MESSAGE


# Step 40E2 established that the immutable archived su binary is group/other
# writable. Keep live collection mechanically disabled until a later reviewed
# change resolves that integrity issue and re-enables it deliberately.
LIVE_CAPTURE_ENABLED = False


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", default="auto",
                        help="existing authorized ADB serial, or auto if exactly one target is listed")
    parser.add_argument("--output-root", type=Path, default=Path.home(),
                        help="host directory outside Git for the new private raw capture")
    parser.add_argument("--dry-run", action="store_true", help="show fixed command plan; do not invoke ADB")
    args = parser.parse_args(argv)

    if not args.dry_run and not LIVE_CAPTURE_ENABLED:
        print("Live capture is disabled: resolve the archived su mode/integrity blocker and review before a vehicle session.", file=sys.stderr)
        print(ABORT_MESSAGE, file=sys.stderr)
        return 1

    try:
        adb = FixedAdb(args.serial, resolve_auto=not args.dry_run)
    except (SafetyStop, ValueError) as exc:
        print(f"Preflight stopped before target access: {exc}", file=sys.stderr)
        print(ABORT_MESSAGE, file=sys.stderr)
        return 1

    privileged = PrivilegedRead(adb)
    if args.dry_run:
        print("Dry run only; no ADB device command has been sent.")
        print("Identity fingerprint: ordinary read-only ADB shell.")
        for operation, kwargs in (
            ("identity", {}), ("ps", {}),
            ("process_read", {"pid": 1234, "leaf": "maps"}),
            ("process_read", {"pid": 1234, "leaf": "smaps"}),
            ("thread_list", {"pid": 1234}),
            ("thread_read", {"pid": 1234, "tid": 1234, "leaf": "status"}),
            ("fd_list", {"pid": 1234}), ("fd_link", {"pid": 1234, "fd": 3}),
            ("network_read", {"table": "tcp"}),
        ):
            from privileged import PrivilegedOperation
            print(privileged.dry_run_command(PrivilegedOperation(operation), **kwargs))
        print(adb.dry_run_command("hash-su"))
        print(adb.dry_run_command("ls-su"))
        return 0

    output_root = args.output_root.expanduser().resolve()
    try:
        output_root.relative_to(REPO_ROOT)
    except ValueError:
        pass
    else:
        print("refusing: raw capture must stay outside the Git worktree", file=sys.stderr)
        print(ABORT_MESSAGE, file=sys.stderr)
        return 1
    output = output_root / ("CLARITY_RUNTIME_PRIV_" + datetime.now().strftime("%Y%m%d_%H%M%S"))
    if output.exists():
        print("refusing: output path already exists", file=sys.stderr)
        print(ABORT_MESSAGE, file=sys.stderr)
        return 1
    output.mkdir(mode=0o700, parents=True)
    capture = Capture(adb, output)
    capture.privileged_mode = True
    capture.root_identity = None
    prior_identity = None

    def verify_preflight() -> None:
        capture.target_identity = capture.verify_target_identity()
        su_hash = capture.store("preflight", "privilege", "su_sha256", "hash-su",
                                timeout=5, max_bytes=64 * 1024)[1]
        su_listing = capture.store("preflight", "privilege", "su_metadata", "ls-su",
                                   timeout=5, max_bytes=64 * 1024)[1]
        validate_su_fingerprint(su_hash, su_listing)
        result = privileged.verify_root()
        capture.root_identity = "uid=0 verified"
        capture.record_result("preflight", "identity", "privileged_root_identity",
                              "privileged_identity", (), *result)
        capture.reader = privileged

    def collect(phase: str) -> None:
        nonlocal prior_identity
        identity = collect_privileged_phase(capture, privileged, phase, prior_identity)
        prior_identity = identity

    def finalize(success: bool) -> None:
        capture.stop_result = None if success else "safe_abort"
        capture.finalize([p for p in ("baseline", "connected", "post-disconnect")
                          if p in capture.phase_identities])

    complete = run_three_phase_session(verify_preflight=verify_preflight,
                                       collect_phase=collect, finalize=finalize)
    if complete:
        print(f"Host capture finalized: {output}")
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
