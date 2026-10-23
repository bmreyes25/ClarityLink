#!/usr/bin/env python3
"""Offline evidence bookkeeping for the CL-OBS-02 parked camera observation.

Standard library only. It never touches the vehicle, ADB, USB, a network, or the Honda: it lays out a
private evidence directory, seals a raw recording with a SHA-256 digest, re-verifies it, and classifies
a hand-written observation record. It is not a vehicle-control application and does not authorize a
session. Rules are specified in docs/development/cl-obs-02-evidence-acceptance.md.

  init      create the private layout and a manifest template (refuses any path inside a Git work tree)
  seal      hash a recording already in original-recording/, write the integrity manifest, make it read-only
  verify    re-hash the raw recording against the integrity manifest
  classify  classify observation.json -> COMPLETE_EVIDENCE | PARTIAL_EVIDENCE | INCONCLUSIVE | ABORTED |
            RESTORATION_UNVERIFIED | VEHICLE_SESSION_NOT_AUTHORIZED
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
import os
import stat
import subprocess
import sys
import tempfile
from pathlib import Path

SUBDIRS = ("original-recording", "integrity-manifest", "private-observation-notes",
           "redacted-analysis", "sanitized-public-summary")
MAX_RECORDING_SECONDS = 600
MAX_PLAUSIBLE_RECORDING_SECONDS = 86400   # beyond this the value is a data-entry error, not a deviation
GIT_PROBE_TIMEOUT_S = 10

COMPLETE, PARTIAL, INCONCLUSIVE, ABORTED, RESTORATION_UNVERIFIED = (
    "COMPLETE_EVIDENCE", "PARTIAL_EVIDENCE", "INCONCLUSIVE", "ABORTED", "RESTORATION_UNVERIFIED")
NOT_AUTHORIZED = "VEHICLE_SESSION_NOT_AUTHORIZED"

# Step fields. Each must be one of these values; anything else is rejected rather than guessed.
STEP_VALUES = {"OBSERVED", "NOT_OBSERVED", "UNOBSERVABLE", "NOT_REACHED", "NOT_TESTED"}
STEP_FIELDS = (
    "baseline_recorded",          # Q1
    "casting_on_navigation",      # Q2
    "page_exit_result",           # Q3
    "page_reentry_result",        # Q4
    "stop_casting_result",        # Q5
    "center_display_normal",      # Q6
)
RESTORATION_VALUES = {"RESTORED_ON_RECORDING", "RESTORED_DIRECT_SIGHT_ONLY", "NOT_RESTORED_OBSERVED",
                      "NOT_REACHED", "NOT_CASTING_STARTED"}               # Q5, Q7
ANOMALY_VALUES = {"NONE_SEEN", "ANOMALY_SEEN", "UNOBSERVABLE"}            # Q7
GEOMETRY_VALUES = {"MEASURED_SAMPLE", "GEOMETRY_NOT_TESTED", "UNOBSERVABLE"}   # Q8
STOP_REASONS = {"NONE", "WARNING_OR_PROMPT", "CASTING_ON_OTHER_PAGE", "DISPLAY_FROZEN_OR_BLANK",
                "HOST_RESTART", "CAMERA_FAILURE", "TIME_LIMIT", "OPERATOR_UNCERTAINTY", "UNEXPECTED_UI"}
AUTH_FIELDS = ("owner_written_approval", "independent_safety_review", "operator_read_stop_procedure")
BOOL_FIELDS = AUTH_FIELDS + ("recording_legible", "event_timeline_preserved", "integrity_manifest_created")
REQUIRED_FIELDS = (STEP_FIELDS + BOOL_FIELDS + (
    "restoration_result", "stale_crop_overlap_anomaly", "geometry", "session_status", "stop_reason",
    "recording_duration_s"))


class RecordError(ValueError):
    pass


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def _nearest_existing_dir(path: Path) -> Path:
    probe = path
    while not probe.exists():
        if probe.parent == probe:
            raise RecordError("no existing ancestor directory for the private root")
        probe = probe.parent
    return probe if probe.is_dir() else probe.parent


def inside_git_work_tree(path: Path) -> bool:
    """True if path is, or would be created, inside a Git work tree or git dir.

    Fails closed: if Git cannot give a definite answer the caller gets RecordError, never False.
    """
    try:
        probe = _nearest_existing_dir(path.resolve())
    except (OSError, RuntimeError, ValueError) as exc:
        raise RecordError(f"cannot resolve private root: {type(exc).__name__}") from exc
    if any((d / ".git").exists() for d in (probe, *probe.parents)):
        return True
    env = {k: v for k, v in os.environ.items() if not k.startswith("GIT_")}
    env["LC_ALL"] = "C"
    try:
        r = subprocess.run(["git", "-C", str(probe), "rev-parse", "--is-inside-work-tree", "--is-inside-git-dir"],
                           capture_output=True, text=True, env=env, timeout=GIT_PROBE_TIMEOUT_S)
    except (OSError, subprocess.SubprocessError) as exc:
        raise RecordError(f"cannot determine Git state of private root: {type(exc).__name__}") from exc
    if r.returncode == 0:
        answers = r.stdout.split()
        if answers == ["false", "false"]:
            return False
        if answers in (["true", "false"], ["false", "true"], ["true", "true"]):
            return True
    elif r.returncode == 128 and "not a git repository" in r.stderr.lower():
        return False
    raise RecordError("cannot determine Git state of private root; refusing")


def init_layout(root: Path) -> list[str]:
    try:
        root = root.resolve()
    except (OSError, RuntimeError, ValueError) as exc:
        raise RecordError(f"invalid private root: {type(exc).__name__}") from exc
    if inside_git_work_tree(root):
        raise RecordError("refusing: private root is inside a Git work tree")
    for name in SUBDIRS:       # a pre-existing subdirectory may be a symlink into a work tree
        sub_dir = root / name
        if sub_dir.is_symlink() or (sub_dir.exists() and inside_git_work_tree(sub_dir)):
            raise RecordError(f"refusing: {name} is a symlink or inside a Git work tree")
    if not root.exists():
        root.mkdir(parents=True)
        os.chmod(root, 0o700)         # a pre-existing root keeps its owner-chosen permissions
    made = []
    for name in SUBDIRS:
        d = root / name
        d.mkdir(exist_ok=True)
        os.chmod(d, 0o700)
        made.append(name)
    template = root / "private-observation-notes" / "manifest.template.json"
    if template.is_symlink():
        raise RecordError("refusing: manifest.template.json is a symlink")
    if not template.exists():
        template.write_text(json.dumps(manifest_template(), indent=2) + "\n")
    return made


def manifest_template() -> dict:
    return {
        "session_id": "", "session_date": "", "operator_role": "owner/operator", "recorder_role": "second person",
        "recording_format": "", "recording_duration_s": None, "raw_sha256": "",
        "camera": {"model_class": "", "resolution": "", "frame_rate": "", "fixed_mount": None,
                   "exposure_note": "", "focus_note": ""},
        "event_markers": [{"marker": "", "t_relative_s": None}],
        "session_completed_or_stopped": "", "missing_evidence_reason": "", "restoration_result": "",
        "privacy_redaction_status": "RAW_PRIVATE_ONLY",
        "note": "No VIN, phone identifier, GPS, account name or personal data belongs here.",
    }


def seal(root: Path, raw: Path) -> dict:
    if inside_git_work_tree(root):
        raise RecordError("refusing: private root is inside a Git work tree")
    for name in ("original-recording", "integrity-manifest"):
        if (root / name).is_symlink() or not (root / name).is_dir():
            raise RecordError(f"{name} must be a real directory inside the private root")
    if raw.is_symlink():
        raise RecordError("raw recording must not be a symlink")
    raw = raw.resolve()
    if not raw.is_file():
        raise RecordError("raw recording not found")
    if raw.parent != (root / "original-recording").resolve():
        raise RecordError("raw recording must already be in original-recording/")
    out = root / "integrity-manifest" / "raw-sha256.json"
    if out.exists() or out.is_symlink():
        raise RecordError("integrity manifest already exists; refusing to overwrite")
    size = raw.stat().st_size
    if size == 0:
        raise RecordError("raw recording is empty")
    entry = {"file": raw.name, "sha256": sha256_file(raw), "bytes": size}
    fd, tmp_name = tempfile.mkstemp(dir=out.parent, prefix=".raw-sha256-", suffix=".tmp")
    tmp = Path(tmp_name)
    published = False
    raw_mode = stat.S_IMODE(raw.stat().st_mode)
    try:
        with os.fdopen(fd, "w") as f:             # complete manifest first, then publish it atomically
            f.write(json.dumps(entry, indent=2) + "\n")
            f.flush()
            os.fsync(f.fileno())
        os.chmod(tmp, stat.S_IRUSR)
        os.link(tmp, out)                          # fails if out appeared meanwhile: never overwrites
        published = True
        os.chmod(raw, stat.S_IRUSR)
        if sha256_file(raw) != entry["sha256"]:
            raise RecordError("raw recording changed while sealing")
    except BaseException:
        if published:                              # only remove a manifest this call created
            out.unlink(missing_ok=True)
            try:
                os.chmod(raw, raw_mode)
            except OSError:
                pass                               # keep the original error visible
        raise
    finally:
        tmp.unlink(missing_ok=True)
    return entry


def _is_plain_name(name: object) -> bool:
    return isinstance(name, str) and name not in ("", ".", "..") and "\0" not in name \
        and "/" not in name and "\\" not in name and Path(name).name == name


def verify(root: Path) -> tuple[bool, str]:
    mf = root / "integrity-manifest" / "raw-sha256.json"
    if mf.is_symlink() or not mf.is_file():
        return False, "no integrity manifest"
    try:
        entry = _loads(mf.read_text())
        if not isinstance(entry, dict) or not _is_plain_name(entry.get("file")) \
                or not isinstance(entry.get("sha256"), str) or not isinstance(entry.get("bytes"), int) \
                or isinstance(entry.get("bytes"), bool) or entry["bytes"] <= 0:
            return False, "malformed integrity manifest"
        raw = root / "original-recording" / entry["file"]
        if raw.is_symlink() or not raw.is_file():
            return False, "raw recording missing"
        if sha256_file(raw) != entry["sha256"]:
            return False, "digest mismatch"
        if raw.stat().st_size != entry["bytes"]:
            return False, "size mismatch"
        return True, "match"
    except (OSError, ValueError, RecursionError) as exc:
        return False, f"unreadable manifest: {type(exc).__name__}"


def _reject_constant(token: str):
    raise ValueError(f"non-finite JSON number {token} is not allowed")


def _no_duplicate_keys(pairs: list) -> dict:
    keys = [k for k, _ in pairs]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate JSON key")
    return dict(pairs)


def _loads(text: str):
    return json.loads(text, parse_constant=_reject_constant, object_pairs_hook=_no_duplicate_keys)


def _is_number(v: object) -> bool:
    return isinstance(v, (int, float)) and not isinstance(v, bool)


def casting_started(rec: dict) -> bool:
    """Casting counts as started unless the step was never tested or never reached."""
    return rec["casting_on_navigation"] not in ("NOT_TESTED", "NOT_REACHED")


def _check_consistency(rec: dict) -> None:
    if casting_started(rec) == (rec["restoration_result"] == "NOT_CASTING_STARTED"):
        raise RecordError("casting_on_navigation and restoration_result contradict each other "
                          "(NOT_TESTED/NOT_REACHED <-> NOT_CASTING_STARTED)")
    if not casting_started(rec):
        for k in ("page_exit_result", "page_reentry_result", "stop_casting_result"):
            if rec[k] == "OBSERVED":
                raise RecordError(f"{k} cannot be OBSERVED when casting was not tested")
    if (rec["session_status"] == "STOPPED_EARLY") != (rec["stop_reason"] != "NONE"):
        raise RecordError("session_status and stop_reason contradict each other")
    if rec["restoration_result"] == "RESTORED_ON_RECORDING":
        if not rec["recording_legible"]:
            raise RecordError("restoration cannot be 'on recording' when the recording is not legible")
        for k in ("stop_casting_result", "center_display_normal"):
            if rec[k] != "OBSERVED":
                raise RecordError(f"restoration cannot be 'on recording' when {k} is not OBSERVED")


def validate(rec: object) -> None:
    if not isinstance(rec, dict):
        raise RecordError("observation record must be a JSON object")
    missing = [k for k in REQUIRED_FIELDS if k not in rec]
    if missing:
        raise RecordError("missing fields: " + ", ".join(missing))
    unknown = sorted(str(k) for k in rec if k not in REQUIRED_FIELDS)
    if unknown:
        raise RecordError("unexpected fields: " + ", ".join(unknown))
    for k in STEP_FIELDS:
        if not isinstance(rec[k], str) or rec[k] not in STEP_VALUES:
            raise RecordError(f"{k}: invalid value")
    for k in BOOL_FIELDS:
        if not isinstance(rec[k], bool):
            raise RecordError(f"{k}: must be true/false")
    for k, allowed in (("restoration_result", RESTORATION_VALUES), ("stale_crop_overlap_anomaly", ANOMALY_VALUES),
                       ("geometry", GEOMETRY_VALUES), ("stop_reason", STOP_REASONS),
                       ("session_status", {"COMPLETED", "STOPPED_EARLY"})):
        if not isinstance(rec[k], str) or rec[k] not in allowed:
            raise RecordError(f"{k}: invalid value")
    d = rec["recording_duration_s"]
    if not _is_number(d) or (isinstance(d, float) and not math.isfinite(d)) or not 0 <= d <= MAX_PLAUSIBLE_RECORDING_SECONDS:
        raise RecordError(f"recording_duration_s: must be a finite number between 0 and {MAX_PLAUSIBLE_RECORDING_SECONDS}")
    _check_consistency(rec)


def classify(rec: dict, integrity_ok: bool) -> tuple[str, list[str]]:
    """Return (classification, reasons). Order matters: authorization, integrity, restoration, abort."""
    validate(rec)
    why: list[str] = []
    if not all(rec[k] for k in AUTH_FIELDS):
        return NOT_AUTHORIZED, ["missing: " + ", ".join(k for k in AUTH_FIELDS if not rec[k])]
    started = casting_started(rec)   # validate() ties this to restoration_result
    if not integrity_ok:
        if started:
            return RESTORATION_UNVERIFIED, ["raw recording unusable, so restoration is not evidenced"]
        return INCONCLUSIVE, ["raw recording missing, unreadable or failing its SHA-256 check"]
    if started and rec["restoration_result"] != "RESTORED_ON_RECORDING":
        return RESTORATION_UNVERIFIED, ["restoration_result=" + rec["restoration_result"]]
    stopped = rec["session_status"] == "STOPPED_EARLY"
    if stopped:
        return ABORTED, ["stop_reason=" + rec["stop_reason"]]
    if rec["recording_duration_s"] > MAX_RECORDING_SECONDS:
        why.append("recording exceeded the 10-minute limit (protocol deviation)")
    if (rec["baseline_recorded"] != "OBSERVED" or not rec["recording_legible"]
            or not rec["event_timeline_preserved"] or rec["recording_duration_s"] <= 0):
        return INCONCLUSIVE, ["baseline, legibility, event timeline or recording duration missing"]
    if why:
        return PARTIAL, why
    full = (all(rec[k] == "OBSERVED" for k in STEP_FIELDS) and rec["integrity_manifest_created"]
            and rec["restoration_result"] == "RESTORED_ON_RECORDING")
    if full:
        return COMPLETE, ["all planned observations recorded"]
    if rec["casting_on_navigation"] == "OBSERVED":
        return PARTIAL, ["some planned observations unobserved or not reached"]
    return INCONCLUSIVE, ["casting on Navigation not observed"]


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    for name in ("init", "verify", "classify"):
        sub.add_parser(name).add_argument("--root", required=True, type=Path)
    sp = sub.add_parser("seal")
    sp.add_argument("--root", required=True, type=Path)
    sp.add_argument("--raw", required=True, type=Path)
    sub.choices["classify"].add_argument("--record", type=Path, help="default: <root>/private-observation-notes/observation.json")
    a = ap.parse_args(argv)
    try:
        if a.cmd == "init":
            print("created:", ", ".join(init_layout(a.root)))
        elif a.cmd == "seal":
            print(json.dumps(seal(a.root, a.raw)))
        elif a.cmd == "verify":
            ok, msg = verify(a.root)
            print(("VERIFIED: " if ok else "FAILED: ") + msg)
            return 0 if ok else 1
        else:
            rec_path = a.record or a.root / "private-observation-notes" / "observation.json"
            ok, _ = verify(a.root)
            label, reasons = classify(_loads(rec_path.read_text()), ok)
            print(label)
            for r in reasons:
                print(" -", r)
    except (RecordError, OSError, ValueError, RecursionError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
