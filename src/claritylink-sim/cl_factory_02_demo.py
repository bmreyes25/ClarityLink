"""End-to-end synthetic navigation-presentation demonstration (CL-FACTORY-02 / F).

Reusable, deterministic driver that exercises the integrated pipeline + simulated
cluster host + an independent Type110 transport gate through the full 16-step
sequence from the campaign brief, and returns a machine-checkable result dict
(per-step pass/fail, accepted/rejected counts, withdrawals, recoveries, bounded
queue high-water, fixture id).

Everything is synthetic and offline: no iPhone, no authentication, no vehicle, no
real Display 1. An "independently generated" maneuver update here is explicitly a
test fixture -- it is NOT derived from real CarPlay Type111 video. Factory output
is never available; ``safe_for_honda()`` stays False.
"""
from __future__ import annotations

import sys
from pathlib import Path

_SRC = Path(__file__).resolve().parents[1]
for _p in ("claritylink-transport", "claritylink-negotiation", "claritylink-honda"):
    _ps = str(_SRC / _p)
    if _ps not in sys.path:
        sys.path.insert(0, _ps)

import frame_gate as fg  # noqa: E402
import lifecycle as lc  # noqa: E402
import cluster_navigation_model as nav  # noqa: E402
import synthetic_navigation_pipeline as snp  # noqa: E402
import simulated_cluster_host as sch  # noqa: E402

FIXTURE_ID = "cl-factory-02-demo/v1"


