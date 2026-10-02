"""Print the proposed 43T0-A delta argv. This program never runs ADB."""

import argparse
import json
from pathlib import Path


READS = (
    ("cat", "/proc/net/dev", "net-dev.raw"),
    ("cat", "/proc/net/route", "net-route.raw"),
    ("cat", "/proc/net/ipv6_route", "ipv6-route.raw"),
    ("cat", "/proc/net/if_inet6", "if-inet6.raw"),
    ("ifconfig", None, "ifconfig.raw"),
)
PHASES = ("baseline", "connected", "post-disconnect")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", required=True)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--host-output", type=Path, required=True)
    args = parser.parse_args()
    manifest = json.loads(args.manifest.read_text())
    if not all(phase in manifest["phase_times"] for phase in PHASES):
        parser.error("40E manifest does not establish all three phases")
    serial = manifest["adb_serial"]
    if not isinstance(serial, str) or not serial or any(c.isspace() for c in serial):
        parser.error("invalid manifest serial")
    if args.host_output.resolve().is_relative_to(Path(__file__).resolve().parents[1]):
        parser.error("host output must be outside the repository")
    for phase in PHASES:
        for executable, path, filename in READS:
            argv = ["adb", "-s", serial, "shell", executable]
            if path:
                argv.append(path)
            print(json.dumps({"phase": phase, "argv": argv,
                              "host_output": str(args.host_output / phase / filename)}))


if __name__ == "__main__":
    main()
