"""Print the identity-gated 43T0 delta plan. No command execution exists here."""

import argparse
import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path


CURRENT_TARGET = "<validated-current-target>"
SHELL_ID_SHA256 = "590cc36f1a98082e64e0e2d836c94c125bef1c73fcb7daf981b7286c6b310992"
KERNEL_SHA256 = "8fa1c06d864d3dab9be4c53c13ddecb421516bd02ace3a27ef7811a7ee79c451"
PROPERTIES = (
    ("ro.build.version.release", "4.2.2", "release.raw"),
    ("ro.build.version.sdk", "17", "sdk.raw"),
    ("ro.product.device", "vcm30t30a", "device.raw"),
    ("ro.product.board", "Andromeda", "board.raw"),
    ("ro.hardware", "vcm30t30", "hardware.raw"),
)
NETWORK_READS = (
    (("cat", "/proc/net/dev"), "net-dev.raw"),
    (("cat", "/proc/net/route"), "net-route.raw"),
    (("cat", "/proc/net/ipv6_route"), "ipv6-route.raw"),
    (("cat", "/proc/net/if_inet6"), "if-inet6.raw"),
    (("ifconfig",), "ifconfig.raw"),
)
PHASES = ("baseline", "connected", "post-disconnect")
IDENTITY_KEYS = ("id", "kernel", *(key for key, _, _ in PROPERTIES))


@dataclass(frozen=True)
class IdentityDecision:
    state: str
    reason: str


def _normalized(value: str) -> str:
    return value.rstrip("\r\n")


def assess_identity(
    targets: list[tuple[str, str]] | None,
    human_confirmed: bool,
    historical_endpoint: str,
    results: dict[str, str] | None,
) -> IdentityDecision:
    """Pure model of the required future gate; never talks to a target."""
    if targets is None or results is None:
        return IdentityDecision("IDENTITY_NOT_CHECKED", "missing enumeration or read results")
    if not human_confirmed:
        return IdentityDecision("IDENTITY_INCOMPLETE", "human confirmation absent")
    if len(targets) != 1 or targets[0][1] != "device" or not targets[0][0]:
        return IdentityDecision("IDENTITY_INCOMPLETE", "ambiguous or unavailable ADB target")
    if targets[0][0] != historical_endpoint:
        return IdentityDecision("IDENTITY_MISMATCH", "CURRENT_ENDPOINT_DIFFERS_FROM_40E")
    if any(key not in results or not _normalized(results[key]) for key in IDENTITY_KEYS):
        return IdentityDecision("IDENTITY_INCOMPLETE", "missing identity result")
    shell_id = _normalized(results["id"])
    if not re.match(r"^uid=2000\(shell\)\s+gid=2000\(shell\)(?:\s|$)", shell_id):
        return IdentityDecision("IDENTITY_MISMATCH", "UNEXPECTED_PRIVILEGE")
    if hashlib.sha256(shell_id.encode("utf-8")).hexdigest() != SHELL_ID_SHA256:
        return IdentityDecision("IDENTITY_MISMATCH", "shell group fingerprint mismatch")
    kernel = _normalized(results["kernel"])
    if hashlib.sha256(kernel.encode("utf-8")).hexdigest() != KERNEL_SHA256:
        return IdentityDecision("IDENTITY_MISMATCH", "kernel fingerprint mismatch")
    for key, expected, _ in PROPERTIES:
        if _normalized(results[key]) != expected:
            return IdentityDecision("IDENTITY_MISMATCH", "property mismatch: " + key)
    return IdentityDecision("IDENTITY_MATCH", "all fixed checks matched")


def network_argv(decision: IdentityDecision, endpoint: str) -> tuple[tuple[str, ...], ...]:
    """Expose network argv only after the pure identity model matches."""
    if decision.state != "IDENTITY_MATCH" or not endpoint:
        raise ValueError("network plan requires IDENTITY_MATCH")
    return tuple(
        ("adb", "-s", endpoint, "shell", *command)
        for _phase in PHASES for command, _name in NETWORK_READS
    )


def plan(host_output: Path) -> list[dict[str, object]]:
    """Describe ordered conditional steps using a placeholder, without I/O."""
    rows: list[dict[str, object]] = [
        {"step": "enumerate", "argv": ["adb", "devices"],
         "require": "exactly one intended target in device state; no auto-selection",
         "timeout_seconds": 5, "max_output_bytes": 65536},
        {"step": "human_confirmation", "require": "parked intended Honda head unit"},
    ]
    identity = [
        ("id", ("id",), "id.raw", "uid=2000(shell), gid=2000(shell); sha256:" + SHELL_ID_SHA256),
        ("kernel", ("cat", "/proc/version"), "proc-version.raw", "sha256:" + KERNEL_SHA256),
        *((key, ("getprop", key), name, expected) for key, expected, name in PROPERTIES),
    ]
    for key, command, name, expected in identity:
        rows.append({"step": "identity", "key": key,
                     "argv": ["adb", "-s", CURRENT_TARGET, "shell", *command],
                     "expect": expected, "host_output": str(host_output / "identity" / name),
                     "timeout_seconds": 5, "max_output_bytes": 65536})
    rows.append({"step": "gate", "require": "IDENTITY_MATCH before any network read; endpoint equal to 40E; stop otherwise"})
    rows.append({"step": "host_capture", "manifest": str(host_output / "manifest.json"),
                 "directory_mode": "0700", "location": "Mac only, outside Git"})
    for phase in PHASES:
        for command, name in NETWORK_READS:
            rows.append({"step": "network", "phase": phase, "only_if": "IDENTITY_MATCH",
                         "argv": ["adb", "-s", CURRENT_TARGET, "shell", *command],
                         "host_output": str(host_output / phase / name),
                         "timeout_seconds": 5, "max_output_bytes": 65536})
    return rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", required=True)
    parser.add_argument("--host-output", type=Path, required=True)
    args = parser.parse_args()
    if args.host_output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error("host output must be outside the repository")
    for row in plan(args.host_output):
        print(json.dumps(row, sort_keys=True))


if __name__ == "__main__":
    main()
