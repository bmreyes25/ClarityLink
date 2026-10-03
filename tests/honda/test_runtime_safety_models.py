import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "claritylink-honda"))

import page_model
import veneer_ranges
import veneer_allocator_model
import rendezvous_model
import pytest
import runtime_safety_model as safety


def test_page_cover_one_and_crossing_pages():
    assert page_model.page_cover(0x1003, 4, 4096) == page_model.PageRange(0x1000, 0x2000)
    assert page_model.page_cover(0x1fff, 2, 4096) == page_model.PageRange(0x1000, 0x3000)


def test_page_cover_supports_non_power_of_two_granule_model():
    assert page_model.page_cover(4999, 2, 5000) == page_model.PageRange(0, 10000)


@pytest.mark.parametrize("address,length,page_size", [
    (0, 0, 4096), (0, 1, 0), (0, 1, -1), (-1, 1, 4096),
    (1 << 32, 1, 4096), ((1 << 32) - 1, 2, 4096),
])
def test_page_cover_rejects_invalid_or_overflow(address, length, page_size):
    with pytest.raises((ValueError, OverflowError)):
        page_model.page_cover(address, length, page_size)


def test_page_cover_allows_exclusive_arm32_limit_when_aligned():
    result = page_model.page_cover((1 << 32) - 4096, 4096, 4096)
    assert result == page_model.PageRange((1 << 32) - 4096, 1 << 32)


def test_permission_model_enforces_wx_and_rx_rw_rx_order():
    model = page_model.PermissionModel()
    model.patch_window()
    assert model.protection == "RW"
    model.finish_patch()
    assert model.protection == "RX"
    with pytest.raises(ValueError):
        model.set("RWX")


def test_thumb_ranges_and_common_intersection():
    info = veneer_ranges.thumb_bl_reach(0x28A158)
    setup = veneer_ranges.thumb_bl_reach(0x28AF72)
    assert (info.start, info.end) == (0, 0x128A15A)
    assert (setup.start, setup.end) == (0, 0x128AF74)
    assert veneer_ranges.common_reach((0x28A158, 0x28AF72)) == veneer_ranges.Reach(0, 0x128A15A)


def test_setup_patch_crosses_four_byte_fetch_group():
    callsite = 0x28AF72
    assert callsite % 4 == 2
    assert (callsite // 4) != ((callsite + 3) // 4)


def test_snapshot_allocator_selects_synthetic_near_gap():
    candidate = veneer_allocator_model.choose_snapshot_gap(
        veneer_ranges.Reach(0x1000, 0x8fff),
        (veneer_allocator_model.Mapping(0x1000, 0x3000),
         veneer_allocator_model.Mapping(0x5000, 0x7000)),
        allocation_size=0x1000, page_size=0x1000)
    assert candidate == page_model.PageRange(0x3000, 0x4000)


def test_snapshot_allocator_fails_if_no_gap_fits_in_reach():
    with pytest.raises(ValueError):
        veneer_allocator_model.choose_snapshot_gap(
            veneer_ranges.Reach(0x1000, 0x2fff),
            (veneer_allocator_model.Mapping(0x1000, 0x3000),),
            allocation_size=0x1000, page_size=0x1000)


def test_rendezvous_proof_rejects_timeout_thread_churn_and_saved_pc():
    baseline = dict(expected_threads={1, 2}, parked_threads={1, 2},
                    generation_before=7, generation_after=7,
                    saved_pcs={1: 0x100, 2: 0x200},
                    forbidden_ranges=((0x500, 0x600), (0x700, 0x800)))
    rendezvous_model.validate_parked_snapshot(**baseline)
    with pytest.raises(RuntimeError, match="every expected"):
        rendezvous_model.validate_parked_snapshot(**{**baseline, "parked_threads": {1}})
    with pytest.raises(RuntimeError, match="thread set changed"):
        rendezvous_model.validate_parked_snapshot(**{**baseline, "generation_after": 8})
    with pytest.raises(RuntimeError, match="saved PC"):
        rendezvous_model.validate_parked_snapshot(**{**baseline, "saved_pcs": {1: 0x100, 2: 0x510}})


def test_runtime_state_machine_allows_bounded_success_and_routes_incomplete_restore_to_unknown():
    machine = safety.RuntimeStateMachine()
    for state in (safety.RuntimeState.ATTACH_PENDING, safety.RuntimeState.ATTACHED,
                  safety.RuntimeState.PREPARED, safety.RuntimeState.PATCHED,
                  safety.RuntimeState.VERIFYING, safety.RuntimeState.ROLLBACK_PENDING,
                  safety.RuntimeState.RESTORING, safety.RuntimeState.VERIFIED,
                  safety.RuntimeState.DETACHED):
        machine.advance(state, preconditions_met=True)
    assert machine.state is safety.RuntimeState.DETACHED
    with pytest.raises(ValueError, match="forbidden transition"):
        machine.advance(safety.RuntimeState.PATCHED, preconditions_met=True)

    failed = safety.RuntimeStateMachine(safety.RuntimeState.RESTORING)
    assert failed.advance(safety.RuntimeState.VERIFIED, preconditions_met=True,
                          exit_evidence_complete=False) is safety.RuntimeState.UNKNOWN


def test_machine_checkable_runtime_invariants_reject_missing_proof_and_type110_changes():
    baseline = dict(type110_unchanged=True, serializer_calls=1, stock_return_preserved=True,
                    wildcard_bind=False, generation_owned_by_transaction=True,
                    stale_generation_cleanup_attempted=False, rollback_complete=True,
                    restoration_complete=True, cf_objects_owned_or_borrowed_explicitly=True,
                    listener_owned_by_generation=True, pointers_validated_before_use=True,
                    null_checked_before_dereference=True)
    safety.assert_runtime_invariants(safety.RuntimeSafetyInvariants(**baseline))
    for field, value in (("type110_unchanged", False), ("serializer_calls", 2),
                         ("wildcard_bind", True), ("restoration_complete", False)):
        with pytest.raises(ValueError, match="unproven"):
            safety.assert_runtime_invariants(safety.RuntimeSafetyInvariants(**{**baseline, field: value}))


def test_veneer_release_waits_for_restore_and_zero_in_flight_callers():
    assert not rendezvous_model.can_release_veneer(hooks_restored=False, in_flight_callers=0)
    assert not rendezvous_model.can_release_veneer(hooks_restored=True, in_flight_callers=1)
    assert rendezvous_model.can_release_veneer(hooks_restored=True, in_flight_callers=0)
