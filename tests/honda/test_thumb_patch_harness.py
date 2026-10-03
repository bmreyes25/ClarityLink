"""Offline counterexample checks for the two-halfword Thumb patch hazard."""
from pathlib import Path
import ast
import itertools
import sys

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src/claritylink-honda"))
sys.path.insert(0, str(ROOT / "src/claritylink-honda/runtime_safety"))
sys.path.insert(0, str(ROOT / "src/claritylink-honda"))

from thumb_call import decode_thumb_bl, encode_thumb_bl
from runtime_safety.thumb_patch_model import (
    FetchState,
    PatchModelError,
    PatchPhase,
    RendezvousEvidence,
    ThumbCallsitePlan,
    ThumbPatchSimulation,
    assess_rendezvous,
)


HONDA_SETUP = ThumbCallsitePlan(
    address=0x28AF72,
    stock_bytes=bytes.fromhex("fa f7 b5 fa"),
    stock_target=0x2854E0,
    replacement_target=0x290000,
    continuation=0x28AF76,
)


def test_current_honda_callsite_layout_crosses_configured_fetch_group():
    assert HONDA_SETUP.address % 4 == 2
    assert HONDA_SETUP.crosses_fetch_group
    assert HONDA_SETUP.affected_page_span() == (0x28A000, 0x28B000)
    stock = decode_thumb_bl(HONDA_SETUP.address, HONDA_SETUP.stock_bytes)
    replacement = decode_thumb_bl(HONDA_SETUP.address, HONDA_SETUP.replacement_bytes)
    assert (stock.target, stock.return_address) == (0x2854E0, 0x28AF76)
    assert (replacement.target, replacement.return_address) == (0x290000, 0x28AF76)


def test_aligned_safe_looking_site_does_not_remove_two_store_partial_states():
    site = 0x1000
    target = 0x2000
    aligned = ThumbCallsitePlan(
        site, encode_thumb_bl(site, target), target, 0x2100, site + 4
    )
    assert not aligned.crosses_fetch_group
    assert len(aligned.possible_halfword_states()) == 4
    assert any(state not in (aligned.stock_bytes, aligned.replacement_bytes)
               for state in aligned.possible_halfword_states())


@pytest.mark.parametrize("first_half", [0, 1])
def test_first_or_second_halfword_only_exposes_mixed_fetch_state(first_half):
    model = ThumbPatchSimulation(HONDA_SETUP)
    model.begin_patch()
    model.write_patch_halfword(first_half)
    assert model.modeled_fetch_state() is FetchState.MIXED_HALFWORDS
    assert model.current_bytes in HONDA_SETUP.possible_halfword_states()
    with pytest.raises(PatchModelError, match="cache_sync_before_both"):
        model.synchronize_cache(success=True)


@pytest.mark.parametrize("order", list(itertools.permutations((0, 1))))
def test_patch_cache_sync_permission_and_readback_event_order(order):
    model = ThumbPatchSimulation(HONDA_SETUP)
    model.begin_patch()
    for half in order:
        model.write_patch_halfword(half)
    assert model.modeled_fetch_state() is FetchState.REPLACEMENT
    model.synchronize_cache(success=True)
    model.finish_patch()
    assert model.phase is PatchPhase.PATCHED_MODEL_ONLY
    assert model.permission == "RX"
    assert model.ordered_event_check()
    with pytest.raises(PatchModelError, match="never_authorizes"):
        model.authorize_executable_experiment()


def test_interruption_before_cache_flush_can_leave_first_halfword_and_be_restored_in_model():
    model = ThumbPatchSimulation(HONDA_SETUP)
    model.begin_patch()
    model.write_patch_halfword(0)
    model.interrupt()
    assert model.phase is PatchPhase.INTERRUPTED
    assert model.permission == "RW"
    assert model.modeled_fetch_state() is FetchState.MIXED_HALFWORDS
    assert model.begin_restore()
    model.write_restore_halfword(0)
    model.write_restore_halfword(1)
    model.synchronize_cache(success=True, restoring=True)
    model.finish_restore()
    assert model.current_bytes == HONDA_SETUP.stock_bytes
    assert model.phase is PatchPhase.RESTORED_MODEL_ONLY
    assert model.ordered_event_check(restoring=True)


