"""Known stock teardown dispatch types; no target finalizer hook."""
from __future__ import annotations

from .setup import EvidenceRequired

KNOWN_TEARDOWN_TYPES = frozenset((100, 101, 110))


def teardown_type_supported_by_static_honda(stream_type: int) -> bool:
    if stream_type == 111:
        raise EvidenceRequired("honda_type111_teardown_dispatch")
    return stream_type in KNOWN_TEARDOWN_TYPES
