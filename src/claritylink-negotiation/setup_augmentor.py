"""Offline model for preserving Honda Setup and augmenting Type 111.

The response identity fields follow pinned MHI2 implementation behavior. Honda
confirms that unsupported Type 111 is non-fatal in the stream loop, but does not
confirm a Type 111 response schema.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Mapping

TYPE111 = 111
MAX_UINT64 = (1 << 64) - 1


class SetupAugmentationError(ValueError):
    """Request/response cannot be augmented without risking stock state."""


@dataclass(frozen=True)
class AugmentationResult:
    response: dict[str, Any]
    augmented: bool
    stream_connection_id: int | None


def _streams(value: Mapping[str, Any], owner: str) -> list[dict[str, Any]]:
    entries = value.get("streams", [])
    if not isinstance(entries, list):
        raise SetupAugmentationError(f"{owner}.streams must be a list")
    if any(not isinstance(item, dict) for item in entries):
        raise SetupAugmentationError(f"every {owner}.streams item must be a dictionary")
    return entries


def _type(entry: Mapping[str, Any]) -> int | None:
    value = entry.get("type")
    if isinstance(value, bool) or not isinstance(value, int):
        return None
    return value


def augment_setup_response(
    request: Mapping[str, Any],
    stock_response: Mapping[str, Any],
    data_port: int,
) -> AugmentationResult:
    """Return a copy of stock response with a prior-art Type-111 entry appended.

    Stock Setup is modeled as having already succeeded. The function is
    transactional: input dictionaries are never mutated, and validation errors
    leave their contents untouched. Response shape copies the requested
    descriptor and sets MHI2-observed `dataPort` and `streamID=111`; Honda's
    Type-111 response schema is not known.
    """
    if not isinstance(request, Mapping) or not isinstance(stock_response, Mapping):
        raise SetupAugmentationError("request and stock_response must be mappings")
    if isinstance(data_port, bool) or not isinstance(data_port, int) or not 1 <= data_port <= 65535:
        raise SetupAugmentationError("data_port must be an assigned TCP port")

    requested = _streams(request, "request")
    stock_streams = _streams(stock_response, "stock_response")
    matches = [entry for entry in requested if _type(entry) == TYPE111]
    if len(matches) > 1:
        raise SetupAugmentationError("duplicate Type-111 descriptors are ambiguous")

    cloned_response = deepcopy(dict(stock_response))
    if not matches:
        return AugmentationResult(cloned_response, False, None)

    descriptor = matches[0]
    cid = descriptor.get("streamConnectionID")
    if isinstance(cid, bool) or not isinstance(cid, int) or not 1 <= cid <= MAX_UINT64:
        raise SetupAugmentationError("Type-111 streamConnectionID must be a nonzero uint64")

    # Re-read cloned list, append a cloned peer descriptor, and preserve every
    # stock response entry/order and all opaque descriptor fields.
    out_streams = cloned_response.get("streams", [])
    if not isinstance(out_streams, list):
        raise SetupAugmentationError("stock_response.streams must be a list")
    type111_response = deepcopy(descriptor)
    type111_response["dataPort"] = data_port
    type111_response["streamID"] = TYPE111
    cloned_response["streams"] = out_streams + [type111_response]
    return AugmentationResult(cloned_response, True, cid)
