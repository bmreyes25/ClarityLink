"""Choose a synthetic free interval from a supplied mapping snapshot only."""

from dataclasses import dataclass

from page_model import PageRange
from veneer_ranges import Reach


@dataclass(frozen=True)
class Mapping:
    start: int
    end: int  # exclusive


def choose_snapshot_gap(reach: Reach, mappings: tuple[Mapping, ...], *,
                        allocation_size: int, page_size: int,
                        minimum_address: int = 0x1000) -> PageRange:
    """Return a page-aligned synthetic candidate; this does not reserve it."""
    if allocation_size <= 0 or page_size <= 0:
        raise ValueError("allocation_size and page_size must be positive")
    if minimum_address < 0:
        raise ValueError("minimum_address must be nonnegative")
    occupied = sorted(mappings, key=lambda item: item.start)
    cursor = max(minimum_address, reach.start)
    cursor = ((cursor + page_size - 1) // page_size) * page_size
    for item in occupied:
        if item.start < 0 or item.end < item.start:
            raise ValueError("invalid mapping snapshot interval")
        if cursor + allocation_size <= item.start:
            end = cursor + allocation_size
            rounded_end = ((end + page_size - 1) // page_size) * page_size
            if rounded_end - 1 <= reach.end:
                return PageRange(cursor, rounded_end)
        cursor = max(cursor, item.end)
        cursor = ((cursor + page_size - 1) // page_size) * page_size
    end = cursor + allocation_size
    rounded_end = ((end + page_size - 1) // page_size) * page_size
    if cursor <= reach.end and rounded_end - 1 <= reach.end:
        return PageRange(cursor, rounded_end)
    raise ValueError("no fitting free interval in supplied snapshot")
