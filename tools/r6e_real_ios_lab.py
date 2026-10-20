#!/usr/bin/env python3
"""Fail-closed Mac lab entry point. No authentication implementation is bundled."""
from __future__ import annotations

import argparse
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "claritylink-jmcs"))

from claritylink_jmcs.auth_providers import select_provider
from claritylink_jmcs.authentication import AuthenticationError
from claritylink_jmcs.capabilities import SecondaryDisplayCapability
from claritylink_jmcs.identity import load_or_create_identity
from claritylink_jmcs.info import InfoProfile, build_info, validate_info_shape
from claritylink_jmcs.trace import SanitizedTrace

MAX_PROFILE_BYTES = 100_000
FORBIDDEN_ENV = ("HONDA_AUTH_KEY", "MFI_PRIVATE_KEY", "MFI_CERTIFICATE",
                 "PLAYPORT_KEY", "CARPLAY_BYPASS", "HONDA_TARGET")
EVIDENCE_FAMILIES = ("device_identity", "receiver_identity", "display", "screen_modes",
                     "audio", "hid_input", "features", "protocol_versions", "timing",
                     "secondary_display")
ACCEPTED_EVIDENCE = ("CURRENT_IOS_LAB_CONFIRMED", "PUBLIC_DOCUMENTED",
                     "PUBLIC_API_DOCUMENTED", "EXTERNAL_PRIOR_ART")


def load_profile(path: Path, identity_path: Path) -> InfoProfile:
    if path.stat().st_size > MAX_PROFILE_BYTES:
        raise ValueError("profile_too_large")
    data = json.loads(path.read_text(encoding="utf-8"))
    evidence = data.get("evidence", {})
    if any(evidence.get(name) not in ACCEPTED_EVIDENCE for name in EVIDENCE_FAMILIES):
        raise ValueError("info_evidence_incomplete")
    identity = load_or_create_identity(identity_path)
    displays = SecondaryDisplayCapability(main_uuid=identity.main_uuid,
                                          secondary_uuid=identity.secondary_uuid,
                                          **data["secondary_display"])
    hid = []
    for entry in data["hid_devices"]:
        item = dict(entry)
        item["displayUUID"] = identity.main_uuid
        item["hidDescriptor"] = bytes.fromhex(item.pop("hidDescriptorHex"))
        hid.append(item)
    profile = InfoProfile(identity, data["name"], data["model"], data["manufacturer"],
                          data["source_version"], data["feature_bits"],
                          tuple(data["audio_formats"]), tuple(data["audio_latencies"]),
                          tuple(hid), displays)
    shape = validate_info_shape(build_info(profile))
    if shape:
        raise ValueError("info_shape_incomplete")
    return profile


def preflight(args: argparse.Namespace) -> dict[str, object]:
    checks: dict[str, bool] = {}
    checks["no_forbidden_credentials_or_honda_target"] = not any(os.environ.get(name) for name in FORBIDDEN_ENV)
    try:
        address = ipaddress.ip_address(args.bind)
        checks["private_bind"] = address.is_loopback
    except ValueError:
        checks["private_bind"] = False
    checks["trace_redaction"] = isinstance(SanitizedTrace(), SanitizedTrace)
    checks["identity_outside_git"] = args.identity_path.resolve() != Path(__file__).resolve().parents[1] and (
        Path(__file__).resolve().parents[1] not in args.identity_path.resolve().parents)
    checks["info_complete"] = False
    if args.profile and checks["identity_outside_git"]:
        try:
            load_profile(args.profile, args.identity_path)
            checks["info_complete"] = True
        except (OSError, KeyError, TypeError, ValueError):
            pass
    checks["authority_configured"] = args.provider in ("hardware", "authorized_service")
    checks["authority_authorized"] = False
    checks["authority_reachable"] = False
    checks["control_transport_available"] = False
    if checks["authority_configured"]:
        try:
            select_provider(args.provider)
        except AuthenticationError:
            pass
    return {"ready": all(checks.values()), "checks": checks,
            "reason": "R6E_AUTHORITY_NOT_AVAILABLE" if not all(checks.values()) else "READY"}


def main() -> int:
    parser = argparse.ArgumentParser(description="Authorized ClarityLink Mac iPhone lab")
    parser.add_argument("mode", choices=("inventory", "preflight", "authority-check", "serve", "info-only",
                                          "capture-metadata", "shutdown"))
    parser.add_argument("--provider", choices=("hardware", "authorized_service"))
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--identity-path", type=Path,
                        default=Path.home() / ".local/share/claritylink/lab-identity.json")
    parser.add_argument("--bind", default="127.0.0.1")
    args = parser.parse_args()
    if args.mode == "inventory":
        # Only return USB product/vendor identifiers; never retain serial numbers,
        # Bluetooth peers, or unrelated device metadata in stdout or Git.
        try:
            raw = subprocess.run(["system_profiler", "SPUSBDataType", "-json"],
                                 check=True, capture_output=True, text=True, timeout=15)
            data = json.loads(raw.stdout)
            devices = []
            def visit(value: object) -> None:
                if isinstance(value, dict):
                    name = value.get("_name")
                    if isinstance(name, str):
                        devices.append({"name": name[:128],
                                        "vendor_id": value.get("vendor_id"),
                                        "product_id": value.get("product_id")})
                    for child in value.values():
                        visit(child)
                elif isinstance(value, list):
                    for child in value:
                        visit(child)
            visit(data)
            print(json.dumps({"usb_devices": devices}, sort_keys=True))
            return 0
        except (OSError, subprocess.SubprocessError, ValueError, TypeError):
            print(json.dumps({"usb_devices": [], "inventory_error": "usb_inventory_unavailable"}))
            return 1
    result = preflight(args)
    if args.mode == "info-only":
        if not args.profile:
            print(json.dumps({"ready": False, "reason": "profile_required"}))
            return 1
        try:
            profile = load_profile(args.profile, args.identity_path)
            info = build_info(profile)
            print(json.dumps({"ready": True, "required_fields": list(info.keys()),
                              "display_types": [x["type"] for x in info["displays"]],
                              "evidence": "HOST_IMPLEMENTED"}, sort_keys=True))
            return 0
        except (OSError, KeyError, TypeError, ValueError):
            print(json.dumps({"ready": False, "reason": "info_profile_invalid"}))
            return 1
    if args.mode == "shutdown":
        print(json.dumps({"status": "NO_ACTIVE_LAB_SESSION"}))
        return 0
    if args.mode == "authority-check":
        print(json.dumps({k: result["checks"][k] for k in
                          ("authority_configured", "authority_authorized",
                           "authority_reachable", "control_transport_available")}, sort_keys=True))
        return 1
    print(json.dumps({"mode": args.mode, **result}, sort_keys=True))
    return 0 if result["ready"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
