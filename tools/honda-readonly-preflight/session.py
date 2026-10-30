"""Three-phase prompt/finalization controller for one offline-reviewed run."""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass


SUCCESS_MESSAGE = "==============================================\nCAPTURE COMPLETE — YOU CAN TURN THE CAR OFF NOW\n=============================================="
ABORT_MESSAGE = "==============================================\nCAPTURE STOPPED — YOU CAN TURN THE CAR OFF NOW\n=============================================="


@dataclass(frozen=True)
class ObservationPhase:
    key: str
    action: str
    expected: str
    prompt: str


DIAGNOSTIC_PHASES = (
    ObservationPhase("baseline", "Confirm the stationary stock baseline.",
                     "Normal cluster, center display, and audio; phone disconnected.",
                     "PHASE 0 — Park and confirm normal stock behavior. Do not begin if abnormal."),
    ObservationPhase("connected", "Connect the iPhone through the normal USB flow.",
                     "Stock CarPlay appears normally; no ClarityLink or Type111 action.",
                     "PHASE 1 — Connect normally and wait for stock CarPlay."),
    ObservationPhase("navigation_selected", "Select factory Navigation with ordinary controls.",
                     "Navigation page is selected and stable.",
                     "PHASE 2 — Select factory Navigation and observe the cluster."),
    ObservationPhase("navigation_deselected", "Deselect factory Navigation with ordinary controls.",
                     "The factory page changes and prior Navigation content withdraws.",
                     "PHASE 3 — Leave Navigation using ordinary factory controls."),
    ObservationPhase("navigation_reselected", "Reselect factory Navigation with ordinary controls.",
                     "Factory Navigation returns normally.",
                     "PHASE 4 — Reselect Navigation and observe restoration."),
    ObservationPhase("post_disconnect", "Disconnect through the normal phone/user flow.",
                     "CarPlay ends normally and stock display/audio behavior remains normal.",
                     "PHASE 5 — Disconnect normally; do not stop or kill processes."),
    ObservationPhase("restoration", "Verify the phone is disconnected and stock functions are normal.",
                     "Cluster, center display, Navigation, and audio match the baseline.",
                     "PHASE 6 — Verify restoration before closing the approved ADB session."),
)


HONDAHACK_PHASES = (
    ObservationPhase("hondahack_casting_disabled", "Use the existing ordinary Stop Casting control if needed.",
                     "HondaHack casting is disabled; factory display is normal.",
                     "OPTIONAL HH-1 — Confirm existing casting is off using its ordinary UI."),
    ObservationPhase("hondahack_casting_enabled", "Use the existing ordinary Start Casting control.",
                     "Existing casting appears normally; no hooks or modules are changed.",
                     "OPTIONAL HH-2 — Start existing casting using its ordinary UI."),
    ObservationPhase("hondahack_navigation_deselected", "Deselect Navigation with ordinary factory controls.",
                     "Record HondaHack visibility after page withdrawal.",
                     "OPTIONAL HH-3 — Deselect Navigation and observe the cluster."),
    ObservationPhase("hondahack_navigation_reselected", "Reselect Navigation with ordinary factory controls.",
                     "Record HondaHack visibility after Navigation returns.",
                     "OPTIONAL HH-4 — Reselect Navigation and observe the cluster."),
    ObservationPhase("hondahack_casting_stopped", "Use the existing ordinary Stop Casting control.",
                     "Casting stops and factory display is restored.",
                     "OPTIONAL HH-5 — Stop Casting through its ordinary UI and observe restoration."),
)


class SessionStopped(RuntimeError):
    pass