def run_demo(*, maneuver_count: int = 5) -> dict:
    """Run the 16-step demo deterministically. Returns a result dict."""
    steps: list[dict] = []
    t110_video_accepted = 0
    nav_accepted = 0
    nav_rejected = 0
    stale_rejected = 0
    withdrawals = 0
    recoveries = 0

    def record(n: int, name: str, ok: bool) -> None:
        steps.append({"step": n, "name": name, "ok": bool(ok)})

    def vframe(gen, seq, ts):
        return fg.Frame(generation=gen, sequence=seq, timestamp=ts, payload=b"t110-video")

    # Components
    t110 = fg.FrameGate(capacity=4)                 # Type110 center-display video
    t111 = lc.Type111Lifecycle()                    # Type111 secondary stream lifecycle
    pipe = snp.SyntheticNavigationPipeline(capacity=4)
    host = sch.SimulatedClusterHost()

    # 1) Start a synthetic Type110 stream
    t110.begin_generation(1)
    ok = t110.offer(vframe(1, 0, 0)) is fg.FrameStatus.ACCEPTED
    t110_video_accepted += int(ok)
    record(1, "start_type110", ok and not t110.closed)

    # 2) Start an independent synthetic Type111 session
    gen = t111.prepare(stream_connection_id=0x1001, data_port=42000)
    t111.mark_advertised(); t111.mark_active()
    record(2, "start_type111", t111.state is lc.State.ACTIVE and gen == 1)

    # 3) Open a structured navigation session from a separate synthetic source
    host.connect_display()
    pipe.open_session(session_id=1, generation=1)
    pipe.set_host_available(host.display_available)
    record(3, "open_nav_session",
           pipe.state is snp.PipelineState.ACTIVE and host.state is sch.HostState.DISPLAY_AVAILABLE)

    # 4) Submit several generic maneuver updates (+ 5) host reflects main content)
    man_cycle = [nav.ManeuverType.TURN_LEFT, nav.ManeuverType.STRAIGHT,
                 nav.ManeuverType.TURN_RIGHT, nav.ManeuverType.ROUNDABOUT, nav.ManeuverType.MERGE]
    host_changed = True
    for i in range(maneuver_count):
        out = pipe.submit_update(generation=1, sequence=i, timestamp=i,
                                 maneuver=man_cycle[i % len(man_cycle)], distance=300 - i,
                                 unit=nav.DistanceUnit.METERS, road_name=f"Rd{i}")
        if out.accepted:
            nav_accepted += 1
            # mirror accepted nav content into the simulated host's main layer
            r = host.present_main(session_id=1, generation=1, content=out)
            host_changed = host_changed and r in (sch.PresentResult.PRESENTED, sch.PresentResult.REPLACED)
        else:
            nav_rejected += 1
    record(4, "submit_maneuvers", nav_accepted == maneuver_count)
    record(5, "host_main_content_active",
           host_changed and host.state is sch.HostState.MAIN_CONTENT_ACTIVE and host.main_presentable())

    # 6) Activate a synthetic interrupt
    host.activate_interrupt()
    pipe.on_warning(); withdrawals += 1
    record(6, "activate_interrupt",
           host.state is sch.HostState.INTERRUPT_ACTIVE and pipe.state is snp.PipelineState.INTERRUPTED)

    # 7) Navigation content withdraws
    record(7, "nav_withdrawn",
           host.main_presentable() is False and pipe.presentation_eligibility()[0] is False)

    # 8) Type110 remains unaffected
    ok8 = (not t110.closed) and t110.offer(vframe(1, 1, 1)) is fg.FrameStatus.ACCEPTED
    t110_video_accepted += int(ok8)
    record(8, "type110_unaffected", ok8)

    # 9) Simulate host disappearance
    host.lose_display()
    pipe.on_host_lost()
    record(9, "host_lost",
           host.state is sch.HostState.DISPLAY_LOST and pipe.state is snp.PipelineState.HOST_LOST)

    # 10) Attempt to send stale updates  +  11) verify rejected
    stale = pipe.submit_update(generation=1, sequence=99, timestamp=99,
                               maneuver=nav.ManeuverType.STRAIGHT, distance=1,
                               unit=nav.DistanceUnit.METERS)
    if not stale.accepted:
        nav_rejected += 1; stale_rejected += 1
    record(10, "attempt_stale_update", stale.accepted is False)
    record(11, "stale_rejected", stale.admission is snp.Admission.REJECTED_NOT_OPEN)

    # 12) Recreate the synthetic host
    pipe.begin_recovery(); recoveries += 1
    pipe.restore_factory()
    host.begin_restore()
    rebuilt = host.complete_restore(display_valid=True)
    record(12, "recreate_host", rebuilt and host.state is sch.HostState.DISPLAY_AVAILABLE)

    # 13) Establish a fresh generation (strictly greater; old one unusable)
    reused_blocked = False
    try:
        pipe.open_session(session_id=2, generation=1)
    except ValueError:
        reused_blocked = True
    pipe.open_session(session_id=2, generation=2)
    pipe.set_host_available(host.display_available)
    # an old-generation replay must now be rejected as stale by transport ownership
    replay = pipe.submit_update(generation=1, sequence=0, timestamp=0,
                                maneuver=nav.ManeuverType.STRAIGHT, distance=1,
                                unit=nav.DistanceUnit.METERS)
    if not replay.accepted:
        nav_rejected += 1
        if replay.transport_status is fg.FrameStatus.STALE_GENERATION:
            stale_rejected += 1
    record(13, "fresh_generation",
           reused_blocked and pipe.generation == 2
           and replay.admission is snp.Admission.REJECTED_TRANSPORT)

    # 14) Resume only with valid new data
    out14 = pipe.submit_update(generation=2, sequence=0, timestamp=0,
                               maneuver=nav.ManeuverType.ARRIVE, distance=10,
                               unit=nav.DistanceUnit.METERS, road_name="Dest")
    if out14.accepted:
        nav_accepted += 1
        host.present_main(session_id=2, generation=2, content=out14)
    record(14, "resume_valid",
           out14.accepted and host.main_presentable() and out14.factory_decision.allowed is False)

    # 15) Stop Type111
    t111.teardown()
    pipe.shutdown()
    record(15, "stop_type111",
           t111.state is lc.State.CLOSED and pipe.state is snp.PipelineState.CLOSED)

    # 16) Confirm clean shutdown and resource release
    host.close()
    clean = (pipe.current is None and pipe.generation is None and pipe.queue_depth == 0
             and host.state is sch.HostState.CLOSED and host.main_content is None)
    record(16, "clean_shutdown", clean)

    all_ok = all(s["ok"] for s in steps)
    return {
        "fixture_id": FIXTURE_ID,
        "all_ok": all_ok,
        "steps": steps,
        "counts": {
            "type110_video_accepted": t110_video_accepted,
            "nav_accepted": nav_accepted,
            "nav_rejected": nav_rejected,
            "stale_rejected": stale_rejected,
            "withdrawals": withdrawals,
            "recoveries": recoveries,
        },
        "invariants": {
            "safe_for_honda": pipe.safe_for_honda(),            # always False
            "presentable_to_factory": pipe.presentable_to_factory(),  # always False
            "pipeline_queue_high_water_bounded": pipe.queue_depth <= 1,
            "factory_denied_total": pipe.stats.factory_denied,
        },
    }


if __name__ == "__main__":  # pragma: no cover - manual run convenience
    import json
    print(json.dumps(run_demo(), indent=2))
