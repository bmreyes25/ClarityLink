"""Pure host model for checked ARM32 page ranges and W^X transitions.

This module does not call mmap/mprotect or alter process memory.
"""

from dataclasses import dataclass

ARM32_LIMIT = 1 << 32


@dataclass(frozen=True)
class PageRange:
    start: int
    end: int  # exclusive

    @property
    def size(self) -> int:
        return self.end - self.start


def page_cover(address: int, length: int, page_size: int) -> PageRange:
    """Return the page-aligned ARM32 interval covering [address,address+length)."""
    if not isinstance(address, int) or not isinstance(length, int) or not isinstance(page_size, int):
        raise TypeError("address, length, and page_size must be integers")
    if page_size <= 0:
        raise ValueError("page_size must be positive")
    if length <= 0:
        raise ValueError("length must be positive")
    if address < 0 or address >= ARM32_LIMIT:
        raise ValueError("address is outside ARM32 address space")
    raw_end = address + length
    if raw_end > ARM32_LIMIT:
        raise OverflowError("range exceeds ARM32 address space")
    start = (address // page_size) * page_size
    end = ((raw_end + page_size - 1) // page_size) * page_size
    if end > ARM32_LIMIT:
        raise OverflowError("page-rounded range exceeds ARM32 address space")
    return PageRange(start, end)


@dataclass
class PermissionModel:
    """Test-only protection state; disallows writable+executable mappings."""
    protection: str = "RX"

    def set(self, protection: str) -> None:
        if protection not in {"R", "RW", "RX", "NONE"}:
            raise ValueError("unsupported modeled protection")
        if "W" in protection and "X" in protection:
            raise ValueError("W^X violation")
        self.protection = protection

    def patch_window(self) -> None:
        if self.protection != "RX":
            raise RuntimeError("patch window requires RX entry state")
        self.set("RW")

    def finish_patch(self) -> None:
        if self.protection != "RW":
            raise RuntimeError("patch completion requires RW state")
        self.set("RX")
