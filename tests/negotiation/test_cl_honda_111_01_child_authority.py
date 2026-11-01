"""CL-HONDA-111-01: parent-owned Type111 child authority (synthetic only).

These tests prove the consumer-side contract in the receiver architecture
document. They do not prove anything about the real Honda receiver, which has
no such provider. ``safeForHonda()`` stays false.
"""
import pickle
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src" / "claritylink-negotiation"))

import type111_child_authority as tca  # noqa: E402


def _parent(**kw):
    return tca.ParentAuthority(**kw)


def _open(parent, sid=0x1111):
    return parent.open_child(parent.grant_child(sid))


# --- construction fails closed ---
def test_non_synthetic_parent_cannot_be_built():
    with pytest.raises(tca.AuthorityError) as e:
        tca.ParentAuthority(synthetic=False)
    assert e.value.code == "attestation_unavailable"


@pytest.mark.parametrize("kw", [dict(parent_id=0), dict(generation=0), dict(parent_id=True),
                                dict(generation=-1), dict(generation="1")])
def test_invalid_parent_identity_rejected(kw):
    with pytest.raises(tca.AuthorityError) as e:
        tca.ParentAuthority(**kw)
    assert e.value.code == "invalid_parent_identity"


def test_synthetic_flag_is_always_true_and_visible():
    p = _parent()
    assert p.synthetic is True
    assert "synthetic=True" in repr(p)


# --- grant and open ---
@pytest.mark.parametrize("bad", [0, -1, 1 << 64, True, "7", None, 1.5])
def test_invalid_stream_connection_id_denied(bad):
    with pytest.raises(tca.AuthorityError) as e:
        _parent().grant_child(bad)
    assert e.value.code == "invalid_stream_connection_id"


def test_grant_opens_exactly_one_child():
    p = _parent()
    g = p.grant_child(0xABCDEF)
    c = p.open_child(g)
    assert c.live and c.state is tca.ChildState.OPEN
    assert c.identity.stream_connection_id == 0xABCDEF
    with pytest.raises(tca.AuthorityError) as e:
        p.open_child(g)
    assert e.value.code == "grant_consumed"


def test_second_grant_denied_while_child_live():
    p = _parent()
    _open(p, 5)
    with pytest.raises(tca.AuthorityError) as e:
        p.grant_child(6)
    assert e.value.code == "child_already_live"


def test_second_grant_denied_while_one_is_outstanding():
    p = _parent()
    p.grant_child(5)
    with pytest.raises(tca.AuthorityError) as e:
        p.grant_child(6)
    assert e.value.code == "grant_outstanding"


def test_grant_from_another_parent_is_refused():
    a, b = _parent(), _parent()
    g = a.grant_child(9)
    with pytest.raises(tca.AuthorityError) as e:
        b.open_child(g)
    assert e.value.code == "foreign_grant"


def test_non_grant_object_is_refused():
    with pytest.raises(tca.AuthorityError) as e:
        _parent().open_child(object())
    assert e.value.code == "foreign_grant"


def test_stream_generation_is_lifetime_monotonic_across_children():
    p = _parent()
    gens = []
    for sid in (3, 3, 4, 3):
        c = _open(p, sid)
        gens.append(c.identity.stream_generation)
        c.close()
    assert gens == sorted(set(gens)) and len(gens) == 4


def test_stream_id_reuse_after_close_gets_a_fresh_generation():
    p = _parent()
    c1 = _open(p, 77)
    g1 = c1.identity.stream_generation
    c1.close()
    c2 = _open(p, 77)
    assert c2.identity.stream_generation > g1


# --- parent loss ---
def test_parent_loss_revokes_child_and_runs_callbacks_once():
    p = _parent()
    c = _open(p)
    seen = []
    c.add_end_callback(seen.append)
    p.lose()
    p.lose()   # idempotent
    assert c.state is tca.ChildState.REVOKED and not c.live
    assert seen == ["parent_lost"]


def test_parent_loss_blocks_new_grants_and_opening_an_old_grant():
    p = _parent()
    g = p.grant_child(8)
    p.lose()
    with pytest.raises(tca.AuthorityError) as e:
        p.open_child(g)
    assert e.value.code == "parent_lost"
    with pytest.raises(tca.AuthorityError) as e:
        p.grant_child(8)
    assert e.value.code == "parent_lost"


def test_child_never_outlives_parent_even_if_state_flag_is_stale():
    p = _parent()
    c = _open(p)
    p.lose()
    assert c.live is False


def test_late_end_callback_runs_immediately_with_the_end_reason():
    p = _parent()
    c = _open(p)
    c.close()
    seen = []
    c.add_end_callback(seen.append)
    assert seen == ["CLOSED"]


def test_raising_callback_is_contained_and_others_still_run():
    p = _parent()
    c = _open(p)
    seen = []

    def boom(_reason):
        raise RuntimeError("consumer bug")
    c.add_end_callback(boom)
    c.add_end_callback(seen.append)
    p.lose()
    assert seen == ["parent_lost"]


def test_callback_count_is_bounded():
    c = _open(_parent())
    for _ in range(tca.MAX_REVOKE_CALLBACKS):
        c.add_end_callback(lambda _r: None)
    with pytest.raises(tca.AuthorityError) as e:
        c.add_end_callback(lambda _r: None)
    assert e.value.code == "too_many_end_callbacks"


def test_close_is_idempotent_and_frees_the_parent_slot():
    p = _parent()
    c = _open(p, 10)
    c.close()
    c.close()
    assert p.live_child is None
    assert _open(p, 11).live


# --- secrecy / serialization ---
def test_child_and_grant_hold_no_secret_material_and_do_not_serialize():
    p = _parent()
    g = p.grant_child(0xDEADBEEF)
    assert "redacted" in repr(g) and "3735928559" not in repr(g) and "deadbeef" not in repr(g).lower()
    with pytest.raises(TypeError):
        pickle.dumps(g)
    c = p.open_child(g)
    assert "3735928559" not in repr(c)
    with pytest.raises(TypeError):
        pickle.dumps(c)
    names = {n.lower() for n in dir(c)}
    assert not any(token in names for token in ("key", "secret", "master", "iv", "socket", "fd"))


def test_child_authority_names_no_type110_state():
    c = _open(_parent())
    assert not any("110" in n or "primary" in n.lower() for n in dir(c))
