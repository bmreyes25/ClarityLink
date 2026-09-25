#!/usr/bin/env python3
"""Take one bounded, read-only Android infotainment snapshot over existing ADB.

Outputs go to the Mac's ignored live-inventory area. Nothing is installed,
started, mounted, or written on the head unit. The operator sets the named
CarPlay/cluster state before each invocation; this tool does not change it.
"""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import subprocess
from pathlib import Path


HERE = Path(__file__).resolve().parent
STATES = (
    "01-disconnected",
    "02-carplay-home",
    "03-apple-maps-open",
    "04-apple-maps-routing",
    "05-route-center-music",
    "06-factory-cluster-navigation",
    "07-hondahack-casting",
    "08-disconnected-again",
)
COMMANDS: dict[str, tuple[str, ...]] = {
    "ps": ("ps",),
    "services": ("service", "list"),
    "packages": ("pm", "list", "packages", "-f"),
    "getprop": ("getprop",),
    "display": ("dumpsys", "display"),
    "window": ("dumpsys", "window"),
    "surfaceflinger": ("dumpsys", "SurfaceFlinger"),
    "activity": ("dumpsys", "activity"),
    "audio": ("dumpsys", "audio"),
    "media-player": ("dumpsys", "media.player"),
    "audio-flinger": ("dumpsys", "media.audio_flinger"),
    "usb": ("dumpsys", "usb"),
    "logcat-tail": ("logcat", "-d", "-t", "300"),
}
PROCESS_NAMES = ("jmcs", "carplay", "externaldisplay", "navigation", "surfaceflinger", "media")


def run(serial: str, remote: tuple[str, ...], timeout: int = 25) -> tuple[int | str, bytes, bytes]:
    try:
        proc = subprocess.run(["adb", "-s", serial, "shell", *remote], capture_output=True, timeout=timeout, check=False)
        return proc.returncode, proc.stdout[:1_000_000], proc.stderr[:100_000]
    except subprocess.TimeoutExpired as exc:
        return "timeout", (exc.stdout or b"")[:1_000_000], (exc.stderr or b"")[:100_000] + b"\nTIMEOUT\n"


def capture(serial: str, state: str, out: Path) -> None:
    if state not in STATES:
        raise ValueError(f"unsupported state: {state}")
    if not serial or any(c.isspace() for c in serial):
        raise ValueError("invalid ADB serial")
    if out.exists():
        raise FileExistsError(out)
    out.mkdir(parents=True)
    manifest: dict[str, object] = {"state": state, "serial": serial, "utc": dt.datetime.now(dt.timezone.utc).isoformat(), "commands": {}}
    ps_output = ""
    for name, remote in COMMANDS.items():
        code, stdout, stderr = run(serial, remote)
        (out / f"{name}.stdout.txt").write_bytes(stdout)
        (out / f"{name}.stderr.txt").write_bytes(stderr)
        manifest["commands"][name] = {"argv": ["adb", "-s", serial, "shell", *remote], "exit": code, "stdout_bytes_saved": len(stdout)}
        if name == "ps":
            ps_output = stdout.decode(errors="replace")
    pids: set[int] = set()
    for line in ps_output.splitlines():
        if not any(name in line.lower() for name in PROCESS_NAMES):
            continue
        fields = line.split()
        if len(fields) >= 2 and re.fullmatch(r"\d+", fields[1]):
            pids.add(int(fields[1]))
    manifest["selected_pids"] = sorted(pids)
    for pid in sorted(pids):
        for leaf in ("cmdline", "status", "maps"):
            code, stdout, stderr = run(serial, ("cat", f"/proc/{pid}/{leaf}"))
            (out / f"proc-{pid}-{leaf}.stdout.txt").write_bytes(stdout)
            (out / f"proc-{pid}-{leaf}.stderr.txt").write_bytes(stderr)
            manifest["commands"][f"proc-{pid}-{leaf}"] = {"exit": code, "stdout_bytes_saved": len(stdout)}
        code, stdout, stderr = run(serial, ("ls", "-l", f"/proc/{pid}/fd"))
        (out / f"proc-{pid}-fd.stdout.txt").write_bytes(stdout)
        (out / f"proc-{pid}-fd.stderr.txt").write_bytes(stderr)
        manifest["commands"][f"proc-{pid}-fd"] = {"exit": code, "stdout_bytes_saved": len(stdout)}
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--serial", required=True)
    ap.add_argument("--state", required=True, choices=STATES)
    ap.add_argument("--session", required=True, help="unique UTC session folder name")
    args = ap.parse_args()
    if not re.fullmatch(r"[0-9]{8}T[0-9]{6}Z", args.session):
        ap.error("session must be YYYYMMDDTHHMMSSZ")
    out = HERE / "live-inventory" / args.session / "runtime" / args.state
    capture(args.serial, args.state, out)
    print(out)


if __name__ == "__main__":
    main()
