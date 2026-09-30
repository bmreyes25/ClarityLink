"""Synthetic all-thread rendezvous proof checks; no signals or threads touched."""


def validate_parked_snapshot(*, expected_threads: set[int],
                             parked_threads: set[int],
                             generation_before: int,
                             generation_after: int,
                             saved_pcs: dict[int, int],
                             forbidden_ranges: tuple[tuple[int, int], ...]) -> None:
    """Reject an incomplete/unstable rendezvous or a PC in patch/veneer code."""
    if generation_before != generation_after:
        raise RuntimeError("thread set changed during rendezvous")
    if parked_threads != expected_threads or set(saved_pcs) != expected_threads:
        raise RuntimeError("not every expected thread is parked with a saved PC")
    for pc in saved_pcs.values():
        if any(start <= pc < end for start, end in forbidden_ranges):
            raise RuntimeError("saved PC is inside patch or veneer lifetime range")


def can_release_veneer(*, hooks_restored: bool, in_flight_callers: int) -> bool:
    if in_flight_callers < 0:
        raise ValueError("in_flight_callers must be nonnegative")
    return hooks_restored and in_flight_callers == 0
