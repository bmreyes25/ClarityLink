"""Standalone synthetic Display 1 host process (CL-INT-04). Offline lab only.

    python3 display1_host_process.py --socket PATH [--lease-seconds S] [--lab-controls]
                                     [--inject-withdraw-failures N]

Prints ``READY epoch=<n>`` once listening, serves until SIGTERM/SIGINT, then stops
cleanly and prints ``STOPPED clean=<bool>``. The host's lifetime does not depend on
any producer. ``--inject-withdraw-failures`` makes the first N cluster withdrawals
raise so failure reporting can be exercised across the process boundary.
No Honda, vehicle or iPhone access; ``safe_for_honda()`` stays False.
"""
from __future__ import annotations

import argparse
import signal
import sys
import threading
from pathlib import Path

_HERE = str(Path(__file__).resolve().parent)
if _HERE not in sys.path:
    sys.path.insert(0, _HERE)

import failsafe_coordinator as fsc  # noqa: E402
from display1_host_ipc import Display1HostServer  # noqa: E402
from display1_host_service import Display1HostService  # noqa: E402


def _inject_failures(host: fsc.Display1LeaseHost, count: int) -> None:
    real = host._cluster.withdraw_main  # noqa: SLF001 - lab fault injection
    remaining = [count]

    def flaky() -> None:
        if remaining[0] > 0:
            remaining[0] -= 1
            raise OSError("injected withdrawal failure")
        real()

    host._cluster.withdraw_main = flaky  # type: ignore[method-assign]  # noqa: SLF001


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--socket", required=True)
    parser.add_argument("--lease-seconds", type=float, default=fsc.DEFAULT_LEASE_SECONDS)
    parser.add_argument("--lab-controls", action="store_true")
    parser.add_argument("--inject-withdraw-failures", type=int, default=0)
    args = parser.parse_args(argv)

    host = fsc.Display1LeaseHost(lease_seconds=args.lease_seconds)
    host.select_page(True)  # the synthetic Navigation page is selected
    if args.inject_withdraw_failures:
        _inject_failures(host, args.inject_withdraw_failures)
    server = Display1HostServer(Display1HostService(host), args.socket, lab_controls=args.lab_controls)
    stop = threading.Event()
    for signum in (signal.SIGTERM, signal.SIGINT):
        signal.signal(signum, lambda *_: stop.set())
    server.start()
    print(f"READY epoch={host.epoch}", flush=True)
    stop.wait()
    clean = server.stop()
    print(f"STOPPED clean={clean}", flush=True)
    return 0 if clean else 1


if __name__ == "__main__":
    raise SystemExit(main())
