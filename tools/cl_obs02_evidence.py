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
import os
import stat
import subprocess
import sys
from pathlib import Path

SUBDIRS = ("original-recording", "integrity-manifest", "private-observation-notes",
           "redacted-analysis", "sanitized-public-summary")
MAX_RECORDING_SECONDS = 600

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


def inside_git_work_tree(path: Path) -> bool:
    probe = path
    while not probe.exists():
        probe = probe.parent
    r = subprocess.run(["git", "-C", str(probe), "rev-parse", "--is-inside-work-tree"],
                       capture_output=True, text=True)
    return r.returncode == 0 and r.stdout.strip() == "true"


def init_layout(root: Path) -> list[str]:
    if inside_git_work_tree(root):
        raise RecordError("refusing: private root is inside a Git work tree")
    root.mkdir(parents=True, exist_ok=True)
    os.chmod(root, 0o700)
    made = []
    for name in SUBDIRS:
        d = root / name
        d.mkdir(exist_ok=True)
        os.chmod(d, 0o700)
        made.append(name)
    template = root / "private-observation-notes" / "manifest.template.json"
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
    raw = raw.resolve()
    if not raw.is_file():
        raise RecordError("raw recording not found")
    if raw.parent != (root / "original-recording").resolve():
        raise RecordError("raw recording must already be in original-recording/")
    out = root / "integrity-manifest" / "raw-sha256.json"
    if out.exists():
        raise RecordError("integrity manifest already exists; refusing to overwrite")
    entry = {"file": raw.name, "sha256": sha256_file(raw), "bytes": raw.stat().st_size}
    out.write_text(json.dumps(entry, indent=2) + "\n")
    os.chmod(raw, stat.S_IRUSR)
    return entry


def verify(root: Path) -> tuple[bool, str]:
    mf = root / "integrity-manifest" / "raw-sha256.json"
    if not mf.is_file():
        return False, "no integrity manifest"
    try:
        entry = json.loads(mf.read_text())
        raw = root / "original-recording" / entry["file"]
        if not raw.is_file():
            return False, "raw recording missing"
        match = sha256_file(raw) == entry["sha256"]
        return match, "match" if match else "digest mismatch"
    except (OSError, ValueError, KeyError) as exc:
        return False, f"unreadable manifest: {type(exc).__name__}"


def validate(rec: dict) -> None:
    missing = [k for k in REQUIRED_FIELDS if k not in rec]
    if missing:
        raise RecordError("missing fields: " + ", ".join(missing))
    for k in STEP_FIELDS:
        if rec[k] not in STEP_VALUES:
            raise RecordError(f"{k}: invalid value")
    for k in BOOL_FIELDS:
        if not isinstance(rec[k], bool):
            raise RecordError(f"{k}: must be true/false")
    for k, allowed in (("restoration_result", RESTORATION_VALUES), ("stale_crop_overlap_anomaly", ANOMALY_VALUES),
                       ("geometry", GEOMETRY_VALUES), ("stop_reason", STOP_REASONS),
                       ("session_status", {"COMPLETED", "STOPPED_EARLY"})):
        if rec[k] not in allowed:
            raise RecordError(f"{k}: invalid value")
    if rec["restoration_result"] == "RESTORED_ON_RECORDING" and not rec["recording_legible"]:
        raise RecordError("restoration cannot be 'on recording' when the recording is not legible")
    d = rec["recording_duration_s"]
    if isinstance(d, bool) or not isinstance(d, (int, float)) or d < 0:
        raise RecordError("recording_duration_s: must be a non-negative number")


def classify(rec: dict, integrity_ok: bool) -> tuple[str, list[str]]:
    """Return (classification, reasons). Order matters: authorization, integrity, restoration, abort."""
    validate(rec)
    why: list[str] = []
    if not all(rec[k] for k in AUTH_FIELDS):
        return NOT_AUTHORIZED, ["missing: " + ", ".join(k for k in AUTH_FIELDS if not rec[k])]
    casting_started = rec["casting_on_navigation"] != "NOT_TESTED" and rec["restoration_result"] != "NOT_CASTING_STARTED"
    if not integrity_ok:
        if casting_started:
            return RESTORATION_UNVERIFIED, ["raw recording unusable, so restoration is not evidenced"]
        return INCONCLUSIVE, ["raw recording missing, unreadable or failing its SHA-256 check"]
    if casting_started and rec["restoration_result"] != "RESTORED_ON_RECORDING":
        return RESTORATION_UNVERIFIED, ["restoration_result=" + rec["restoration_result"]]
    stopped = rec["session_status"] == "STOPPED_EARLY" or rec["stop_reason"] != "NONE"
    if stopped:
        return ABORTED, ["stop_reason=" + rec["stop_reason"]]
    if rec["recording_duration_s"] > MAX_RECORDING_SECONDS:
        why.append("recording exceeded the 10-minute limit (protocol deviation)")
    if rec["baseline_recorded"] != "OBSERVED" or not rec["recording_legible"] or not rec["event_timeline_preserved"]:
        return INCONCLUSIVE, ["baseline, legibility or event timeline missing"]
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
            label, reasons = classify(json.loads(rec_path.read_text()), ok)
            print(label)
            for r in reasons:
                print(" -", r)
    except (RecordError, OSError, ValueError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
