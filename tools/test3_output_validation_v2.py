"""Strict parsers for fixed Test 3 command responses; no ADB access."""

from __future__ import annotations

import re
import argparse
import json
import sys
from pathlib import Path


class OutputRejected(ValueError):
    pass


STAGE_PATH = "/data/local/tmp/clt3-2fdbe11e9f26457b.apk"
LOCAL_APK = str(Path(__file__).resolve().parents[1] /
                "build/test3-admission-probe/clt3-2fdbe11e9f26457b.apk")


def stage_absent(stdout: str, stderr: str, returncode: int, path: str = STAGE_PATH) -> None:
    """Accept only toolbox ls's explicit ENOENT for the one reviewed stage path.

    API17's legacy ADB shell service can return host status zero even when the
    remote command fails, so status alone is never evidence of absence.
    """
    if path != STAGE_PATH:
        raise OutputRejected("stage path is outside the reviewed exact artifact")
    if returncode != 0 or stderr:
        raise OutputRejected("stage inspection transport or stderr is abnormal")
    normalized = stdout.replace("\r", "")
    if normalized.splitlines() != [path + ": No such file or directory"]:
        raise OutputRejected("stage absence is not proven by the exact ENOENT response")


def exact_line(output: str, expected: str) -> None:
    if output.replace("\r", "").splitlines() != [expected]:
        raise OutputRejected(f"expected exactly one {expected!r} line")


def package_absent(path_output: str, list_output: str) -> None:
    if path_output.replace("\r", "").strip() or list_output.replace("\r", "").strip():
        raise OutputRejected("package absence was not proven")


def package_present(path_output: str, package: str) -> str:
    lines = path_output.replace("\r", "").splitlines()
    if len(lines) != 1 or not lines[0].startswith("package:"):
        raise OutputRejected("package path response is malformed or absent")
    path = lines[0][len("package:"):]
    if not path.startswith("/data/app/") or not path.rsplit("/", 1)[-1].startswith(package + "-"):
        raise OutputRejected("package path is outside expected app location")
    return path


def install_succeeded(stdout: str, stderr: str, returncode: int) -> bool:
    lines = stdout.replace("\r", "").splitlines()
    err_lines = stderr.replace("\r", "").splitlines()
    success = [line for line in lines if line == "Success"]
    failure = [line for line in lines if line.startswith("Failure")]
    stage_line = "\tpkg: " + STAGE_PATH
    allowed_out = {"Performing Push Install", stage_line, "Success"}
    if any(line not in allowed_out and not line.startswith("Failure [") for line in lines):
        raise OutputRejected("ADB install output contains an unrecognized line")
    if lines.count(stage_line) != 1 or lines.count("Performing Push Install") != 1:
        raise OutputRejected("ADB install preamble or exact stage path is missing or duplicated")
    progress = re.compile(re.escape(LOCAL_APK) + r": \d+ file pushed, 0 skipped\. [0-9.]+ [KMGT]?B/s \([0-9]+ bytes in [0-9.]+s\)")
    if any(not progress.fullmatch(line) for line in err_lines):
        raise OutputRejected("ADB install stderr is not the pinned push-progress grammar")
    if len(err_lines) > 1:
        raise OutputRejected("ADB install emitted multiple progress lines")
    if len(failure) == 1 and not success:
        return False
    if len(success) == 1 and not failure:
        if returncode != 0:
            raise OutputRejected("ADB install reported Success with nonzero exit")
        return True
    raise OutputRejected("ADB install result is ambiguous")


def uninstall_succeeded(stdout: str, stderr: str, returncode: int) -> None:
    if returncode != 0 or stderr:
        raise OutputRejected("ADB uninstall process failed or wrote stderr")
    if stdout.replace("\r", "").splitlines() != ["Success"]:
        raise OutputRejected("ADB uninstall response is not exactly Success")