def run_three_phase_session(*, verify_preflight: Callable[[], None],
                            collect_phase: Callable[[str], None],
                            finalize: Callable[[bool], None],
                            input_fn: Callable[[str], str] = input,
                            output_fn: Callable[[str], None] = print) -> bool:
    """Run the reviewed A/B/C human state machine; never hide a failed phase."""
    phases = (
        ("baseline", "PHASE A\nKeep vehicle parked.\nKeep iPhone disconnected.\nPress Enter when ready."),
        ("connected", "PHASE B\nConnect iPhone normally and wait for stock CarPlay.\nOpen Apple Maps on the CENTER DISPLAY.\nDo not start ClarityLink.\nPress Enter when normal CarPlay is ready."),
        ("post-disconnect", "PHASE C\nDisconnect normal CarPlay through the ordinary user flow.\nPress Enter when disconnected."),
    )
    output_fn("OFFLINE PREPARATION COMPLETE.\nVEHICLE SESSION IS NOW REQUIRED.")
    try:
        for index, (phase, prompt) in enumerate(phases):
            input_fn(prompt)
            if index == 0:
                verify_preflight()
            collect_phase(phase)
            if index < 2:
                output_fn(f"PHASE {chr(ord('A') + index)} COMPLETE.")
        finalize(True)
    except (Exception, KeyboardInterrupt, EOFError) as exc:
        try:
            finalize(False)
        except Exception as finalize_error:
            output_fn(f"Host finalization issue recorded: {type(finalize_error).__name__}.")
        output_fn(ABORT_MESSAGE)
        output_fn(f"Capture stopped safely: {type(exc).__name__}.")
        return False
    output_fn(SUCCESS_MESSAGE)
    return True


def run_diagnostic_campaign(*, verify_preflight: Callable[[], None],
                            collect_phase: Callable[[str], None],
                            finalize: Callable[[bool, str | None], None],
                            include_hondahack: bool = False,
                            hondahack_separately_authorized: bool = False,
                            input_fn: Callable[[str], str] = input,
                            output_fn: Callable[[str], None] = print) -> bool:
    """Run fixed human-marked observations; any failure stops without retry or phase continuation."""
    if include_hondahack and not hondahack_separately_authorized:
        output_fn("HondaHack observations require their own separate approval; no phase started.")
        return False
    phases = list(DIAGNOSTIC_PHASES)
    if include_hondahack:
        phases[5:5] = HONDAHACK_PHASES
    completed: list[str] = []
    current = phases[0]
    output_fn("Controller outline only: this function does not authorize live phases or enforce an approval gate.")
    try:
        for index, current in enumerate(phases):
            input_fn(f"{current.prompt}\nExpected: {current.expected}\nPress Enter only when ready.")
            if index == 0:
                verify_preflight()
            collect_phase(current.key)
            completed.append(current.key)
        finalize(True, None)
    except (Exception, KeyboardInterrupt, EOFError) as exc:
        failure = f"{current.key}:{type(exc).__name__}"
        try:
            finalize(False, failure)
        except Exception:
            output_fn("Host finalization also failed; preserve all files already written and stop.")
        output_fn("OWNER DECISION REQUIRED — NO RETRY OR NEXT PHASE WAS STARTED.")
        output_fn(f"Phase: {current.key}")
        output_fn(f"Action attempted: {current.action}")
        output_fn(f"Expected result: {current.expected}")
        output_fn(f"Actual result: stopped ({type(exc).__name__}); details retained in the private manifest when available.")
        output_fn("Risk to stock behavior: assess the cluster, center display, navigation, and audio before any decision.")
        output_fn(f"Evidence preserved: completed phases {completed}; current phase is marked incomplete.")
        output_fn("Possible next actions: stop and close the session, or request a new review for a specific independent phase.")
        output_fn("Recommended safest action: stop the session and preserve current factory behavior.")
        output_fn("Owner decision required: whether to stop or which separately reviewed phase to consider.")
        output_fn(ABORT_MESSAGE)
        return False
    output_fn("PARKED_DIAGNOSTIC_SESSION_COMPLETE — verify restoration before ending the session.")
    output_fn(SUCCESS_MESSAGE)
    return True


