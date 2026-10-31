#!/usr/bin/env python3
"""Hash-pinned offline gate for a separately reviewed privileged-read campaign.

The live path is deliberately disabled. This module builds the reviewed fixed
manifest and validates external human attestations without contacting ADB.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
from dataclasses import asdict
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any

from collector import (Capture, FixedAdb, ProcessIdentity, REPO_ROOT, SafetyStop,
                       parse_ls_symlink_target, parse_ps_jmcs)
from privileged import (PrivilegedOperation, PrivilegedRead,
                        validate_su_fingerprint)
from parsers import (correlate_process_socket_endpoints, parse_maps,
                     parse_proc_net, parse_proc_net_unix, parse_proc_stat_start_time,
                     parse_status, parse_smaps)


HERE = Path(__file__).resolve().parent
PROFILE_PATH = HERE / "privileged_campaign_profile.json"
PROFILE_HASH_PATH = HERE / "privileged_campaign_profile.sha256"
SOURCE_LOCK_PATH = HERE / "privileged_campaign_source_hashes.json"
STATIC_DEPENDENCIES_PATH = HERE / "privileged_campaign_static_dependencies.json"
CAMPAIGN_ID = "CL-HONDA-ROOT-READ-EVIDENCE"
MAX_COMMAND_TIMEOUT = 30
MAX_COMMAND_OUTPUT = 16 * 1024 * 1024
MAX_FD_COUNT = 256
PHASE_IDS = ("R2_baseline_disconnected", "R3_before_connect_disconnected",
             "R3_carplay_connected", "R3_post_disconnect")
STAGE_IDS = ("R0_nonexecuting", "R1_minimum_privilege_check",
             "R2_targeted_metadata", "R3_normal_carplay_correlation")
STAGE_PHASES = {"R0_nonexecuting": [], "R1_minimum_privilege_check": [],
                "R2_targeted_metadata": [PHASE_IDS[0]],
                "R3_normal_carplay_correlation": list(PHASE_IDS[1:])}

# These are the only elevated reads in the proposed profile. Paths and numeric
# identifiers are assembled through PrivilegedRead's enum API.
PHASE_OPERATIONS = (
    ("identity", (), 5, 16 * 1024),
    ("ps", (), 10, 2 * 1024 * 1024),
    ("process_read", ("<JMCS_PID>", "stat"), 5, 64 * 1024),
    ("process_read", ("<JMCS_PID>", "status"), 5, 256 * 1024),
    ("process_read", ("<JMCS_PID>", "cmdline"), 5, 64 * 1024),
    ("process_exe_link", ("<JMCS_PID>",), 5, 64 * 1024),
    ("process_read", ("<JMCS_PID>", "maps"), 10, 4 * 1024 * 1024),
    ("process_read", ("<JMCS_PID>", "smaps"), 30, MAX_COMMAND_OUTPUT),
    ("fd_list", ("<JMCS_PID>",), 10, 2 * 1024 * 1024),
    ("fd_link_each", ("<JMCS_PID>", "<FD_NONNEGATIVE_32BIT>"), 5, 64 * 1024),
    *(("network_read", (table,), 10, 2 * 1024 * 1024)
      for table in ("tcp", "tcp6", "udp", "udp6", "unix")),
    ("ps", (), 10, 2 * 1024 * 1024),
    ("process_read", ("<JMCS_PID>", "stat"), 5, 64 * 1024),
    ("process_read", ("<JMCS_PID>", "status"), 5, 256 * 1024),
    ("process_read", ("<JMCS_PID>", "cmdline"), 5, 64 * 1024),
    ("process_exe_link", ("<JMCS_PID>",), 5, 64 * 1024),
    ("identity", (), 5, 16 * 1024),
)

LIVE_CAPTURE_ENABLED = False


def canonical_json(value: object) -> bytes:
    return (json.dumps(value, sort_keys=True, indent=2, ensure_ascii=True) + "\n").encode()


def profile_payload() -> dict[str, Any]:
    return {
        "campaign_id": CAMPAIGN_ID,
        "schema_version": 1,
        "status": "REVIEW_REQUIRED_LIVE_DISABLED",
        "target": {"android_release": "4.2.2", "android_sdk": "17",
                   "product_device": "vcm30t30a", "product_board": "Andromeda",
                   "hardware": "vcm30t30", "process": "/system/bin/jmcs",
                   "expected_uid": "0", "expected_gid": "0"},
        "transport": "one exact owner-approved existing ADB serial; never auto-enumerate",
        "privilege": {"executable": "/system/xbin/su", "invocation": "-c",
                       "expected_sha256": "d95fdbb551aca66d8a81471ea7683f58dba75a09d5cdc4712209b955574eab26",
                       "required_owner": "root", "required_setuid": True,
                       "group_other_writable": False,
                       "zero_target_write": "NOT ESTABLISHED; review must explicitly accept possible SuperSU state/log/daemon writes"},
        "source_lock_sha256": hashlib.sha256(SOURCE_LOCK_PATH.read_bytes()).hexdigest(),
        "limits": {"max_command_timeout_seconds": MAX_COMMAND_TIMEOUT,
                   "max_command_output_bytes": MAX_COMMAND_OUTPUT,
                   "max_fd_entries": MAX_FD_COUNT,
                   "phase_upper_bounds": {
                       "R0_nonexecuting": {"command_count": 9, "timeout_seconds_sum": 45,
                                            "output_bytes_sum": (16 + 64 + 5 * 64 + 16 + 16) * 1024},
                       "R1_minimum_privilege_check": {"command_count": 1,
                                                      "timeout_seconds_sum": 5,
                                                      "output_bytes_sum": 16 * 1024},
                       "R2_targeted_metadata": {
                           "command_count": sum(MAX_FD_COUNT if row[0] == "fd_link_each" else 1
                                                for row in PHASE_OPERATIONS),
                           "timeout_seconds_sum": sum(row[2] * (MAX_FD_COUNT if row[0] == "fd_link_each" else 1)
                                                      for row in PHASE_OPERATIONS),
                           "output_bytes_sum": sum(row[3] * (MAX_FD_COUNT if row[0] == "fd_link_each" else 1)
                                                    for row in PHASE_OPERATIONS)},
                       "R3_normal_carplay_correlation": {
                           "command_count": 3 * sum(MAX_FD_COUNT if row[0] == "fd_link_each" else 1
                                                     for row in PHASE_OPERATIONS),
                           "timeout_seconds_sum": 3 * sum(row[2] * (MAX_FD_COUNT if row[0] == "fd_link_each" else 1)
                                                          for row in PHASE_OPERATIONS),
                           "output_bytes_sum": 3 * sum(row[3] * (MAX_FD_COUNT if row[0] == "fd_link_each" else 1)
                                                       for row in PHASE_OPERATIONS)},
                       "human_transition_waits_included": False},
                   "stop_on_timeout_output_limit_permission_denial_or_identity_change": True,
                   "retry": False, "fallback": False},
        "stages": [
            {"id": "R0_nonexecuting", "elevated": False,
             "purpose": "Check target identity and su file metadata/hash without executing su; stop if fingerprint or mode fails.",
             "operations": [
                 {"operation": "id", "argv": ["adb", "-s", "<EXACT_SERIAL>", "shell", "id"], "timeout_seconds": 5, "max_output_bytes": 16384},
                 {"operation": "kernel_identity", "argv": ["adb", "-s", "<EXACT_SERIAL>", "shell", "cat", "/proc/version"], "timeout_seconds": 5, "max_output_bytes": 65536},
                 {"operation": "identity_properties", "argv": ["adb", "-s", "<EXACT_SERIAL>", "shell", "getprop", "<one fixed Android identity property>"], "properties": ["ro.build.version.release", "ro.build.version.sdk", "ro.product.device", "ro.product.board", "ro.hardware"], "timeout_seconds": 5, "max_output_bytes": 65536},
                 {"operation": "sha256sum", "argv": ["adb", "-s", "<EXACT_SERIAL>", "shell", "sha256sum", "/system/xbin/su"], "timeout_seconds": 5, "max_output_bytes": 16384},
                 {"operation": "ls_metadata", "argv": ["adb", "-s", "<EXACT_SERIAL>", "shell", "ls", "-l", "/system/xbin/su"], "timeout_seconds": 5, "max_output_bytes": 16384},
             ]},
            {"id": "R1_minimum_privilege_check", "elevated": True,
             "operations": [{"operation": "identity", "command": "/system/xbin/su -c id",
                            "timeout_seconds": 5, "max_output_bytes": 16384,
                            "expected": "exit 0 and uid=0; any prompt, denial or unexpected state stops"}]},
            {"id": "R2_targeted_metadata", "elevated": True,
             "phases": list(PHASE_IDS[:1]),
             "operations": [_operation_dict(row) for row in PHASE_OPERATIONS]},
            {"id": "R3_normal_carplay_correlation", "elevated": True,
             "phases": list(PHASE_IDS[1:]),
             "owner_transitions": ["normal stock CarPlay connect", "normal disconnect"],
             "operations": [_operation_dict(row) for row in PHASE_OPERATIONS]},
        ],
        "socket_attribution": "only exact jmcs fd symlink socket:[inode] correspondence to /proc/net rows; otherwise unattributed",
        "exclusions": ["/proc/<pid>/mem", "credentials", "environ", "auth secrets", "private keys",
                       "signals", "ptrace", "debugger attach", "memory permission changes", "process modification",
                       "helper upload/exec", "adb root", "settings/properties/mount changes", "CAN", "deployment"],
        "private_evidence": {"raw_output": "owner-only host directory outside Git, mode 0700",
                              "files": "mode 0600", "manifest": "SHA-256 covers every evidence artifact",
                              "network_endpoints_and_process_metadata": "private; sanitized public summaries only"},
        "approval": "independent qualified human review and separate exact owner authorization are required for every live stage; this file is not an approval",
    }


def _operation_dict(row: tuple[str, tuple[str, ...], int, int]) -> dict[str, Any]:
    op, args, timeout, maximum = row
    return {"operation": op, "arguments": list(args), "timeout_seconds": timeout,
            "max_output_bytes": maximum, "failure_policy": "stop_without_retry"}


def verify_profile() -> str:
    try:
        if any(path.is_symlink() for path in (PROFILE_PATH, PROFILE_HASH_PATH, SOURCE_LOCK_PATH)):
            raise SafetyStop("privileged campaign profile pins cannot be symlinks")
        actual_bytes = PROFILE_PATH.read_bytes()
        expected_bytes = canonical_json(profile_payload())
        expected_hash = PROFILE_HASH_PATH.read_text(encoding="ascii").split()[0]
    except (OSError, ValueError, IndexError) as exc:
        raise SafetyStop("privileged campaign profile or hash pin is unavailable") from exc
    actual_hash = hashlib.sha256(actual_bytes).hexdigest()
    if actual_bytes != expected_bytes or not re.fullmatch(r"[0-9a-f]{64}", expected_hash) or actual_hash != expected_hash:
        raise SafetyStop("privileged campaign profile does not match its exact committed hash pin")
    source_hashes()
    _verify_fixed_operations()
    return actual_hash


def source_hashes() -> dict[str, str]:
    try:
        if SOURCE_LOCK_PATH.is_symlink():
            raise SafetyStop("privileged source hash lock cannot be a symlink")
        lock = json.loads(SOURCE_LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyStop("privileged source hash lock is unreadable") from exc
    expected_names = {"analyze.py", "privileged.py", "privileged_campaign.py", "collector.py", "parsers.py",
                      "privileged_campaign_static_dependencies.json"}
    if not isinstance(lock, dict) or set(lock) != expected_names:
        raise SafetyStop("privileged source hash lock has an unexpected file set")
    actual: dict[str, str] = {}
    for name, expected in sorted(lock.items()):
        candidate = HERE / name
        if candidate.is_symlink():
            raise SafetyStop("privileged source lock contains an unsafe path")
        path = candidate.resolve()
        if HERE not in path.parents or not path.is_file():
            raise SafetyStop("privileged source lock contains an unsafe path")
        digest = hashlib.sha256(path.read_bytes()).hexdigest()
        if not isinstance(expected, str) or not re.fullmatch(r"[0-9a-f]{64}", expected) or digest != expected:
            raise SafetyStop(f"pinned privileged source hash mismatch: {name}")
        actual[name] = digest
    return actual


def _verify_fixed_operations() -> None:
    allowed_process_leaves = {"stat", "status", "cmdline", "maps", "smaps"}
    if {row[1][1] for row in PHASE_OPERATIONS if row[0] == "process_read"} != allowed_process_leaves:
        raise SafetyStop("privileged process-read manifest changed unexpectedly")
    for operation, arguments, timeout, maximum in PHASE_OPERATIONS:
        if not (0 < timeout <= MAX_COMMAND_TIMEOUT and 0 < maximum <= MAX_COMMAND_OUTPUT):
            raise SafetyStop("privileged operation exceeds profile timeout/output limits")
        if operation == "process_read" and arguments[1] not in allowed_process_leaves:
            raise SafetyStop("privileged process path is outside the reviewed allowlist")
        if operation == "network_read" and arguments[0] not in {"tcp", "tcp6", "udp", "udp6", "unix"}:
            raise SafetyStop("network table is outside the reviewed allowlist")
        if operation not in {"identity", "ps", "process_read", "process_exe_link", "fd_list",
                             "fd_link_each", "network_read"}:
            raise SafetyStop("operation is not in the reviewed privileged allowlist")


def _capture_call(capture: Capture, reader: PrivilegedRead, phase: str, category: str,
                  name: str, operation: PrivilegedOperation | str, *args: str,
                  timeout: int, maximum: int, record_pid: int | None = None,
                  **operation_kwargs: Any) -> bytes:
    code, output, error = reader.run(operation, *args, timeout=timeout,
                                     max_bytes=maximum, **operation_kwargs)
    capture.record_result(phase, category, name, str(operation), args, code, output, error,
                          pid=record_pid)
    if code != 0:
        raise SafetyStop(f"{phase} {name} failed (exit {code}); stop without retry")
    return output


def _discover_bounded_identity(capture: Capture, reader: PrivilegedRead,
                               phase: str, label: str) -> ProcessIdentity:
    ps = _capture_call(capture, reader, phase, "identity", f"{label}_ps",
                       PrivilegedOperation.PS, timeout=10, maximum=2 * 1024 * 1024)
    pids = parse_ps_jmcs(ps.decode("utf-8", "replace"))
    if len(pids) != 1:
        raise SafetyStop(f"expected one jmcs process; observed {len(pids)}")
    pid = pids[0]
    values: dict[str, bytes] = {}
    for leaf, maximum in (("stat", 64 * 1024), ("status", 256 * 1024), ("cmdline", 64 * 1024)):
        values[leaf] = _capture_call(capture, reader, phase, "identity", f"{label}_{leaf}",
                                     PrivilegedOperation.PROCESS_READ, pid=pid, leaf=leaf,
                                         timeout=5, maximum=maximum, record_pid=pid)
    status = parse_status(values["status"].decode("utf-8", "replace"))
    argv0 = values["cmdline"].split(b"\0", 1)[0].decode("utf-8", "replace").strip()
    try:
        start = parse_proc_stat_start_time(values["stat"].decode("utf-8", "replace"))
        status_pid = int(status["Pid"])
        uid = status["Uid"].split()[0]
        gid = status["Gid"].split()[0]
        ppid = status.get("PPid", "")
    except (KeyError, ValueError, IndexError) as exc:
        raise SafetyStop("jmcs process identity fields are incomplete") from exc
    if (status_pid != pid or status.get("Name", "").strip() != "jmcs"
            or Path(argv0).name != "jmcs" or uid != "0" or gid != "0"):
        raise SafetyStop("jmcs PID, comm or executable command line does not match")
    capture.record_result(phase, "process", "status", "read", f"/proc/{pid}/status",
                          0, values["status"], b"", pid=pid)
    return ProcessIdentity(pid, start, argv0,
                           values["cmdline"].replace(b"\0", b" ").decode("utf-8", "replace").strip(),
                           uid, gid, ppid)


def collect_bounded_phase(capture: Capture, reader: PrivilegedRead, phase: str,
                          expected_identity: ProcessIdentity | None = None) -> ProcessIdentity:
    """Collect one exact R2/R3 phase; the caller must pass the reviewed owner action."""
    started_utc = datetime.now(timezone.utc).isoformat()
    root_id = reader.verify_root()
    capture.record_result(phase, "identity", "privileged_uid", "privileged_identity", (), *root_id)
    before = _discover_bounded_identity(capture, reader, phase, "before")
    if expected_identity is not None and (
            before.pid, before.start_time_ticks, before.executable, before.uid, before.gid) != (
            expected_identity.pid, expected_identity.start_time_ticks, expected_identity.executable,
            expected_identity.uid, expected_identity.gid):
        raise SafetyStop("jmcs process identity changed between approved phases")
    pid = before.pid
    capture.phase_identities[phase] = before
    exe = _capture_call(capture, reader, phase, "process", "executable_link",
                        PrivilegedOperation.PROCESS_EXE_LINK, pid=pid,
                        timeout=5, maximum=64 * 1024, record_pid=pid)
    exe_path = parse_ls_symlink_target(exe).removesuffix(" (deleted)")
    if exe_path != "/system/bin/jmcs":
        raise SafetyStop("/proc/<pid>/exe did not prove the expected jmcs executable")

    maps_raw = _capture_call(capture, reader, phase, "process", "maps", "read",
                             f"/proc/{pid}/maps", timeout=10, maximum=4 * 1024 * 1024, record_pid=pid)
    smaps_raw = _capture_call(capture, reader, phase, "process", "smaps", "read",
                              f"/proc/{pid}/smaps", timeout=30, maximum=MAX_COMMAND_OUTPUT, record_pid=pid)
    try:
        mappings = parse_maps(maps_raw.decode("utf-8", "strict"))
        smaps = parse_smaps(smaps_raw.decode("utf-8", "strict"))
    except (UnicodeDecodeError, ValueError) as exc:
        raise SafetyStop("maps/smaps output is malformed; phase stopped") from exc
    if not any(m.pathname.removesuffix(" (deleted)") == "/system/bin/jmcs" and "x" in m.permissions
               for m in mappings):
        raise SafetyStop("maps contain no executable /system/bin/jmcs mapping")

    fd_raw = _capture_call(capture, reader, phase, "process", "fd_links", "list",
                           f"/proc/{pid}/fd", timeout=10, maximum=2 * 1024 * 1024, record_pid=pid)
    fd_ids = _parse_fd_ids(fd_raw)
    if len(fd_ids) > MAX_FD_COUNT:
        raise SafetyStop("jmcs FD count exceeds the reviewed 256 descriptor ceiling")
    fd_targets: dict[str, dict[str, object]] = {}
    for fd in fd_ids:
        raw = _capture_call(capture, reader, phase, "process", f"fd_{fd}_target", "readlink",
                            f"/proc/{pid}/fd/{fd}", timeout=5, maximum=64 * 1024, record_pid=pid)
        target = parse_ls_symlink_target(raw)
        if not target:
            raise SafetyStop(f"FD {fd} symlink target was not readable")
        socket = re.fullmatch(r"socket:\[(\d+)\]", target)
        fd_targets[str(fd)] = {"target": target,
                               "socket_inode": int(socket.group(1)) if socket else None}

    net: dict[str, list[dict[str, object]]] = {}
    unix_rows: tuple[dict[str, str], ...] = ()
    for table in ("tcp", "tcp6", "udp", "udp6", "unix"):
        artifact_name = {"tcp": "tcp4", "tcp6": "tcp6", "udp": "udp4",
                         "udp6": "udp6", "unix": "unix"}[table]
        raw = _capture_call(capture, reader, phase, "network", artifact_name, "read",
                            f"/proc/net/{table}", timeout=10, maximum=2 * 1024 * 1024, record_pid=pid)
        try:
            if table == "unix":
                unix_rows = parse_proc_net_unix(raw.decode("utf-8", "strict"))
            else:
                protocol = "tcp" if table.startswith("tcp") else "udp"
                family = 6 if table.endswith("6") else 4
                net[table] = [asdict(row) for row in parse_proc_net(
                    raw.decode("utf-8", "strict"), protocol, family)]
        except (UnicodeDecodeError, ValueError) as exc:
            raise SafetyStop(f"/proc/net/{table} output could not be parsed") from exc
    owned = correlate_process_socket_endpoints(fd_targets, net, unix_rows)
    correlation = {"attribution": "verified_fd_inode_match_only", "owned_socket_count": len(owned),
                   "sockets": owned}
    capture.record_result(phase, "network", "jmcs_socket_inode_correlations",
                          "offline_fd_inode_join", (), 0,
                          (json.dumps(correlation, sort_keys=True) + "\n").encode(), b"", pid=pid)
    after = _discover_bounded_identity(capture, reader, phase, "after")
    after_exe = _capture_call(capture, reader, phase, "process", "executable_link_after",
                              PrivilegedOperation.PROCESS_EXE_LINK, pid=pid,
                              timeout=5, maximum=64 * 1024, record_pid=pid)
    if (after != before or parse_ls_symlink_target(after_exe).removesuffix(" (deleted)") != exe_path):
        raise SafetyStop("jmcs identity changed during privileged collection")
    reader.verify_root()
    capture.phase_times[phase] = {"started_utc": started_utc,
                                  "finished_utc": datetime.now(timezone.utc).isoformat()}
    return after


def compare_runtime_dependencies(runtime_mapping_paths: list[str],
                                 saved_elf_needed_names: list[str]) -> dict[str, Any]:
    """Compare actual path mappings with saved ELF NEEDED names without conflating them."""
    if any(not isinstance(path, str) or not path.startswith("/") for path in runtime_mapping_paths):
        raise SafetyStop("runtime library paths must be absolute strings from parsed maps")
    if any(not isinstance(name, str) or not name or "/" in name for name in saved_elf_needed_names):
        raise SafetyStop("saved ELF dependency names must be basename-only NEEDED values")
    mapped = sorted({Path(path.removesuffix(" (deleted)")).name
                     for path in runtime_mapping_paths if Path(path).name.endswith(".so")})
    needed = sorted(set(saved_elf_needed_names))
    return {
        "runtime_mapped_library_basenames": mapped,
        "saved_elf_needed_names": needed,
        "saved_dependencies_currently_mapped": sorted(set(mapped) & set(needed)),
        "saved_dependencies_not_seen_in_runtime_maps": sorted(set(needed) - set(mapped)),
        "runtime_mappings_not_listed_as_elf_needed": sorted(set(mapped) - set(needed)),
        "interpretation": "Runtime map evidence is observational for the captured process epoch; ELF NEEDED entries are static dependencies and do not prove runtime loading.",
    }


def analyze_privileged_capture(output: Path, phases_to_analyze: list[str]) -> dict[str, Any]:
    """Use the existing offline maps/smaps analyzer and add a pinned ELF comparison."""
    source_hashes()
    try:
        dependencies = json.loads(STATIC_DEPENDENCIES_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyStop("saved jmcs ELF dependency inventory is unavailable") from exc
    needed = dependencies.get("jmcs_needed") if isinstance(dependencies, dict) else None
    if not isinstance(needed, list) or not all(isinstance(name, str) for name in needed):
        raise SafetyStop("saved jmcs ELF dependency inventory is malformed")
    import analyze
    result: dict[str, Any] = {"static_dependency_source": dependencies.get("evidence_source"),
                              "evidence_class": dependencies.get("evidence_class"),
                              "phases": {}}
    for phase in phases_to_analyze:
        summary = analyze.analyze_phase(output, phase)
        maps_path = output / phase / "process" / "maps.raw"
        try:
            maps = parse_maps(maps_path.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, ValueError) as exc:
            raise SafetyStop(f"saved maps for {phase} cannot be analyzed") from exc
        mapped_paths = [mapping.pathname for mapping in maps if mapping.pathname.startswith("/")]
        summary["runtime_dependency_comparison"] = compare_runtime_dependencies(mapped_paths, needed)
        summary["mapped_library_paths"] = sorted({path for path in mapped_paths
                                                  if Path(path.removesuffix(" (deleted)")).name.endswith(".so")})
        result["phases"][phase] = summary
    return result


def run_r0_nonexecuting_preflight(capture: Capture) -> None:
    """Check the target and su file only through ordinary ADB shell reads."""
    target = capture.verify_target_identity("R0_nonexecuting")
    code, shell_identity = capture.store_required("R0_nonexecuting", "identity", "shell_identity",
                                                 "id", timeout=5, max_bytes=16 * 1024)
    if not re.search(rb"(?:^|\s)uid=2000\(shell\)(?:\s|$)", shell_identity):
        raise SafetyStop("R0 expected ordinary UID 2000 shell; stop before su invocation")
    digest = capture.store_required("R0_nonexecuting", "privilege", "su_sha256", "hash-su",
                                    timeout=5, max_bytes=16 * 1024)[1]
    metadata = capture.store_required("R0_nonexecuting", "privilege", "su_metadata", "ls-su",
                                      timeout=5, max_bytes=16 * 1024)[1]
    validate_su_fingerprint(digest, metadata)
    capture.target_identity = target


def run_r1_minimum_privilege_check(capture: Capture, reader: PrivilegedRead) -> None:
    """Issue only the fixed `su -c id` check after R0 and separate R1 approval."""
    code, stdout, stderr = reader.verify_root()
    capture.record_result("R1_minimum_privilege_check", "identity", "root_identity",
                          "privileged_identity", (), code, stdout, stderr)
    capture.root_identity = "uid=0 verified"


def recheck_su_fingerprint(capture: Capture, stage_id: str) -> None:
    """Require the reviewed ordinary-shell fingerprint immediately before su use."""
    digest = capture.store_required(stage_id, "privilege", "su_sha256_pre_elevation", "hash-su",
                                    timeout=5, max_bytes=16 * 1024)[1]
    metadata = capture.store_required(stage_id, "privilege", "su_metadata_pre_elevation", "ls-su",
                                      timeout=5, max_bytes=16 * 1024)[1]
    validate_su_fingerprint(digest, metadata)


def _confirm_owner(input_fn: Any, token: str, prompt: str) -> None:
    if input_fn(prompt).strip() != token:
        raise SafetyStop("owner did not confirm the exact reviewed step; stopping without retry")


def _finalize_root_capture(capture: Capture, phases: list[str]) -> None:
    """Finalize hashes without inheriting the generic collector's zero-write claim."""
    capture.finalize(phases)
    manifest_path = capture.output / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    guarantees = [item for item in manifest.get("guarantees", [])
                  if item != "no target file writes"]
    guarantees.append("fixed enumerated command profile; no arbitrary remote command API")
    manifest["guarantees"] = guarantees
    manifest["target_side_effect_assessment"] = (
        "No explicit target write command is in this profile. This does not prove zero target-side effects. "
        + ("SuperSU daemon, request, logging and persistent-state effects remain unknown."
           if getattr(capture, "privileged_mode", False) else
           "R0 does not execute su; read-side filesystem and system effects are not claimed absent."))
    manifest_path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    manifest_path.chmod(0o600)
    entries = []
    for path in sorted(capture.output.rglob("*")):
        if path.is_symlink():
            raise SafetyStop("capture contains a symlink; hash finalization stopped")
        if path.is_file() and path.name != "sha256.txt":
            entries.append(f"{hashlib.sha256(path.read_bytes()).hexdigest()}  {path.relative_to(capture.output)}")
    inventory = capture.output / "sha256.txt"
    inventory.write_text("\n".join(entries) + "\n", encoding="ascii")
    inventory.chmod(0o600)


