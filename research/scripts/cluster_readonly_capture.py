#!/usr/bin/env python3
"""Bounded, Mac-side ADB capture for the parked Clarity; never writes vehicle files."""
import argparse
import datetime as dt
import json
import pathlib
import re
import subprocess
import time

CAPTURE_ROOT = pathlib.Path(__file__).resolve().parent.parent / "captures"
PNG = b"\x89PNG\r\n\x1a\n"


def output_dir(path):
    folder = path.resolve()
    if folder == CAPTURE_ROOT.resolve() or CAPTURE_ROOT.resolve() not in folder.parents:
        raise ValueError("Output must be a child of research/captures")
    return folder


def normalize_png(raw):
    # Android 4.2.2 ADB shell may use a PTY and insert CR before each LF.
    if raw.startswith(PNG):
        return raw
    restored = raw.replace(b"\r\n", b"\n")
    if restored.startswith(PNG):
        return restored
    raise ValueError("screencap output is not a PNG")


def phase_commands(phase):
    if phase == "baseline":
        return [
            ["shell", "getprop"], ["shell", "ps"],
            ["shell", "cat", "/proc/meminfo"],
            ["shell", "dumpsys", "display"],
            ["shell", "dumpsys", "SurfaceFlinger"],
            ["shell", "service", "list"],
        ]
    if phase in ("maps", "music"):
        return [
            ["shell", "screencap", "-d", "0", "-p"],
            ["shell", "screencap", "-d", "1", "-p"],
            ["shell", "dumpsys", "SurfaceFlinger"],
            ["shell", "dumpsys", "display"],
            ["shell", "ps"],
        ]
    if phase == "process-inventory":
        return [["shell", "ps"], ["shell", "cat", "/proc/net/unix"],
                ["shell", "cat", "/proc/net/tcp"]]
    if phase == "capability-survey":
        return [["shell", "cat", "/proc/mounts"],
                ["shell", "cat", "/proc/config.gz"],
                ["shell", "cat", "/proc/modules"],
                ["shell", "ls", "-ld", "/sys/kernel/debug"],
                ["shell", "ls", "-ld", "/sys/kernel/debug/usb/usbmon"],
                ["shell", "ls", "-l", "/sys/kernel/debug/usb/usbmon/0u"],
                ["shell", "test", "-r", "/sys/kernel/debug/usb/usbmon/0u"],
                ["shell", "cat", "/sys/kernel/debug/usb/devices"],
                ["shell", "ls", "-ld", "/sys/kernel/debug/tracing"]]
    if phase == "twin-survey":
        return [["shell", "dumpsys", "display"],
                ["shell", "dumpsys", "SurfaceFlinger"],
                ["shell", "dumpsys", "window"],
                ["shell", "dumpsys", "activity", "activities"],
                ["shell", "dumpsys", "activity", "services"],
                ["shell", "dumpsys", "audio"],
                ["shell", "dumpsys", "media.audio_flinger"],
                ["shell", "dumpsys", "media.player"],
                ["shell", "service", "list"],
                ["shell", "ps"],
                ["shell", "screencap", "-d", "0", "-p"],
                ["shell", "screencap", "-d", "1", "-p"]]
    if phase == "reconnect-log":
        return [["logcat", "-v", "threadtime"]]
    raise ValueError("Unknown phase")


def process_inventory_commands(ps_text):
    """Locate the existing receiver process; generate only /proc reads."""
    for line in ps_text.splitlines():
        fields = line.split()
        if len(fields) >= 3 and fields[-1] == "/system/bin/jmcs" and fields[1].isdigit():
            base = f"/proc/{fields[1]}"
            return [["shell", "cat", base + "/status"],
                    ["shell", "cat", base + "/maps"],
                    ["shell", "ls", "-l", base + "/fd"]]
    return []


