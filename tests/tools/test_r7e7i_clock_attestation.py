"""Synthetic host fixtures for signature and clock-attestation validation."""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import tempfile

import pytest

from tools import r7e7i_clock_attestation as clock


NOW = dt.datetime(2026, 10, 12, 2, 45, tzinfo=dt.timezone.utc)
HIST_POLICY = "Host UTC is compared against host monotonic elapsed time only to detect a clock step during inspection; monotonic uptime is not wall time. Target /proc/uptime is elapsed time since kernel boot and includes suspend."
INEQ_POLICY = "latest_prior = failure_finished_utc + historical_error; earliest_boot = host_start_utc - current_error - (observed_uptime + 0.01s); termination is established only when earliest_boot - latest_prior > 1.0s."


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


@pytest.fixture(scope="module")
def signing_identity(tmp_path_factory):
    if not shutil.which("gpg") or not shutil.which("gpgv"):
        pytest.skip("GPG tools are required for detached-signature tests")
    home = Path(tempfile.mkdtemp(prefix="gpg-", dir="/tmp"))
    home.chmod(0o700)
    subprocess.run(["gpg", "--batch", "--homedir", str(home), "--passphrase", "",
                    "--quick-generate-key", "Synthetic Clock Reviewer <clock@example.invalid>",
                    "ed25519", "sign", "0"], check=True, capture_output=True)
    listing = subprocess.run(["gpg", "--batch", "--homedir", str(home), "--with-colons",
                             "--list-secret-keys"], check=True, capture_output=True, text=True)
    rows = [line.split(":") for line in listing.stdout.splitlines()]
    fingerprint = next(row[9] for row in rows if row[0] == "fpr")
    keyring = home / "trusted.gpg"
    subprocess.run(["gpg", "--batch", "--homedir", str(home), "--output", str(keyring),
                    "--export", fingerprint], check=True, capture_output=True)
    yield home, fingerprint, keyring
    shutil.rmtree(home, ignore_errors=True)