def run_r3_interactive_sequence(capture: Capture, reader: PrivilegedRead,
                                input_fn: Any = input, output_fn: Any = print) -> None:
    """Run the owner-controlled baseline/connect/disconnect metadata sequence."""
    _confirm_owner(input_fn, "BASELINE", "Confirm Park, brake, reviewed power state, factory baseline and iPhone disconnected; type BASELINE: ")
    identity = collect_bounded_phase(capture, reader, PHASE_IDS[1])
    output_fn("Collecting baseline complete. Owner controls the normal stock CarPlay connection.")
    _confirm_owner(input_fn, "CONNECTED", "Confirm stock CarPlay connected normally and Type110/factory behavior is normal; type CONNECTED: ")
    identity = collect_bounded_phase(capture, reader, PHASE_IDS[2], identity)
    output_fn("Connected phase complete. Owner controls normal CarPlay disconnect.")
    _confirm_owner(input_fn, "DISCONNECTED", "Confirm normal disconnect and factory behavior is normal; type DISCONNECTED: ")
    collect_bounded_phase(capture, reader, PHASE_IDS[3], identity)
    _confirm_owner(input_fn, "RESTORED", "Confirm center display, cluster, Navigation and audio restored; type RESTORED: ")


def execute_approved_stage(authorization: dict[str, Any], stage_id: str, output_root: Path,
                           input_fn: Any = input, output_fn: Any = print) -> Path:
    """Execute only one already reviewed/authorized stage; no enumeration or retry."""
    if not LIVE_CAPTURE_ENABLED:
        raise SafetyStop("live root capture is disabled pending SuperSU safety resolution")
    serial = authorization["adb_serial"]
    if serial == "auto":
        raise SafetyStop("auto serial selection is never permitted")
    adb = FixedAdb(serial, resolve_auto=False)
    requested_root = output_root.expanduser()
    if requested_root.is_symlink():
        raise SafetyStop("private output root cannot be a symlink")
    root = requested_root.resolve()
    try:
        root.relative_to(REPO_ROOT.resolve())
    except ValueError:
        pass
    else:
        raise SafetyStop("raw capture must remain outside the Git worktree")
    if not root.exists():
        root.mkdir(mode=0o700, parents=True)
    if not root.is_dir() or root.stat().st_mode & 0o777 != 0o700:
        raise SafetyStop("private output root is not a directory")
    output = root / (
        f"CLARITY_ROOT_READ_{stage_id}_{datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%SZ')}")
    try:
        output.relative_to(REPO_ROOT.resolve())
    except ValueError:
        pass
    else:
        raise SafetyStop("raw capture must remain outside the Git worktree")
    output.mkdir(mode=0o700, parents=True, exist_ok=False)
    capture = Capture(adb, output)
    capture.campaign_metadata = {"campaign_id": CAMPAIGN_ID,
                                 "stage_id": stage_id,
                                 "profile_sha256": verify_profile(),
                                 "source_hashes": source_hashes()}
    capture.privileged_mode = stage_id != "R0_nonexecuting"
    reader = PrivilegedRead(adb)
    phase_order: list[str] = []
    try:
        _confirm_owner(input_fn, "READY", "Confirm owner present, stationary Park, parking brake and reviewed PHEV power state; type READY: ")
        if stage_id == "R0_nonexecuting":
            run_r0_nonexecuting_preflight(capture)
            phase_order = ["R0_nonexecuting"]
        elif stage_id == "R1_minimum_privilege_check":
            recheck_su_fingerprint(capture, stage_id)
            run_r1_minimum_privilege_check(capture, reader)
            phase_order = [stage_id]
        elif stage_id == "R2_targeted_metadata":
            recheck_su_fingerprint(capture, stage_id)
            _confirm_owner(input_fn, "DISCONNECTED", "Confirm iPhone disconnected and factory display/audio/cluster normal; type DISCONNECTED: ")
            collect_bounded_phase(capture, reader, PHASE_IDS[0])
            phase_order = [PHASE_IDS[0]]
        elif stage_id == "R3_normal_carplay_correlation":
            recheck_su_fingerprint(capture, stage_id)
            run_r3_interactive_sequence(capture, reader, input_fn, output_fn)
            phase_order = list(PHASE_IDS[1:])
        else:
            raise SafetyStop("stage is not supported")
        capture.stop_result = "complete"
        _finalize_root_capture(capture, phase_order)
        if stage_id in {"R2_targeted_metadata", "R3_normal_carplay_correlation"}:
            analysis = analyze_privileged_capture(output, phase_order)
            for phase, summary in analysis["phases"].items():
                capture.record_result(phase, "analysis", "runtime_and_dependency_summary",
                                      "offline_analysis", (), 0,
                                      (json.dumps(summary, indent=2, sort_keys=True) + "\n").encode(), b"")
            _finalize_root_capture(capture, phase_order)
        output_fn(f"Stage complete; private evidence finalized at {output}")
        return output
    except Exception as exc:
        capture.stop_result = "safe_abort"
        capture.failure_card = {"stage_id": stage_id, "status": "STOPPED_NO_RETRY",
                                "exception_type": type(exc).__name__,
                                "completed_phases": phase_order}
        try:
            _finalize_root_capture(capture, phase_order)
        except Exception:
            output_fn("Host finalization failed; preserve all existing files and stop.")
        output_fn(f"Stage stopped ({type(exc).__name__}); no retry or fallback.")
        raise


