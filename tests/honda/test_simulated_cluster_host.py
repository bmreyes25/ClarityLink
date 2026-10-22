"""Deterministic tests for the simulated cluster display host
(CL-FACTORY-02 / P1). Offline, synthetic only. No Android WindowManager, no
Honda IPC, no real display. Synthetic warning priority is NOT proof of real
Honda safety-system behavior.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "claritylink-honda"))

import pytest
import simulated_cluster_host as sch


def _host():
    h = sch.SimulatedClusterHost()
    h.connect_display()
    return h


def test_initial_state_denies_presentation():
    h = sch.SimulatedClusterHost()
    assert h.state is sch.HostState.NOT_INITIALIZED
    assert h.main_presentable() is False
    assert h.present_main(session_id=1, generation=1, content="x") is sch.PresentResult.REJECTED_NO_DISPLAY


def test_connect_then_present_main():
    h = _host()
    assert h.state is sch.HostState.DISPLAY_AVAILABLE
    r = h.present_main(session_id=1, generation=1, content="turn-left")
    assert r is sch.PresentResult.PRESENTED
    assert h.state is sch.HostState.MAIN_CONTENT_ACTIVE
    assert h.main_presentable() is True
    assert h.main_owner == sch.MainOwner(1, 1)
    assert h.main_content == "turn-left"


def test_newer_generation_replaces_main():
    h = _host()
    h.present_main(session_id=1, generation=1, content="a")
    r = h.present_main(session_id=2, generation=2, content="b")
    assert r is sch.PresentResult.REPLACED
    assert h.main_owner == sch.MainOwner(2, 2) and h.main_content == "b"


def test_stale_generation_rejected():
    h = _host()
    h.present_main(session_id=1, generation=5, content="a")
    h.withdraw_main()
    r = h.present_main(session_id=1, generation=4, content="old")
    assert r is sch.PresentResult.REJECTED_STALE_GENERATION
    assert h.main_content is None


def test_same_generation_different_session_rejected():
    h = _host()
    h.present_main(session_id=1, generation=3, content="a")
    r = h.present_main(session_id=2, generation=3, content="hijack")
    assert r is sch.PresentResult.REJECTED_STALE_GENERATION
    assert h.main_owner == sch.MainOwner(1, 3)


# --- interrupt independence ---
def test_interrupt_preempts_and_hides_main():
    h = _host()
    h.present_main(session_id=1, generation=1, content="nav")
    h.activate_interrupt()
    assert h.state is sch.HostState.INTERRUPT_ACTIVE
    assert h.interrupt_active is True
    assert h.main_presentable() is False
    # presenting main during an interrupt is rejected
    assert h.present_main(session_id=1, generation=2, content="nav2") is sch.PresentResult.REJECTED_INTERRUPTED


def test_interrupt_clear_does_not_expose_stale_main():
    h = _host()
    h.present_main(session_id=1, generation=1, content="nav")
    h.activate_interrupt()
    h.clear_interrupt()
    assert h.state is sch.HostState.DISPLAY_AVAILABLE
    assert h.main_presentable() is False      # not auto-restored
    assert h.main_content is None             # stale content gone


def test_repeated_interrupt_activation_is_safe():
    h = _host()
    h.present_main(session_id=1, generation=1, content="nav")
    for _ in range(5):
        h.activate_interrupt()
    assert h.state is sch.HostState.INTERRUPT_ACTIVE
    assert h.stats.interrupts_activated == 1  # idempotent counting
    h.clear_interrupt()
    assert h.interrupt_active is False


def test_interrupt_never_depends_on_main_content():
    # with no main content at all, a critical interrupt still activates
    h = _host()
    h.activate_interrupt()
    assert h.state is sch.HostState.INTERRUPT_ACTIVE and h.interrupt_active is True


# --- display loss / validity-gated restore ---
def test_display_loss_withdraws_and_destroys_ownership():
    h = _host()
    h.present_main(session_id=1, generation=1, content="nav")
    h.lose_display()
    assert h.state is sch.HostState.DISPLAY_LOST
    assert h.main_owner is None and h.main_content is None
    assert h.main_presentable() is False
    # presentation denied while lost
    assert h.present_main(session_id=1, generation=2, content="x") is sch.PresentResult.REJECTED_NO_DISPLAY


def test_invalid_display_refuses_restore():
    h = _host()
    h.lose_display()
    h.begin_restore()
    assert h.state is sch.HostState.RESTORING
    assert h.complete_restore(display_valid=False) is False
    assert h.state is sch.HostState.DISPLAY_LOST
    assert h.stats.restores_refused == 1


def test_valid_display_rebuilds_and_requires_fresh_generation():
    h = _host()
    h.present_main(session_id=1, generation=5, content="nav")
    h.lose_display(); h.begin_restore()
    assert h.complete_restore(display_valid=True) is True
    assert h.state is sch.HostState.DISPLAY_AVAILABLE
    assert h.main_owner is None
    # stale generation cannot reappear after rebuild (lifetime high-water holds)
    assert h.present_main(session_id=1, generation=5, content="replay") is sch.PresentResult.REJECTED_STALE_GENERATION
    assert h.present_main(session_id=2, generation=6, content="fresh") is sch.PresentResult.PRESENTED


def test_interrupt_during_reconnect_does_not_restore_stale_data():
    h = _host()
    h.present_main(session_id=1, generation=1, content="nav")
    h.lose_display()
    h.activate_interrupt()   # interrupt while lost must not resurrect content
    assert h.main_content is None
    h.begin_restore()
    h.complete_restore(display_valid=True)
    assert h.main_content is None and h.main_presentable() is False


def test_close_is_terminal():
    h = _host()
    h.close()
    assert h.state is sch.HostState.CLOSED
    assert h.present_main(session_id=1, generation=1, content="x") is sch.PresentResult.REJECTED_CLOSED
    with pytest.raises(RuntimeError):
        h.connect_display()


def test_clear_host_resets_to_available():
    h = _host()
    h.present_main(session_id=1, generation=1, content="nav")
    h.clear_host()
    assert h.state is sch.HostState.DISPLAY_AVAILABLE
    assert h.main_content is None and h.interrupt_active is False