@pytest.fixture
def signed_fixture(tmp_path, signing_identity):
    home, fingerprint, keyring = signing_identity
    root = tmp_path / "repo"
    (root / "build/r7e6a/test-a/evidence").mkdir(parents=True)
    (root / "build/r7e7g/phase-r/evidence").mkdir(parents=True)
    (root / "tools").mkdir()
    (root / "research/runtime").mkdir(parents=True)
    old = root / "build/r7e6a/test-a/evidence/collector-failure-20261012T021444Z-b64f.json"
    old.write_text(json.dumps({"finished_utc": "2026-10-12T02:14:44.929697+00:00"}))
    phase_r = root / "build/r7e7g/phase-r/evidence/phase-r-20261012T143126461753Z-reviewed.json"
    phase_r.write_text("synthetic phase-r bytes\n")
    collector = root / "tools/r7e7i_phase_s_collector.py"
    collector.write_text("synthetic frozen collector\n")
    validator = root / "tools/r7e7i_clock_attestation.py"
    validator.write_text("synthetic frozen validator\n")
    manifest = root / "research/runtime/r7e7i-phase-s-manifest.json"
    manifest.write_text(json.dumps({"old_failure_finished_utc": "2026-10-12T02:14:44.929697+00:00",
                                    "minimum_historical_error_seconds": 1800}))
    historical_receipt = tmp_path / "historical-source-receipt.json"
    historical_receipt.write_text('{"fixture":"synthetic historical chronology evidence"}\n')
    historical_receipt.chmod(0o600)
    current_receipt = tmp_path / "current-source-receipt.json"
    current_receipt.write_text('{"fixture":"synthetic current clock calibration evidence"}\n')
    current_receipt.chmod(0o600)
    attestation = {
        "schema_version": "R7E7I-CLOCK-ATTESTATION-2",
        "attestation_id": "TEST-ONLY-SYNTHETIC-ATTESTATION",
        "issued_utc": "2026-10-12T02:40:00Z",
        "expires_utc": "2026-10-12T03:00:00Z",
        "bindings": {"historical_evidence_sha256": sha(old), "phase_r_evidence_sha256": sha(phase_r),
                     "collector_sha256": sha(collector), "clock_validation_tool_sha256": sha(validator),
                     "manifest_sha256": sha(manifest)},
        "historical": {"event_finished_utc": "2026-10-12T02:14:44.929697+00:00",
                       "conservative_error_seconds": 1800,
                       "independent_source": "Synthetic CI chronology source",
                       "source_uri": clock.HISTORICAL_SOURCE_URI,
                       "source_timestamp_utc": clock.HISTORICAL_SOURCE_TIME,
                       "source_max_clock_error_seconds": 120,
                       "source_evidence_file": historical_receipt.name,
                       "source_evidence_sha256": sha(historical_receipt),
                       "rationale": "Synthetic test assertion: later independent record brackets event."},
        "current": {"measured_utc": "2026-10-12T02:39:30Z",
                    "conservative_error_seconds": 60,
                    "independent_source": "Synthetic time source",
                    "method": "Synthetic bounded request bracket with declared source accuracy.",
                    "source_uri": "https://time.example.invalid/receipt/1",
                    "source_max_clock_error_seconds": 30,
                    "source_evidence_file": current_receipt.name,
                    "source_evidence_sha256": sha(current_receipt)},
        "monotonic_uptime_policy": HIST_POLICY,
        "inequality_policy": INEQ_POLICY,
        "reviewer": {"name": "Synthetic reviewer", "organization": "Test only",
                     "fingerprint": fingerprint, "reviewed_utc": "2026-10-12T02:39:45Z",
                     "provenance_reference": "synthetic test key; not production reviewer provenance"},
    }
    document = tmp_path / "attestation.json"
    document.write_text(json.dumps(attestation, sort_keys=True, separators=(",", ":")) + "\n")
    document.chmod(0o600)
    signature = tmp_path / "attestation.json.asc"
    subprocess.run(["gpg", "--batch", "--homedir", str(home), "--local-user", fingerprint,
                    "--detach-sign", "--armor", "--output", str(signature), str(document)],
                   check=True, capture_output=True)
    return root, document, signature, keyring, fingerprint, attestation


def test_signed_hash_bound_attestation_passes_validation(signed_fixture):
    root, document, signature, keyring, fingerprint, _ = signed_fixture
    result = clock.validate(document, signature, keyring, fingerprint, now=NOW, root=root)
    assert result["decision"] == "VALID_SIGNED_ATTESTATION"


@pytest.mark.parametrize("change", ["document", "expiry", "bound", "identity", "signature", "receipt"])
def test_mutation_untrusted_identity_or_expiry_is_rejected(signed_fixture, change):
    root, document, signature, keyring, fingerprint, data = signed_fixture
    if change == "document":
        document.write_text(document.read_text() + " ")
    elif change == "expiry":
        data["expires_utc"] = "2026-10-12T02:44:59Z"
        document.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n")
    elif change == "bound":
        data["historical"]["conservative_error_seconds"] = 1300
        document.write_text(json.dumps(data, sort_keys=True, separators=(",", ":")) + "\n")
    elif change == "identity":
        fingerprint = "0" * 40
    elif change == "signature":
        signature.write_text("not a valid signature")
    elif change == "receipt":
        (document.parent / data["current"]["source_evidence_file"]).write_text("changed receipt\n")
    with pytest.raises(clock.AttestationError):
        clock.validate(document, signature, keyring, fingerprint, now=NOW, root=root)


def test_unsigned_old_style_bounds_are_rejected(signed_fixture):
    root, document, signature, keyring, fingerprint, data = signed_fixture
    data.clear()
    data.update({"version": "R7E7I-CLOCK-BOUND-1", "historical_clock_error_seconds": 1800,
                "current_clock_error_seconds": 60})
    document.write_text(json.dumps(data))
    with pytest.raises(clock.AttestationError):
        clock.validate(document, signature, keyring, fingerprint, now=NOW, root=root)