def _parse_fd_ids(raw: bytes) -> tuple[int, ...]:
    values: set[int] = set()
    try:
        lines = raw.decode("utf-8", "strict").splitlines()
    except UnicodeDecodeError as exc:
        raise SafetyStop("FD listing was not valid UTF-8") from exc
    for line in lines:
        if not line.strip():
            continue
        match = re.search(r"(?:^|\s)([0-9]+)\s*->\s*", line)
        if not match:
            raise SafetyStop("FD listing contained an unparseable descriptor row")
        value = int(match.group(1))
        if value > 2_147_483_647:
            raise SafetyStop("FD number exceeds the supported numeric bound")
        values.add(value)
    if not values:
        raise SafetyStop("FD listing contained no parseable descriptors")
    return tuple(sorted(values))


def dry_run_report(serial: str = "EXACT_APPROVED_SERIAL") -> dict[str, Any]:
    """Build command plan locally without constructing ADB or contacting a target."""
    profile_hash = verify_profile()
    if not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", serial) or serial == "auto":
        raise SafetyStop("dry-run serial must be an explicit exact serial label")
    adb = FixedAdb.__new__(FixedAdb)
    adb.adb, adb.serial, adb.records = "adb", serial, []
    reader = PrivilegedRead(adb)
    result = []
    for operation, args, timeout, maximum in (
            ("id", (), 5, 16384),
            ("read", ("/proc/version",), 5, 64 * 1024),
            *(("property", (name,), 5, 64 * 1024) for name in (
                "ro.build.version.release", "ro.build.version.sdk", "ro.product.device",
                "ro.product.board", "ro.hardware")),
            ("hash-su", (), 5, 16384), ("ls-su", (), 5, 16384)):
        command = FixedAdb.plan_without_adb_lookup(serial, operation, args)
        result.append({"stage": "R0_nonexecuting", "argv": list(command),
                       "timeout_seconds": timeout, "max_output_bytes": maximum,
                       "expected": "exact archived identity and su SHA/metadata; stop on any mismatch"})
    for stage, operation in (("R1_minimum_privilege_check", "identity"),):
        command = ("adb", "-s", serial, "shell", "/system/xbin/su", "-c", "id")
        result.append({"stage": stage, "argv": list(command), "timeout_seconds": 5,
                       "max_output_bytes": 16384, "expected": "uid=0; stop on any deviation"})
    for phase in PHASE_IDS:
        for operation, args, timeout, maximum in PHASE_OPERATIONS:
            kwargs: dict[str, Any] = {}
            if operation in {"process_read", "process_exe_link", "fd_list", "fd_link_each"}:
                kwargs["pid"] = 1234
            if operation == "process_read":
                kwargs["leaf"] = args[1]
                op_enum = PrivilegedOperation.PROCESS_READ
            elif operation == "process_exe_link":
                op_enum = PrivilegedOperation.PROCESS_EXE_LINK
            elif operation == "fd_list":
                op_enum = PrivilegedOperation.FD_LIST
            elif operation == "fd_link_each":
                kwargs["fd"] = 3
                op_enum = PrivilegedOperation.FD_LINK
            elif operation == "network_read":
                kwargs["table"] = args[0]
                op_enum = PrivilegedOperation.NETWORK_READ
            else:
                op_enum = PrivilegedOperation(operation)
            argv = reader.plan(op_enum, **kwargs)
            result.append({"stage": phase, "argv": list(argv), "timeout_seconds": timeout,
                           "max_output_bytes": maximum,
                           "note": "PID/FD values shown are placeholders; run-time values require strict parsing and bounds."})
    return {"campaign_id": CAMPAIGN_ID, "profile_sha256": profile_hash,
            "source_hashes": source_hashes(), "live_capture_enabled": False,
            "live_capture_gate": "exact stage-specific human review plus separate owner authorization",
            "commands": result}