def label(command):
    if "screencap" in command:
        return "display-" + command[command.index("-d") + 1] + ".png"
    if command == ["shell", "cat", "/proc/config.gz"]:
        return "kernel-config.gz"
    return "-".join(command[1:]).replace("/", "_") + ".txt"


def capture(serial, folder, phase, duration):
    folder = output_dir(folder)
    folder.mkdir(parents=True, exist_ok=True)
    connection = subprocess.run(["adb", "connect", serial], capture_output=True, text=True, timeout=15)
    state = subprocess.run(["adb", "-s", serial, "get-state"], capture_output=True, text=True, timeout=10)
    if state.returncode or state.stdout.strip() != "device":
        raise RuntimeError("ADB device unavailable: " + state.stderr.strip())
    record = {"phase": phase, "startedUtc": dt.datetime.now(dt.timezone.utc).isoformat(),
              "serial": serial, "connectResult": connection.stdout.strip(), "commands": []}
    phase_folder = folder / phase
    phase_folder.mkdir(exist_ok=True)
    if phase == "reconnect-log":
        target = phase_folder / "logcat.txt"
        with target.open("wb") as output:
            proc = subprocess.Popen(["adb", "-s", serial, "logcat", "-v", "threadtime"],
                                    stdout=output, stderr=subprocess.PIPE)
            try:
                time.sleep(duration)
            finally:
                proc.terminate()
                try:
                    _, error = proc.communicate(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    _, error = proc.communicate(timeout=5)
            record["commands"].append({"argv": ["logcat", "-v", "threadtime"],
                                       "file": "logcat.txt", "bytes": target.stat().st_size,
                                       "stderr": error.decode("utf-8", "replace")[-500:]})
    else:
        queue = phase_commands(phase)
        for command in queue:
            result = subprocess.run(["adb", "-s", serial, *command],
                                    capture_output=True, timeout=20)
            if phase == "process-inventory" and command == ["shell", "ps"] and result.returncode == 0:
                queue.extend(process_inventory_commands(result.stdout.decode("utf-8", "replace")))
            name = label(command)
            item = {"argv": command, "file": name, "exitCode": result.returncode,
                    "stderr": result.stderr.decode("utf-8", "replace")[-500:]}
            if result.returncode == 0:
                try:
                    data = normalize_png(result.stdout) if name.endswith(".png") else result.stdout
                    (phase_folder / name).write_bytes(data)
                    item["bytes"] = len(data)
                except ValueError as error:
                    item["error"] = str(error)
            record["commands"].append(item)
    record["finishedUtc"] = dt.datetime.now(dt.timezone.utc).isoformat()
    (phase_folder / "manifest.json").write_text(json.dumps(record, indent=2) + "\n")
    return record


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--serial", required=True, help="Wirebug adb address, including port")
    parser.add_argument("--output", type=pathlib.Path, required=True)
    parser.add_argument("--phase", choices=("baseline", "reconnect-log", "maps", "music", "process-inventory", "capability-survey", "twin-survey"), required=True)
    parser.add_argument("--duration", type=int, default=120, help="reconnect log seconds, 1..180")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    if not re.fullmatch(r"[A-Za-z0-9.:-]{1,80}", args.serial) or not 1 <= args.duration <= 180:
        parser.error("Invalid serial or duration")
    folder = output_dir(args.output)
    if args.dry_run:
        preview = {"output": str(folder), "phase": args.phase,
                   "adbCommands": phase_commands(args.phase)}
        if args.phase == "process-inventory":
            preview["afterPsIfJmcsFound"] = ["cat /proc/<jmcs-pid>/status",
                                               "cat /proc/<jmcs-pid>/maps",
                                               "ls -l /proc/<jmcs-pid>/fd"]
        print(json.dumps(preview, indent=2))
        return
    result = capture(args.serial, folder, args.phase, args.duration)
    print(json.dumps({"phase": result["phase"], "folder": str(folder / args.phase),
                      "files": [item.get("file") for item in result["commands"]]}, indent=2))


if __name__ == "__main__":
    main()
