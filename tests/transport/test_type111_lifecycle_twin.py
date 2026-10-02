import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path[:0] = [
    str(ROOT / "src/claritylink-transport"),
    str(ROOT / "src/claritylink-negotiation"),
    str(ROOT / "src/carplay-session-model"),
]

from legacy_dual_screen_twin import LegacyDualScreenTwin, LegacyScreenInputError, ScreenRole
from screen_parser import HEADER_SIZE
from dual_screen_lifecycle import DualScreenLifecycleTwin
from project_lifecycle import ChildPhase


MASTER = bytes(range(16))
ID_A, ID_B1, ID_B2 = 101, 201, 202


def encrypt_block(key, counter):
    return bytes(left ^ right for left, right in zip(key, counter))


def packet(body):
    header = bytearray(HEADER_SIZE)
    header[:4] = len(body).to_bytes(4, "little")
    return bytes(header) + body


def state(screen):
    crypto = screen._receiver._crypto
    parser = screen._receiver._parser
    return (
        id(screen),
        id(screen._receiver),
        id(parser),
        id(crypto),
        bytes(crypto._counter),
        crypto._position,
        bytes(parser._buffer),
        parser._pending_header,
        screen._receiver.config,
        screen._receiver._config_pending,
        screen.active,
    )


def make_twin(now=None, lease_seconds=5):
    screens = LegacyDualScreenTwin(MASTER, encrypt_block=encrypt_block, max_body_size=64)
    a = screens.add_screen(ScreenRole.TYPE110, ID_A)
    clock = (lambda: now[0]) if now is not None else None
    kwargs = {"lease_seconds": lease_seconds}
    if clock is not None:
        kwargs["clock"] = clock
    lifecycle = DualScreenLifecycleTwin(screens, **kwargs)
    return screens, lifecycle, a


def make_active_b(lifecycle, stream_id=ID_B1):
    generation = lifecycle.create_type111(stream_id)
    assert generation.activate()
    return generation


def test_create_and_activate_b_without_changing_active_type110():
    _, lifecycle, a = make_twin()
    a.feed(packet(b"A partial parser buffer")[:HEADER_SIZE + 3])
    before = state(a)
    generation = lifecycle.create_type111(ID_B1)
    assert generation.role is ScreenRole.TYPE111_SYNTHETIC
    assert generation.generation == 1
    assert generation.phase is ChildPhase.PREPARED
    assert a.active and a is lifecycle.type110 and lifecycle.type110_generation == 1
    assert state(a) == before
    assert generation.activate()
    assert generation.phase is ChildPhase.ACTIVE
    assert a.active and state(a) == before


def test_exact_b_teardown_and_double_teardown_are_idempotent():
    _, lifecycle, a = make_twin()
    b = make_active_b(lifecycle)
    before = state(a)
    assert b.teardown() is True
    assert b.phase is ChildPhase.STOPPED
    assert b.teardown() is False
    assert lifecycle.current_type111 is None
    assert a.active and state(a) == before
    assert not lifecycle.parent_destroyed


def test_restart_uses_new_generation_and_fresh_screen_and_receiver_state():
    _, lifecycle, a = make_twin()
    b1 = make_active_b(lifecycle)
    a.feed(packet(b"A state"))
    before = state(a)
    b1.feed(packet(b"B1 state"))
    old_state = state(b1._screen)
    old_receiver = b1._screen._receiver
    old_parser = old_receiver._parser
    old_crypto = old_receiver._crypto
    assert b1.teardown()
    b2 = make_active_b(lifecycle, ID_B2)
    assert b2.generation == b1.generation + 1
    assert b1.phase is ChildPhase.STOPPED
    assert b2._screen is not b1._screen
    assert state(b2._screen) != old_state
    assert b2._screen._receiver is not old_receiver
    assert b2._screen._receiver._parser is not old_parser
    assert b2._screen._receiver._crypto is not old_crypto
    assert old_crypto._destroyed
    assert a.active and state(a) == before


def test_new_generation_supersedes_active_old_generation_and_stale_actions_are_noops():
    _, lifecycle, a = make_twin()
    b1 = make_active_b(lifecycle)
    b1_screen = b1._screen
    before_a = state(a)
    b2 = make_active_b(lifecycle, ID_B2)
    assert lifecycle.current_type111 is b2
    assert b1.phase is ChildPhase.STOPPED
    assert not b1.teardown()
    assert not b1.fail()
    assert not b1.activate()
    assert not b1.renew()
    assert b2.phase is ChildPhase.ACTIVE
    assert b2._screen is not b1_screen
    assert a.active and state(a) == before_a


def test_old_generation_lease_ticket_cannot_reap_new_generation():
    now = [0.0]
    _, lifecycle, a = make_twin(now)
    b1 = make_active_b(lifecycle)
    stale_ticket = b1.lease_ticket()
    now[0] = 6.0
    b2 = make_active_b(lifecycle, ID_B2)
    before_a, before_b2 = state(a), state(b2._screen)
    assert lifecycle.reap_lease(stale_ticket, now=100.0) is False
    assert b2.phase is ChildPhase.ACTIVE
    assert state(a) == before_a
    assert state(b2._screen) == before_b2