def validate_authorization(path: Path, *, stage_id: str,
                           review_artifact: Path | None = None) -> dict[str, Any]:
    """Validate one stage's private owner record and exact independent review."""
    profile_hash = verify_profile()
    if stage_id not in STAGE_IDS:
        raise SafetyStop("authorization stage is not a member of this profile")
    try:
        requested = path.expanduser()
        if requested.is_symlink() or not requested.is_file() or requested.stat().st_size > 1024 * 1024:
            raise SafetyStop("authorization record must be a bounded regular private file")
        try:
            requested.resolve().relative_to(REPO_ROOT.resolve())
        except ValueError:
            pass
        else:
            raise SafetyStop("authorization record must remain outside the Git worktree")
        if requested.stat().st_mode & 0o777 != 0o600:
            raise SafetyStop("authorization record must be owner-only (mode 0600)")
        data = json.loads(requested.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SafetyStop("authorization record is missing or malformed") from exc
    if not isinstance(data, dict) or data.get("campaign_id") != CAMPAIGN_ID:
        raise SafetyStop("authorization campaign id does not match")
    if data.get("profile_sha256") != profile_hash or data.get("source_hashes") != source_hashes():
        raise SafetyStop("authorization does not bind the current profile and source hashes")
    if data.get("stage_id") != stage_id:
        raise SafetyStop("owner authorization is not for this exact stage")
    if data.get("phase_ids") != STAGE_PHASES[stage_id]:
        raise SafetyStop("owner authorization phase list does not exactly match the stage")
    if data.get("owner_authorized") is not True:
        raise SafetyStop("separate exact owner authorization is absent")
    try:
        datetime.fromisoformat(str(data.get("owner_authorized_utc", "")).replace("Z", "+00:00"))
    except ValueError as exc:
        raise SafetyStop("owner authorization timestamp is invalid") from exc
    serial = data.get("adb_serial")
    if not isinstance(serial, str) or serial == "auto" or not re.fullmatch(r"[A-Za-z0-9._:-]{1,128}", serial):
        raise SafetyStop("authorization must name one exact ADB serial")
    if data.get("owner_confirmed_park") is not True or data.get("owner_confirmed_parking_brake") is not True:
        raise SafetyStop("owner has not attested stationary Park and parking brake")
    if data.get("owner_present") is not True or data.get("owner_confirmed_factory_baseline") is not True:
        raise SafetyStop("owner presence and normal factory baseline are not attested")
    stage_index = STAGE_IDS.index(stage_id)
    expected_receipts = STAGE_IDS[:stage_index]
    receipt_rows = data.get("prior_stage_receipts", [])
    if not isinstance(receipt_rows, list) or [row.get("stage_id") for row in receipt_rows
                                              if isinstance(row, dict)] != list(expected_receipts):
        raise SafetyStop("prior stage receipts are missing or out of order")
    for receipt in receipt_rows:
        if not isinstance(receipt, dict):
            raise SafetyStop("prior stage receipt entry is malformed")
        receipt_path = Path(str(receipt.get("path", ""))).expanduser()
        if receipt_path.is_symlink() or not receipt_path.is_file() or receipt_path.stat().st_size > 8 * 1024 * 1024:
            raise SafetyStop("prior stage receipt must be a bounded regular private file")
        try:
            receipt_path.resolve().relative_to(REPO_ROOT.resolve())
        except ValueError:
            pass
        else:
            raise SafetyStop("prior stage receipt must remain outside the Git worktree")
        if receipt_path.stat().st_mode & 0o777 != 0o600:
            raise SafetyStop("prior stage receipt must be owner-only (mode 0600)")
        if hashlib.sha256(receipt_path.read_bytes()).hexdigest() != receipt.get("sha256"):
            raise SafetyStop("prior stage receipt hash mismatch")
        try:
            receipt_data = json.loads(receipt_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise SafetyStop("prior stage receipt is unreadable") from exc
        campaign = receipt_data.get("campaign") if isinstance(receipt_data, dict) else None
        if (not isinstance(campaign, dict) or campaign.get("campaign_id") != CAMPAIGN_ID
                or campaign.get("stage_id") != receipt["stage_id"]
                or campaign.get("profile_sha256") != profile_hash
                or campaign.get("source_hashes") != source_hashes()
                or receipt_data.get("stop_result") != "complete"
                or receipt_data.get("adb_serial") != serial):
            raise SafetyStop("prior stage receipt does not prove the same profile, serial and successful stage")
    reviewer = data.get("independent_review")
    if not isinstance(reviewer, dict) or reviewer.get("decision") != "APPROVED":
        raise SafetyStop("qualified independent review is absent or not approved")
    for key in ("reviewer_identity", "reviewer_competence", "artifact_sha256"):
        if not isinstance(reviewer.get(key), str) or not reviewer[key].strip():
            raise SafetyStop(f"independent review is missing {key}")
    if reviewer.get("independence_attested") is not True or reviewer.get("profile_sha256") != profile_hash:
        raise SafetyStop("review independence or exact profile binding is missing")
    if (reviewer.get("source_hashes") != source_hashes() or reviewer.get("stage_id") != stage_id
            or reviewer.get("phase_ids") != STAGE_PHASES[stage_id]):
        raise SafetyStop("review does not bind the exact source hashes and authorized stage")
    reviewed_power = reviewer.get("reviewed_vehicle_power_state")
    owner_power = data.get("owner_confirmed_vehicle_power_state")
    if not isinstance(reviewed_power, str) or not reviewed_power.strip() or owner_power != reviewed_power:
        raise SafetyStop("owner confirmation does not match the exact reviewer-approved PHEV power state")
    artifact_value = review_artifact or Path(str(reviewer.get("artifact_path", ""))).expanduser()
    if not str(artifact_value):
        raise SafetyStop("review artifact path is absent")
    artifact = artifact_value.expanduser()
    try:
        artifact.resolve().relative_to(REPO_ROOT.resolve())
    except ValueError:
        pass
    else:
        raise SafetyStop("independent review artifact must remain outside the Git worktree")
    if artifact.is_symlink() or not artifact.is_file() or artifact.stat().st_size > 8 * 1024 * 1024:
        raise SafetyStop("independent review artifact must be a bounded regular file")
    if artifact.stat().st_mode & 0o777 != 0o600:
        raise SafetyStop("independent review artifact must be owner-only (mode 0600)")
    if hashlib.sha256(artifact.read_bytes()).hexdigest() != reviewer.get("artifact_sha256"):
        raise SafetyStop("independent review artifact hash does not match authorization")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="print fixed manifest without ADB access")
    parser.add_argument("--serial", default="EXACT_APPROVED_SERIAL")
    parser.add_argument("--authorization", type=Path)
    parser.add_argument("--review-artifact", type=Path)
    parser.add_argument("--stage", choices=STAGE_IDS)
    parser.add_argument("--output-root", type=Path, default=Path.home())
    args = parser.parse_args(argv)
    if args.dry_run:
        try:
            print(json.dumps(dry_run_report(args.serial), indent=2, sort_keys=True))
            return 0
        except SafetyStop as exc:
            print(f"Dry run stopped: {exc}", file=sys.stderr)
            return 2
    if args.authorization is None or args.stage is None:
        print("Exact private authorization record and one explicit --stage are required before target access.", file=sys.stderr)
        return 2
    if not LIVE_CAPTURE_ENABLED:
        print("Live root capture is disabled: the SuperSU zero-write and integrity gate remains unresolved.", file=sys.stderr)
        return 2
    try:
        authorization = validate_authorization(args.authorization, stage_id=args.stage,
                                               review_artifact=args.review_artifact)
    except SafetyStop as exc:
        print(f"Authorization stopped before target access: {exc}", file=sys.stderr)
        return 2
    try:
        execute_approved_stage(authorization, args.stage, args.output_root)
        return 0
    except (SafetyStop, OSError) as exc:
        print(f"Stage stopped: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
