"""Phase F — end-to-end synthetic demonstration (CL-FACTORY-02).

Drives the reusable 16-step demo and asserts a machine-checkable result with
per-step pass/fail and bounded resource stats. Offline, synthetic. The maneuver
updates are explicit test fixtures, NOT decoded Type111 video. safe_for_honda()
is False.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in ("claritylink-transport", "claritylink-negotiation", "claritylink-honda", "claritylink-sim"):
    sys.path.insert(0, str(ROOT / "src" / p))

import cl_factory_02_demo as demo


def test_end_to_end_demo_all_steps_pass():
    result = demo.run_demo()
    # per-step visibility: surface the first failure if any
    failed = [s for s in result["steps"] if not s["ok"]]
    assert not failed, f"failing steps: {failed}"
    assert result["all_ok"] is True
    assert len(result["steps"]) == 16


def test_demo_counts_are_consistent():
    result = demo.run_demo(maneuver_count=5)
    c = result["counts"]
    assert c["nav_accepted"] == 6           # 5 maneuvers + 1 resume
    assert c["stale_rejected"] >= 2         # NOT_OPEN attempt + old-generation replay
    assert c["type110_video_accepted"] == 2
    assert c["withdrawals"] == 1
    assert c["recoveries"] == 1


def test_demo_safety_invariants_hold():
    inv = demo.run_demo()["invariants"]
    assert inv["safe_for_honda"] is False
    assert inv["presentable_to_factory"] is False
    assert inv["pipeline_queue_high_water_bounded"] is True
    assert inv["factory_denied_total"] >= 1


def test_demo_is_deterministic():
    a = demo.run_demo()
    b = demo.run_demo()
    assert a["steps"] == b["steps"] and a["counts"] == b["counts"]