def test_interruption_after_patch_cache_sync_but_before_rx_is_not_execution_authority():
    model = ThumbPatchSimulation(HONDA_SETUP)
    model.begin_patch()
    model.write_patch_halfword(1)
    model.write_patch_halfword(0)
    model.synchronize_cache(success=True)
    model.interrupt()
    assert model.phase is PatchPhase.INTERRUPTED
    assert model.permission == "RW"
    assert model.current_bytes == HONDA_SETUP.replacement_bytes
    assert model.begin_restore()
    model.write_restore_halfword(1)
    model.write_restore_halfword(0)
    model.synchronize_cache(success=True, restoring=True)
    model.finish_restore()
    with pytest.raises(PatchModelError, match="never_authorizes"):
        model.authorize_executable_experiment()


def test_cache_sync_failure_or_interrupted_restore_never_counts_as_restored():
    model = ThumbPatchSimulation(HONDA_SETUP)
    model.begin_patch()
    model.write_patch_halfword(0)
    model.write_patch_halfword(1)
    model.synchronize_cache(success=False)
    assert model.phase is PatchPhase.UNKNOWN
    with pytest.raises(PatchModelError, match="patch_not_cache_synchronized"):
        model.finish_patch()

    assert model.begin_restore()
    model.write_restore_halfword(0)
    model.interrupt()
    assert model.phase is PatchPhase.INTERRUPTED
    assert model.current_bytes != HONDA_SETUP.stock_bytes
    assert model.begin_restore()
    model.write_restore_halfword(0)
    model.write_restore_halfword(1)
    model.synchronize_cache(success=True, restoring=True)
    model.finish_restore()
    assert model.phase is PatchPhase.RESTORED_MODEL_ONLY


def test_restore_is_idempotent_and_foreign_bytes_are_never_overwritten():
    model = ThumbPatchSimulation(HONDA_SETUP)
    assert model.begin_restore() is False
    assert model.begin_restore() is False
    model = ThumbPatchSimulation(HONDA_SETUP)
    model.begin_patch()
    model.write_patch_halfword(0)
    model.write_patch_halfword(1)
    model.synchronize_cache(success=True)
    model.finish_patch()
    model.code[0] ^= 0x01
    before = model.current_bytes
    with pytest.raises(PatchModelError, match="foreign_bytes"):
        model.begin_restore()
    assert model.current_bytes == before


def test_thread_rendezvous_snapshot_flags_active_span_churn_and_unblocked_reentry():
    safe_snapshot = RendezvousEvidence(
        thread_ids_before=(1, 2), thread_ids_after=(1, 2), parked_thread_ids=(1, 2),
        saved_pcs=((1, 0x100), (2, 0x200)), reentry_blocked=True,
    )
    assert assess_rendezvous(safe_snapshot, 0x28AF72, 0x28AF76).acceptable_snapshot
    unsafe_snapshot = RendezvousEvidence(
        thread_ids_before=(1, 2), thread_ids_after=(1, 2, 3), parked_thread_ids=(1,),
        saved_pcs=((1, 0x28AF74), (2, 0x200)), reentry_blocked=False,
    )
    result = assess_rendezvous(unsafe_snapshot, 0x28AF72, 0x28AF76)
    assert not result.acceptable_snapshot
    assert set(result.failures) == {
        "thread_set_changed", "not_every_thread_parked", "saved_pc_inside_patch_span",
        "reentry_not_blocked",
    }


def test_harness_imports_no_process_or_device_io_backend():
    source = (ROOT / "src/claritylink-honda/runtime_safety/thumb_patch_model.py").read_text()
    tree = ast.parse(source)
    imported_roots = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported_roots.update(alias.name.split(".")[0] for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported_roots.add(node.module.split(".")[0])
    assert not imported_roots.intersection({"os", "ctypes", "socket", "subprocess", "ptrace", "adb"})
