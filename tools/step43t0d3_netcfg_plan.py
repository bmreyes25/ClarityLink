"""Non-executing D3 command contract. This module has no device capability."""
from pathlib import Path

VERSION = "43T0-D0-3"
TARGET = "<validated-current-target>"
IDENTITY = (
    ("id", ("shell", "id"), "id.raw"),
    ("kernel", ("shell", "cat", "/proc/version"), "proc-version.raw"),
    ("ro.build.version.release", ("shell", "getprop", "ro.build.version.release"), "release.raw"),
    ("ro.build.version.sdk", ("shell", "getprop", "ro.build.version.sdk"), "sdk.raw"),
    ("ro.product.device", ("shell", "getprop", "ro.product.device"), "device.raw"),
    ("ro.product.board", ("shell", "getprop", "ro.product.board"), "board.raw"),
    ("ro.hardware", ("shell", "getprop", "ro.hardware"), "hardware.raw"),
)
NETWORK = (
    (("shell", "cat", "/proc/net/dev"), "net-dev.raw"),
    (("shell", "cat", "/proc/net/route"), "net-route.raw"),
    (("shell", "cat", "/proc/net/ipv6_route"), "ipv6-route.raw"),
    (("shell", "cat", "/proc/net/if_inet6"), "if-inet6.raw"),
    (("shell", "netcfg"), "netcfg.raw"),
)
PHASES = ("baseline", "connected", "post-disconnect")


def plan(host_output: Path) -> list[dict]:
    rows = [{"step": "enumerate", "argv": ["adb", "devices"], "host_output": str(host_output / "preflight/devices.raw")},
            {"step": "human_confirmation", "require": "parked intended Honda"}]
    rows.extend({"step": "identity", "key": key, "argv": ["adb", "-s", TARGET, *suffix],
                 "host_output": str(host_output / "identity" / filename)}
                for key, suffix, filename in IDENTITY)
    rows.append({"step": "gate", "require": "IDENTITY_MATCH before network reads; historical endpoint equality"})
    for phase in PHASES:
        rows.extend({"step": "network", "phase": phase, "argv": ["adb", "-s", TARGET, *suffix],
                     "host_output": str(host_output / phase / filename)}
                    for suffix, filename in NETWORK)
    return rows
