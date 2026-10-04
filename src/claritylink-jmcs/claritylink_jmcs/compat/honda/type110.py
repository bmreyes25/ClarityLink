"""Known-field Type110 oracle from static Honda Setup evidence."""
from __future__ import annotations

from typing import Mapping, Any

from .setup import EvidenceRequired


def known_type110_response_matches(entry: Mapping[str, Any], port: int) -> bool:
    """Only verifies the confirmed `type` and `dataPort` pair."""
    if entry.get("type") != 110 or entry.get("dataPort") != port:
        return False
    if any(key not in ("type", "dataPort") for key in entry):
        raise EvidenceRequired("honda_type110_extra_response_fields")
    return True
