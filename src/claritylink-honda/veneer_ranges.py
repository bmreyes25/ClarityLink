"""Pure arithmetic for Thumb BL reach; no target allocation is attempted."""

from dataclasses import dataclass

BL_MIN = -(1 << 24)
BL_MAX = (1 << 24) - 2


@dataclass(frozen=True)
class Reach:
    start: int
    end: int  # inclusive even code addresses


def thumb_bl_reach(callsite: int) -> Reach:
    if callsite < 0 or callsite > 0xFFFFFFFE or callsite & 1:
        raise ValueError("callsite must be an aligned Thumb code address")
    pc = callsite + 4
    # Negative displacements are valid, but addresses below zero are not
    # allocatable. Clamp the architectural target-address interval to ARM32.
    return Reach(max(0, pc + BL_MIN), min(0xFFFFFFFE, pc + BL_MAX))


def common_reach(callsites: tuple[int, ...]) -> Reach:
    if not callsites:
        raise ValueError("at least one callsite is required")
    intervals = [thumb_bl_reach(site) for site in callsites]
    start = max(item.start for item in intervals)
    end = min(item.end for item in intervals)
    if start > end:
        raise ValueError("call sites have no common veneer range")
    if start & 1:
        start += 1
    if end & 1:
        end -= 1
    return Reach(start, end)
