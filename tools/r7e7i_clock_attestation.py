#!/usr/bin/env python3
"""Offline verifier for independently reviewed R7E7I clock attestations.

This utility verifies signed claims and package/evidence identities. It does
not create attestations, calibrate a clock, contact a source, or authorize S.
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import math
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
MAX_AGE_SECONDS = 86400
MAX_CURRENT_SAMPLE_AGE_SECONDS = 3600
HISTORICAL_SAFETY_SECONDS = 2
HISTORICAL_SOURCE_URI = "https://github.com/bmreyes25/ClarityLink/actions/runs/38196454003"
HISTORICAL_SOURCE_TIME = "2026-10-12T02:36:36Z"


class AttestationError(ValueError):
    pass


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _utc(value: object, label: str) -> dt.datetime:
    if not isinstance(value, str):
        raise AttestationError(f"{label}: expected timestamp")
    try:
        parsed = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise AttestationError(f"{label}: malformed timestamp") from exc
    if parsed.tzinfo is None or parsed.utcoffset() != dt.timedelta(0):
        raise AttestationError(f"{label}: timestamp must be UTC with an offset")
    return parsed.astimezone(dt.timezone.utc)


def _object_bytes(path: Path) -> tuple[bytes, dict[str, object]]:
    if path.is_symlink() or not stat.S_ISREG(path.stat().st_mode):
        raise AttestationError("attestation must be a regular non-symlink file")
    if path.stat().st_mode & 0o777 != 0o600:
        raise AttestationError("attestation must have mode 0600")
    raw = path.read_bytes()

    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise AttestationError("duplicate JSON key")
            obj[key] = value
        return obj

    try:
        value = json.loads(raw, object_pairs_hook=unique)
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise AttestationError("invalid attestation JSON") from exc
    if not isinstance(value, dict):
        raise AttestationError("attestation must be a JSON object")
    return raw, value


def _keys(obj: object, expected: set[str], label: str) -> dict:
    if not isinstance(obj, dict) or set(obj) != expected:
        raise AttestationError(f"{label}: field set does not match schema")
    return obj


def _hash(value: object, label: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[a-f0-9]{64}", value):
        raise AttestationError(f"{label}: invalid SHA-256")
    return value


def _verify_receipt(attestation: Path, filename: object, expected_hash: object, label: str) -> None:
    if (not isinstance(filename, str) or filename in {"", ".", ".."}
            or Path(filename).name != filename or Path(filename).is_absolute()):
        raise AttestationError(f"{label}: receipt must be a sibling file name")
    path = attestation.parent / filename
    digest = _hash(expected_hash, f"{label}.sha256")
    if (path.is_symlink() or not path.is_file() or path.stat().st_mode & 0o777 != 0o600
            or _sha(path) != digest):
        raise AttestationError(f"{label}: source receipt missing, non-private, or hash-mismatched")


def _signature_fingerprint(signature: Path, document: Path, keyring: Path,
                           expected: str, document_bytes: bytes) -> None:
    if any(p.is_symlink() or not p.is_file() for p in (signature, document, keyring)):
        raise AttestationError("signature and trusted keyring must be regular files")
    try:
        signature_bytes = signature.read_bytes()
        with tempfile.TemporaryDirectory(prefix="r7e7i-clock-") as temporary:
            temp_root = Path(temporary)
            signed_doc, detached_sig = temp_root / "attestation.json", temp_root / "attestation.asc"
            signed_doc.write_bytes(document_bytes)
            detached_sig.write_bytes(signature_bytes)
            signed_doc.chmod(0o600)
            detached_sig.chmod(0o600)
            result = subprocess.run(
                ["gpgv", "--status-fd", "1", "--keyring", str(keyring),
                 str(detached_sig), str(signed_doc)], capture_output=True, text=True, check=False,
                timeout=10,
            )
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise AttestationError("offline signature verification failed") from exc
    if document_bytes != document.read_bytes():
        raise AttestationError("attestation changed during signature verification")
    if result.returncode != 0:
        raise AttestationError("detached signature is invalid or untrusted")
    valid_rows = [line.split() for line in result.stdout.splitlines()
                  if line.startswith("[GNUPG:] VALIDSIG ")]
    fingerprints = []
    for row in valid_rows:
        if len(row) < 3:
            raise AttestationError("signature verifier returned malformed identity data")
        # A subkey signature carries the primary-key fingerprint as its last
        # field; a primary-key signature carries only the signing fingerprint.
        fingerprints.append(row[-1] if len(row) > 10 else row[2])
    if len(fingerprints) != 1 or fingerprints[0] != expected.upper():
        raise AttestationError("signature fingerprint does not match trusted reviewer")


def _verify_bindings(bindings: dict, root: Path) -> dict:
    bindings = _keys(bindings, {"historical_evidence_sha256", "phase_r_evidence_sha256",
                               "collector_sha256", "clock_validation_tool_sha256",
                               "manifest_sha256"}, "bindings")
    paths = {
        "historical_evidence_sha256": root / "build/r7e6a/test-a/evidence/collector-failure-20261012T021444Z-b64f.json",
        "phase_r_evidence_sha256": root / "build/r7e7g/phase-r/evidence/phase-r-20261012T143126461753Z-reviewed.json",
        "collector_sha256": root / "tools/r7e7i_phase_s_collector.py",
        "clock_validation_tool_sha256": root / "tools/r7e7i_clock_attestation.py",
        "manifest_sha256": root / "research/runtime/r7e7i-phase-s-manifest.json",
    }
    for key, path in paths.items():
        expected = _hash(bindings[key], f"bindings.{key}")
        if path.is_symlink() or not path.is_file() or _sha(path) != expected:
            raise AttestationError(f"package binding mismatch: {key}")
    return json.loads((root / "research/runtime/r7e7i-phase-s-manifest.json").read_text())


def _verify_historical(attestation_path: Path, historical: dict, manifest: dict) -> int:
    historical = _keys(historical, {"event_finished_utc", "conservative_error_seconds",
        "independent_source", "source_uri", "source_timestamp_utc",
        "source_max_clock_error_seconds", "source_evidence_file",
        "source_evidence_sha256", "rationale"}, "historical")
    event = _utc(historical["event_finished_utc"], "historical.event_finished_utc")
    if historical["event_finished_utc"] != manifest["old_failure_finished_utc"]:
        raise AttestationError("historical event time does not match frozen evidence")
    source_time = _utc(historical["source_timestamp_utc"], "historical.source_timestamp_utc")
    if (historical["source_uri"] != HISTORICAL_SOURCE_URI
            or historical["source_timestamp_utc"] != HISTORICAL_SOURCE_TIME):
        raise AttestationError("historical chronology source does not match reviewed run identity")
    bound, margin = historical["conservative_error_seconds"], historical["source_max_clock_error_seconds"]
    if (type(bound) is not int or type(margin) is not int
            or not 0 <= margin <= MAX_AGE_SECONDS
            or not 0 <= bound <= MAX_AGE_SECONDS or source_time <= event):
        raise AttestationError("invalid historical chronology bounds")
    required = math.ceil((source_time - event).total_seconds() + margin) + HISTORICAL_SAFETY_SECONDS
    if bound < required or bound < manifest["minimum_historical_error_seconds"]:
        raise AttestationError("historical bound is narrower than chronology supports")
    _verify_receipt(attestation_path, historical["source_evidence_file"],
                    historical["source_evidence_sha256"], "historical.source_evidence")
    return bound


def _verify_current(attestation_path: Path, current: dict, issued: dt.datetime,
                    expiry: dt.datetime, current_time: dt.datetime) -> int:
    current = _keys(current, {"measured_utc", "conservative_error_seconds", "independent_source",
        "method", "source_uri", "source_max_clock_error_seconds", "source_evidence_file",
        "source_evidence_sha256"}, "current")
    measured = _utc(current["measured_utc"], "current.measured_utc")
    bound, margin = current["conservative_error_seconds"], current["source_max_clock_error_seconds"]
    _verify_receipt(attestation_path, current["source_evidence_file"],
                    current["source_evidence_sha256"], "current.source_evidence")
    sample_age = (issued - measured).total_seconds()
    if (type(bound) is not int or type(margin) is not int
            or not 0 <= margin <= MAX_AGE_SECONDS or not 0 <= bound <= MAX_AGE_SECONDS
            or bound < margin or sample_age < 0 or sample_age > MAX_CURRENT_SAMPLE_AGE_SECONDS):
        raise AttestationError("current bound does not cover its source uncertainty")
    if (current_time - dt.timedelta(seconds=bound) < issued
            or current_time + dt.timedelta(seconds=bound) > expiry):
        raise AttestationError("attestation validity is uncertain within the current clock bound")
    return bound


def _verify_source_descriptions(historical: dict, current: dict) -> None:
    for section, required in ((historical, ("independent_source", "source_uri", "rationale")),
                              (current, ("independent_source", "method", "source_uri"))):
        if any(not isinstance(section[k], str) or not section[k].strip() for k in required):
            raise AttestationError("clock source description is incomplete")
        if urlparse(section["source_uri"]).scheme != "https":
            raise AttestationError("clock source URI must use HTTPS")


def _verify_policies(top: dict) -> None:
    if top["monotonic_uptime_policy"] != "Host UTC is compared against host monotonic elapsed time only to detect a clock step during inspection; monotonic uptime is not wall time. Target /proc/uptime is elapsed time since kernel boot and includes suspend.":
        raise AttestationError("monotonic uptime interpretation mismatch")
    if top["inequality_policy"] != "latest_prior = failure_finished_utc + historical_error; earliest_boot = host_start_utc - current_error - (observed_uptime + 0.01s); termination is established only when earliest_boot - latest_prior > 1.0s.":
        raise AttestationError("conservative inequality mismatch")


def validate(attestation_path: Path, signature_path: Path, keyring_path: Path,
             trusted_fingerprint: str, now: dt.datetime | None = None,
             root: Path = ROOT) -> dict[str, object]:
    raw, data = _object_bytes(attestation_path)
    top = _keys(data, {"schema_version", "attestation_id", "issued_utc", "expires_utc",
                       "bindings", "historical", "current", "monotonic_uptime_policy",
                       "inequality_policy", "reviewer"}, "attestation")
    if top["schema_version"] != "R7E7I-CLOCK-ATTESTATION-2" or not isinstance(top["attestation_id"], str) or not top["attestation_id"].strip():
        raise AttestationError("unsupported schema or empty attestation id")
    issued, expiry = _utc(top["issued_utc"], "issued_utc"), _utc(top["expires_utc"], "expires_utc")
    current_time = now or dt.datetime.now(dt.timezone.utc)
    if current_time.tzinfo is None:
        raise AttestationError("validator time must be timezone-aware")
    current_time = current_time.astimezone(dt.timezone.utc)
    if expiry <= issued or (expiry - issued).total_seconds() > MAX_AGE_SECONDS:
        raise AttestationError("expiry must be after issue and no more than 24 hours later")

    reviewer = _keys(top["reviewer"], {"name", "organization", "fingerprint", "reviewed_utc", "provenance_reference"}, "reviewer")
    for key in ("name", "organization", "provenance_reference"):
        if not isinstance(reviewer[key], str) or not reviewer[key].strip():
            raise AttestationError(f"reviewer.{key}: required")
    reviewer_time = _utc(reviewer["reviewed_utc"], "reviewer.reviewed_utc")
    if (not isinstance(trusted_fingerprint, str)
            or not re.fullmatch(r"[A-Fa-f0-9]{40,64}", trusted_fingerprint)
            or reviewer_time > issued or reviewer["fingerprint"] != trusted_fingerprint.upper()):
        raise AttestationError("reviewer provenance or trusted fingerprint mismatch")
    _signature_fingerprint(signature_path, attestation_path, keyring_path,
                           trusted_fingerprint.upper(), raw)

    manifest = _verify_bindings(top["bindings"], root)
    historical = top["historical"]
    current = top["current"]
    historical_bound = _verify_historical(attestation_path, historical, manifest)
    current_bound = _verify_current(attestation_path, current, issued, expiry, current_time)
    _verify_source_descriptions(historical, current)
    _verify_policies(top)
    # Read bytes before verifying to prevent accepting a signature over some
    # other file. gpgv is strictly offline and uses only the supplied keyring.
    if not raw:
        raise AttestationError("empty attestation")
    return {"decision": "VALID_SIGNED_ATTESTATION", "attestation_id": top["attestation_id"],
            "reviewer_fingerprint": trusted_fingerprint.upper(), "expires_utc": expiry.isoformat(),
            "historical_error_seconds": historical_bound,
            "current_error_seconds": current_bound}


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("attestation", type=Path)
    p.add_argument("signature", type=Path)
    p.add_argument("--keyring", required=True, type=Path, help="reviewer keyring supplied from a trusted source")
    p.add_argument("--trusted-fingerprint", required=True)
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        print(json.dumps(validate(args.attestation, args.signature, args.keyring,
                                  args.trusted_fingerprint), sort_keys=True))
        return 0
    except (AttestationError, OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print(f"CLOCK_ATTESTATION_REJECTED: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