def test_renewal_invalidates_old_lease_ticket_deterministically():
    now = [0.0]
    _, lifecycle, a = make_twin(now)
    b = make_active_b(lifecycle)
    previous = b.lease_ticket()
    now[0] = 4.0
    assert b.renew()
    renewed = b.lease_ticket()
    assert renewed.revision > previous.revision
    before_a, before_b = state(a), state(b._screen)
    assert lifecycle.reap_lease(previous, now=100.0) is False
    assert b.phase is ChildPhase.ACTIVE
    assert state(a) == before_a and state(b._screen) == before_b
    assert lifecycle.reap_lease(renewed, now=8.0) is False
    assert b.phase is ChildPhase.ACTIVE
    assert lifecycle.reap_lease(renewed, now=9.0) is True
    assert b.phase is ChildPhase.STOPPED
    assert a.active and state(a) == before_a


def test_expired_current_generation_is_reaped_exactly():
    now = [0.0]
    _, lifecycle, a = make_twin(now)
    b = make_active_b(lifecycle)
    before_a = state(a)
    now[0] = 5.0
    assert lifecycle.reap_expired() == (b.generation,)
    assert b.phase is ChildPhase.STOPPED
    assert lifecycle.current_type111 is None
    assert a.active and state(a) == before_a


def test_malformed_b_failure_retires_only_b_and_allows_fresh_restart():
    _, lifecycle, a = make_twin()
    b1 = make_active_b(lifecycle)
    a.feed(packet(b"A remains usable"))
    before_a = state(a)
    malformed = bytearray(HEADER_SIZE)
    malformed[:4] = (65).to_bytes(4, "little")
    with pytest.raises(LegacyScreenInputError, match="synthetic screen input rejected"):
        b1.feed(bytes(malformed))
    assert b1.phase is ChildPhase.STOPPED
    assert a.active and state(a) == before_a
    assert a.feed(packet(b"next A frame"))
    b2 = make_active_b(lifecycle, ID_B2)
    assert b2.generation == b1.generation + 1
    assert b2._screen is not b1._screen
    assert a.active


def test_b_only_teardown_does_not_destroy_parent_or_a_and_parent_destroy_is_explicit():
    _, lifecycle, a = make_twin()
    b = make_active_b(lifecycle)
    assert b.teardown()
    assert a.active and not lifecycle.parent_destroyed
    assert lifecycle.destroy_parent() is True
    assert lifecycle.destroy_parent() is False
    assert lifecycle.parent_destroyed
    assert not a.active


def test_lifecycle_generations_are_separate_across_parent_sessions():
    _, first, a1 = make_twin()
    _, second, a2 = make_twin()
    b1 = make_active_b(first)
    b2 = make_active_b(second)
    assert b1.generation == b2.generation == 1
    assert b1._screen is not b2._screen
    first.destroy_parent()
    assert b1.phase is ChildPhase.STOPPED
    assert b2.phase is ChildPhase.ACTIVE and a2.active
    assert not a1.active


def test_duplicate_id_policy_from_43q_a_remains_fail_closed():
    screens, lifecycle, _ = make_twin()
    with pytest.raises(ValueError, match="unique"):
        lifecycle.create_type111(ID_A)
    assert screens.roles == (ScreenRole.TYPE110,)
    assert lifecycle.current_type111 is None


def test_duplicate_replacement_id_does_not_retire_current_generation():
    _, lifecycle, a = make_twin()
    b1 = make_active_b(lifecycle)
    before_a, before_b = state(a), state(b1._screen)
    with pytest.raises(ValueError, match="fresh stream ID"):
        lifecycle.create_type111(ID_B1)
    assert lifecycle.current_type111 is b1
    assert b1.phase is ChildPhase.ACTIVE
    assert state(a) == before_a and state(b1._screen) == before_b


def test_stale_failure_and_teardown_never_target_current_generation():
    _, lifecycle, a = make_twin()
    b1 = make_active_b(lifecycle)
    b2 = make_active_b(lifecycle, ID_B2)
    before_a, before_b2 = state(a), state(b2._screen)
    assert b1.fail() is False
    assert b1.teardown() is False
    assert lifecycle.current_type111 is b2
    assert b2.phase is ChildPhase.ACTIVE
    assert state(a) == before_a and state(b2._screen) == before_b2


def test_parent_destruction_stops_child_and_type110_only_through_parent_api():
    _, lifecycle, a = make_twin()
    b = make_active_b(lifecycle)
    assert lifecycle.destroy_parent()
    assert b.phase is ChildPhase.STOPPED
    assert not a.active
    assert lifecycle.current_type111 is None
