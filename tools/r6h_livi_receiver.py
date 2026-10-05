#!/usr/bin/env python3
"""Fail-closed Mac receiver side for the pinned LIVI Unix-socket delegate."""
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
import platform
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src" / "claritylink-jmcs"))
sys.path.insert(0, str(ROOT / "tools"))

from claritylink_jmcs.auth_providers.livi import LiviAuthority
from claritylink_jmcs.auth_providers.livi_ipc import LiviUnixSocketBridgeFactory
from claritylink_jmcs.authentication import LabAuthenticationProvider
from claritylink_jmcs.receiver import Receiver
from claritylink_jmcs.session import ReceiverSession
from claritylink_jmcs.trace import SanitizedTrace
from r6e_real_ios_lab import load_profile

FORBIDDEN_ENV = ("HONDA_AUTH_KEY", "MFI_PRIVATE_KEY", "MFI_CERTIFICATE",
                 "PLAYPORT_KEY", "CARPLAY_BYPASS", "HONDA_TARGET")
DEFAULT_IDENTITY = Path.home() / ".local/share/claritylink/lab-identity.json"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("preflight", "serve", "shutdown"))
    parser.add_argument("--profile", type=Path)
    parser.add_argument("--identity-path", type=Path, default=DEFAULT_IDENTITY)
    parser.add_argument("--socket-path", type=Path,
                        default=Path.home() / "Library/Caches/ClarityLink/livi.sock")
    parser.add_argument("--confirm-user-owned-cpc200", action="store_true",
                        help="assert this is the user's separately owned CPC200-CCPA lab unit")
    args = parser.parse_args()
    if args.mode == "shutdown":
        print(json.dumps({"status": "NO_ACTIVE_LAB_SESSION"}))
        return 0
    checks = {
        "macOS_only": platform.system() == "Darwin",
        "no_restricted_environment": not any(os.environ.get(key) for key in FORBIDDEN_ENV),
        "user_owned_unit_confirmed": args.confirm_user_owned_cpc200,
        "cpc200_usb_visible": _cpc200_usb_visible() if platform.system() == "Darwin" else False,
        "profile_present": bool(args.profile and args.profile.is_file()),
        "private_absolute_socket_path": args.socket_path.is_absolute(),
    }
    profile = None
    if checks["profile_present"]:
        try:
            profile = load_profile(args.profile, args.identity_path)
        except (OSError, KeyError, TypeError, ValueError):
            checks["profile_valid"] = False
        else:
            checks["profile_valid"] = True
    else:
        checks["profile_valid"] = False
    ready = all(checks.values())
    if args.mode == "preflight" or not ready:
        print(json.dumps({"ready": ready, "checks": checks,
                          "reason": "ready" if ready else "r6h_preflight_failed"}, sort_keys=True))
        return 0 if ready else 1
    if len(os.fsencode(args.socket_path)) > 103:
        print(json.dumps({"ready": False, "reason": "socket_path_too_long"}))
        return 1

    receiver = Receiver()
    while True:
        factory = LiviUnixSocketBridgeFactory(args.socket_path)
        authority = LiviAuthority(bridge_factory=factory, explicitly_authorized=True)
        provider = LabAuthenticationProvider(authority=authority)
        trace = SanitizedTrace()
        session = ReceiverSession(provider, receiver, profile, trace=trace)
        try:
            session.open()
            print(json.dumps({"status": "AUTHENTICATED_CONTROL_SESSION_OPEN",
                              "generation": session.generation}))
            while True:
                session.handle_one(timeout=30)
                # Trace metadata is allowlisted and contains no peer identifier/body values.
                print(json.dumps(trace.events[-3:], sort_keys=True))
        except KeyboardInterrupt:
            print(json.dumps({"status": "LAB_STOP_REQUESTED"}))
            return 0
        except Exception:
            print(json.dumps({"status": "LAB_SESSION_ENDED",
                              "generation": session.generation,
                              "reason": "bounded_session_failure"}))
        finally:
            session.close()


def _cpc200_usb_visible() -> bool:
    """Read only the USB product label; never retain serials or unrelated IDs."""
    try:
        result = subprocess.run(["system_profiler", "SPUSBDataType", "-json"],
                                check=True, capture_output=True, text=True, timeout=15)
        root = json.loads(result.stdout)
    except (OSError, subprocess.SubprocessError, ValueError):
        return False
    found = False
    def visit(value: object) -> None:
        nonlocal found
        if isinstance(value, dict):
            name = value.get("_name")
            if isinstance(name, str) and "cpc200" in name.casefold():
                found = True
            for child in value.values():
                visit(child)
        elif isinstance(value, list):
            for child in value:
                visit(child)
    visit(root)
    return found


if __name__ == "__main__":
    raise SystemExit(main())
