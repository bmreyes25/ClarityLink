"""Stock-first, fail-soft Setup transaction model with injected project setup."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass
from typing import Any, Callable, Mapping

from setup_augmentor import SetupAugmentationError, augment_setup_response


@dataclass(frozen=True)
class TransactionResult:
    status: int
    response: dict[str, Any] | None
    augmented: bool


def run_stock_first_setup(
    request: Mapping[str, Any],
    stock_setup: Callable[[Mapping[str, Any]], tuple[int, Mapping[str, Any] | None]],
    prepare_type111: Callable[[int], int],
    rollback_type111: Callable[[], None],
) -> TransactionResult:
    """Run stock first; project failure preserves and returns stock response.

    `prepare_type111` is an injected offline stand-in for project-owned KDF,
    listener, and session allocation. No platform resources are created here.
    """
    status, response = stock_setup(request)
    if status != 0:
        return TransactionResult(status, deepcopy(dict(response)) if response is not None else None, False)
    if response is None:
        return TransactionResult(status, None, False)

    try:
        entries = request.get("streams", [])
        if not isinstance(entries, list):
            raise SetupAugmentationError("request.streams must be a list")
        matches = [entry for entry in entries if isinstance(entry, dict) and entry.get("type") == 111]
        if len(matches) > 1:
            raise SetupAugmentationError("duplicate Type-111 descriptors are ambiguous")
        if not matches:
            return TransactionResult(status, deepcopy(dict(response)), False)
        cid = matches[0].get("streamConnectionID")
        if isinstance(cid, bool) or not isinstance(cid, int) or not 1 <= cid < (1 << 64):
            raise SetupAugmentationError("Type-111 streamConnectionID must be a nonzero uint64")
        port = prepare_type111(cid)
        augmented = augment_setup_response(request, response, port)
        return TransactionResult(status, augmented.response, augmented.augmented)
    except Exception:
        rollback_type111()
        return TransactionResult(status, deepcopy(dict(response)), False)