def probe_log_delta(
    baseline: str,
    after: str,
    *,
    maximum_bytes: int = 32768,
    expected_uid: int | None = None,
    expected_pid: int | None = None,
    require_public_inventory: bool = False,
) -> dict:
    """Require an unchanged full baseline and parse only newly appended records."""
    if len(baseline.encode("utf-8")) > maximum_bytes or len(after.encode("utf-8")) > maximum_bytes:
        raise OutputRejected("filtered log output exceeds the frozen byte bound")
    baseline = baseline.replace("\r", "")
    after = after.replace("\r", "")
    if not after.startswith(baseline):
        raise OutputRejected("filtered log rotated or baseline changed; freshness is unknown")
    delta = after[len(baseline):]
    tagged = []
    for line in delta.splitlines():
        match = re.fullmatch(r"([VDIWEF])/ClarityLinkTest3Probe\(\s*(\d+)\): (.*)", line)
        if match:
            tagged.append((match.group(1), int(match.group(2)), match.group(3)))
    # The probe implementation emits only Log.i records. Retain, and validate,
    # that provenance instead of normalizing every record to informational.
    if any(priority != "I" for priority, _, _ in tagged):
        raise OutputRejected("probe emitted a non-informational record")
    starts = [(pid, re.fullmatch(r"PROBE_START api=(\d+) uid=(\d+)", message))
              for _, pid, message in tagged if message.startswith("PROBE_START ")]
    completes = [(pid, re.fullmatch(r"PROBE_COMPLETE windows_created=(\d+) surfaces_allocated=(\d+)", message))
                 for _, pid, message in tagged if message.startswith("PROBE_COMPLETE ")]
    if len(starts) != 1 or len(completes) != 1 or starts[0][1] is None or completes[0][1] is None:
        raise OutputRejected("new log suffix lacks one unique start/completion pair")
    start_pid, start_match = starts[0]
    complete_pid, complete_match = completes[0]
    start_index = next(i for i, (_, _, message) in enumerate(tagged) if message.startswith("PROBE_START "))
    complete_index = next(i for i, (_, _, message) in enumerate(tagged) if message.startswith("PROBE_COMPLETE "))
    if (start_index >= complete_index or start_pid != complete_pid or
            start_match.group(1) != "17" or complete_match.groups() != ("0", "0")):
        raise OutputRejected("probe log markers are out of order or violate no-window contract")
    uid = int(start_match.group(2))
    if expected_uid is not None and uid != expected_uid:
        raise OutputRejected("probe UID does not match the installed package UID")
    if expected_pid is not None and start_pid != expected_pid:
        raise OutputRejected("probe PID does not match the installed package process")
    # Accept only records from the PID that emitted the unique start marker.
    pid_records = [(priority, pid, message) for priority, pid, message in tagged if pid == start_pid]
    if any(pid != start_pid for _, pid, _ in tagged):
        raise OutputRejected("probe evidence contains records from a second process")
    records = [f"{priority}/ClarityLinkTest3Probe({pid}): {message}"
               for priority, pid, message in pid_records]
    display_pattern = re.compile(
        r"DISPLAY id=1 name=[^\s]+ type=[^\s]+ valid=true "
        r"size=([1-9][0-9]*)x([1-9][0-9]*) "
        r"refresh_hz=(0|[1-9][0-9]*(?:\.[0-9]+)?) rotation=([0-3])"
    )
    context_pattern = re.compile(
        r"DISPLAY_CONTEXT_CREATED id=1 metrics=([1-9][0-9]*)x([1-9][0-9]*) "
        r"density_dpi=([1-9][0-9]*)"
    )
    target = [(line, display_pattern.fullmatch(line.split(": ", 1)[1])) for line in records
              if " DISPLAY id=1 " in line]
    context = [(line, context_pattern.fullmatch(line.split(": ", 1)[1])) for line in records
               if " DISPLAY_CONTEXT_CREATED id=1 " in line]
    if len(target) != 1 or len(context) != 1:
        raise OutputRejected("probe did not prove exactly one Display 1 and context record")
    if target[0][1] is None or context[0][1] is None:
        raise OutputRejected("Display 1 validity or context metrics are malformed")
    try:
        if float(target[0][1].group(3)) <= 0:
            raise OutputRejected("Display 1 refresh rate must be positive")
    except ValueError as exc:
        raise OutputRejected("Display 1 refresh rate is malformed") from exc
    if require_public_inventory:
        for marker in ("DISPLAY_MANAGER_AVAILABLE", "PRESENTATION_CATEGORY_LIST"):
            if sum(marker in line for line in records) != 1:
                raise OutputRejected(f"probe did not emit exactly one {marker} record")
    if any("_FAILED" in line or "_DENIED" in line or "_UNAVAILABLE" in line
           or "_AMBIGUOUS" in line for line in records):
        raise OutputRejected("probe reported an inventory or access failure")
    return {
        "api": 17,
        "uid": uid,
        "pid": start_pid,
        "display1_visible": True,
        "display1_record": target[0][0],
        "display1_context_created": True,
        "display1_context_record": context[0][0],
        "no_window_or_surface": True,
        "probe_complete": True,
        "probe_records": records,
    }


def _main() -> int:
    parser = argparse.ArgumentParser(description="Validate bounded Test 3 probe log evidence.")
    parser.add_argument("--expected-uid", type=int, required=True)
    parser.add_argument("--expected-pid", type=int, required=True)
    parser.add_argument("--require-public-inventory", action="store_true")
    args = parser.parse_args()
    try:
        result = probe_log_delta("", sys.stdin.read(), expected_uid=args.expected_uid,
                                 expected_pid=args.expected_pid,
                                 require_public_inventory=args.require_public_inventory)
    except OutputRejected as exc:
        print(f"probe evidence rejected: {exc}", file=sys.stderr)
        return 1
    json.dump(result, sys.stdout, sort_keys=True)
    sys.stdout.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
