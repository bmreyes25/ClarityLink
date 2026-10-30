"""Synthetic producer process for the CL-INT-04 process-boundary tests.

    python3 cl_int_04_producer.py SOCKET MODE

Drives the real ``FailSafeCoordinator`` against a host in ANOTHER process, streams a
few synthetic frames, prints ``STREAMING pid=<pid>``, then behaves per MODE:

  idle      keep the connection open and stay alive, sending nothing (silent producer)
  clean     end orderly through ``coordinator.fault(CARPLAY_ENDED)`` and exit 0
  hold      like idle; the test SIGKILLs this process (unexpected termination)

No Honda, iPhone or vehicle access; content is synthetic text.
"""
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-honda"))

import failsafe_coordinator as fsc  # noqa: E402
from display1_host_ipc import RemoteDisplay1Host  # noqa: E402

FRAMES = 3


def main() -> int:
    path, mode = sys.argv[1], sys.argv[2]
    remote = RemoteDisplay1Host(path)
    coordinator = fsc.FailSafeCoordinator(remote)
    coordinator.phone_attached()
    coordinator.carplay_started()
    if not coordinator.type111_negotiated():
        print("NEGOTIATION_REFUSED", flush=True)
        return 3
    for index in range(FRAMES):
        if coordinator.submit_frame(f"synthetic-frame-{index}") is not fsc.SubmitResult.ACCEPTED:
            print("SUBMIT_REFUSED", flush=True)
            return 4
    print(f"STREAMING pid={os.getpid()}", flush=True)
    if mode == "clean":
        coordinator.fault(fsc.Fault.CARPLAY_ENDED)
        remote.close()
        return 0
    while True:  # idle / hold: alive, silent, no tick(), no heartbeat, no cleanup
        time.sleep(0.5)


if __name__ == "__main__":
    raise SystemExit(main())