def collect_privileged_phase(capture: object, privileged: object, phase: str,
                             expected_identity: object | None = None) -> object:
    """Read the bounded second-session dataset through `PrivilegedRead` only."""
    from collector import SafetyStop, discover_process, parse_task_listing, classify_command_result
    from datetime import datetime, timezone
    from privileged import PrivilegedOperation, decode_config_base64
    import re
    import time

    root_result = privileged.verify_root()
    capture.record_result(phase, "identity", "privileged_root_identity", "privileged_identity",
                          (), *root_result)
    identity = discover_process(privileged, capture=capture, phase=phase, label="initial")
    if expected_identity is not None and (identity.pid, identity.start_time_ticks, identity.executable) != (
            expected_identity.pid, expected_identity.start_time_ticks, expected_identity.executable):
        raise SafetyStop("jmcs process identity changed between session phases")
    capture.phase_identities[phase] = identity
    capture.phase_times[phase] = {"started_utc": datetime.now(timezone.utc).isoformat()}
    pid = identity.pid
    for leaf in ("stat", "status", "cmdline", "limits", "maps", "smaps", "mountinfo",
                 "sched", "schedstat", "oom_score", "oom_score_adj", "cgroup"):
        max_bytes = 32 * 1024 * 1024 if leaf == "smaps" else 4 * 1024 * 1024
        code, raw = capture.store(phase, "process", leaf, "read", f"/proc/{pid}/{leaf}",
                                  timeout=25 if leaf == "smaps" else 10,
                                  max_bytes=max_bytes, pid=pid)
        if leaf == "maps":
            status = classify_command_result(code, raw, b"", operation="read")
            if status.value != "success":
                raise SafetyStop("privileged maps read failed; stopping before CarPlay transitions")
            try:
                from parsers import parse_maps
                mappings = parse_maps(raw.decode("utf-8", "replace"))
            except ValueError as exc:
                raise SafetyStop("privileged maps output could not be parsed") from exc
            if not any(item.pathname.removesuffix(" (deleted)") == "/system/bin/jmcs"
                       and "x" in item.permissions for item in mappings):
                raise SafetyStop("privileged maps do not contain the expected executable jmcs mapping")

    code, fd_listing = capture.store(phase, "process", "fd_links", "list", f"/proc/{pid}/fd",
                                     timeout=10, max_bytes=2 * 1024 * 1024, pid=pid)
    if code == 0:
        fd_ids = set()
        for line in fd_listing.decode("utf-8", "replace").splitlines():
            if "->" not in line:
                continue
            value = line.split("->", 1)[0].split()[-1]
            if value.isdecimal():
                fd_ids.add(int(value))
        fd_ids = sorted(fd_ids)
        for fd in fd_ids:
            capture.store(phase, "process", f"fd_{fd}_target", "readlink",
                          f"/proc/{pid}/fd/{fd}", timeout=5, max_bytes=64 * 1024, pid=pid)

    privileged.verify_root()
    def take_thread_snapshot(index: int) -> None:
        capture.assert_same_instance(identity)
        _, listing = capture.store(phase, "threads", f"snapshot_{index:02d}_task_listing",
                                   "list", f"/proc/{pid}/task", timeout=5,
                                   max_bytes=256 * 1024, pid=pid)
        try:
            tids = parse_task_listing(listing.decode("utf-8", "replace"))
        except ValueError:
            tids = ()
        for tid in tids:
            for leaf in ("status", "stat", "wchan"):
                capture.store(phase, "threads", f"snapshot_{index:02d}_tid_{tid}_{leaf}",
                              "read", f"/proc/{pid}/task/{tid}/{leaf}", timeout=5,
                              max_bytes=256 * 1024, pid=pid)
        capture.assert_same_instance(identity)

    for index in range(3):
        take_thread_snapshot(index)
        if index < 2:
            time.sleep(1.0)
    privileged.verify_root()
    capture.store(phase, "network", "unix", "read", "/proc/net/unix", timeout=10,
                  max_bytes=2 * 1024 * 1024, pid=pid)
    for table in ("tcp", "tcp6", "udp", "udp6"):
        capture.store(phase, "network", table, "read", f"/proc/net/{table}", timeout=10,
                      max_bytes=2 * 1024 * 1024, pid=pid)
    capture.assert_same_instance(identity)
    if phase == "baseline":
        code, encoded, err = privileged.run(PrivilegedOperation.CONFIG_BASE64,
                                            timeout=10, max_bytes=4 * 1024 * 1024)
        try:
            compressed = decode_config_base64(encoded) if code == 0 else None
        except SafetyStop:
            compressed = None
        if compressed is not None:
            capture.record_result(phase, "platform", "proc_config.gz", "config_base64",
                                  ("/proc/config.gz",), code, compressed, err, pid=pid)
        else:
            capture.record_result(phase, "platform", "proc_config_base64", "config_base64",
                                  ("/proc/config.gz",), code, encoded, err, pid=pid)
    capture.phase_times[phase]["finished_utc"] = datetime.now(timezone.utc).isoformat()
    return identity
