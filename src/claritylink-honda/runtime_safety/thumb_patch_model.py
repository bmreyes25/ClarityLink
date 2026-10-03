"""Simulation-only counterexample model for a four-byte Thumb BL replacement.

This code mutates only an in-process bytearray. It has no process-memory,
ptrace, ADB, device, listener, or runtime-experiment backend, and can never
authorize an executable experiment. Permission/cache events are abstract model
labels, not calls to an operating system or claims about a specific CPU.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from thumb_call import decode_thumb_bl, encode_thumb_bl


class PatchModelError(ValueError):
    """The requested model transition is invalid or evidence is incomplete."""


class PatchPhase(str, Enum):
    STOCK = "STOCK"
    PATCHING = "PATCHING"
    PATCHED_MODEL_ONLY = "PATCHED_MODEL_ONLY"
    RESTORING = "RESTORING"
    RESTORED_MODEL_ONLY = "RESTORED_MODEL_ONLY"
    INTERRUPTED = "INTERRUPTED"
    UNKNOWN = "UNKNOWN"


class FetchState(str, Enum):
    STOCK = "STOCK"
    REPLACEMENT = "REPLACEMENT"
    MIXED_HALFWORDS = "MIXED_HALFWORDS"
    FOREIGN = "FOREIGN"


@dataclass(frozen=True)
class ThumbCallsitePlan:
    address: int
    stock_bytes: bytes
    stock_target: int
    replacement_target: int
    continuation: int
    fetch_group_size: int = 4

    def __post_init__(self) -> None:
        if isinstance(self.address, bool) or not isinstance(self.address, int) or self.address < 0 or self.address & 1:
            raise PatchModelError("callsite_must_be_halfword_aligned")
        if not isinstance(self.stock_bytes, bytes) or len(self.stock_bytes) != 4:
            raise PatchModelError("callsite_must_be_four_bytes")
        if self.fetch_group_size < 2 or self.fetch_group_size & (self.fetch_group_size - 1):
            raise PatchModelError("fetch_group_size_must_be_power_of_two")
        stock = decode_thumb_bl(self.address, self.stock_bytes)
        if stock.target != self.stock_target or stock.return_address != self.continuation:
            raise PatchModelError("stock_target_or_continuation_mismatch")
        replacement = decode_thumb_bl(self.address, self.replacement_bytes)
        if replacement.target != self.replacement_target or replacement.return_address != self.continuation:
            raise PatchModelError("replacement_target_or_continuation_mismatch")

    @property
    def replacement_bytes(self) -> bytes:
        return encode_thumb_bl(self.address, self.replacement_target)

    @property
    def crosses_fetch_group(self) -> bool:
        end = self.address + len(self.stock_bytes) - 1
        return self.address // self.fetch_group_size != end // self.fetch_group_size

    def possible_halfword_states(self) -> frozenset[bytes]:
        """All combinations reachable when either 16-bit half is written first."""
        old = (self.stock_bytes[:2], self.stock_bytes[2:])
        new = (self.replacement_bytes[:2], self.replacement_bytes[2:])
        return frozenset((old[0] + old[1], new[0] + old[1], old[0] + new[1], new[0] + new[1]))

    def affected_page_span(self, page_size: int = 4096) -> tuple[int, int]:
        """Return a modeled page-cover interval; this performs no mapping call."""
        if isinstance(page_size, bool) or not isinstance(page_size, int) or page_size <= 0:
            raise PatchModelError("page_size_invalid")
        start = self.address // page_size * page_size
        end_exclusive = self.address + 4
        end = ((end_exclusive + page_size - 1) // page_size) * page_size
        return start, end


@dataclass(frozen=True)
class RendezvousEvidence:
    thread_ids_before: tuple[int, ...]
    thread_ids_after: tuple[int, ...]
    parked_thread_ids: tuple[int, ...]
    saved_pcs: tuple[tuple[int, int], ...]
    reentry_blocked: bool


@dataclass(frozen=True)
class RendezvousAssessment:
    acceptable_snapshot: bool
    failures: tuple[str, ...]


def assess_rendezvous(evidence: RendezvousEvidence, patch_start: int, patch_end: int) -> RendezvousAssessment:
    """Check one proposed snapshot; this does not stop or control any thread."""
    failures: list[str] = []
    before, after, parked = map(set, (evidence.thread_ids_before, evidence.thread_ids_after,
                                      evidence.parked_thread_ids))
    pcs = dict(evidence.saved_pcs)
    if before != after:
        failures.append("thread_set_changed")
    if parked != before:
        failures.append("not_every_thread_parked")
    if set(pcs) != before:
        failures.append("saved_pc_set_incomplete")
    if any(patch_start <= pc < patch_end for pc in pcs.values()):
        failures.append("saved_pc_inside_patch_span")
    if evidence.reentry_blocked is not True:
        failures.append("reentry_not_blocked")
    return RendezvousAssessment(not failures, tuple(failures))


@dataclass
class ThumbPatchSimulation:
    """Bytearray-only model of two ordered halfword writes and restoration."""
    plan: ThumbCallsitePlan
    page_size: int = 4096
    code: bytearray = field(init=False)
    permission: str = field(default="RX", init=False)
    phase: PatchPhase = field(default=PatchPhase.STOCK, init=False)
    events: list[str] = field(default_factory=list, init=False)
    _patch_halves: set[int] = field(default_factory=set, init=False, repr=False)
    _restore_halves: set[int] = field(default_factory=set, init=False, repr=False)
    _cache_sync_ok: bool = field(default=False, init=False, repr=False)

    def __post_init__(self) -> None:
        self.plan.affected_page_span(self.page_size)
        self.code = bytearray(self.plan.stock_bytes)

    @property
    def current_bytes(self) -> bytes:
        return bytes(self.code)

    def modeled_fetch_state(self) -> FetchState:
        current = self.current_bytes
        if current == self.plan.stock_bytes:
            return FetchState.STOCK
        if current == self.plan.replacement_bytes:
            return FetchState.REPLACEMENT
        if current in self.plan.possible_halfword_states():
            return FetchState.MIXED_HALFWORDS
        return FetchState.FOREIGN

    def begin_patch(self) -> None:
        if self.phase is not PatchPhase.STOCK or self.current_bytes != self.plan.stock_bytes or self.permission != "RX":
            raise PatchModelError("patch_requires_exact_stock_rx_state")
        self.permission = "RW"
        self.events.append("model_permission:RX->RW")
        self.phase = PatchPhase.PATCHING

    def write_patch_halfword(self, index: int) -> None:
        if self.phase is not PatchPhase.PATCHING or self.permission != "RW" or index not in (0, 1):
            raise PatchModelError("patch_halfword_transition_invalid")
        if index in self._patch_halves:
            raise PatchModelError("patch_halfword_already_written")
        start = index * 2
        self.code[start:start + 2] = self.plan.replacement_bytes[start:start + 2]
        self._patch_halves.add(index)
        self.events.append(f"model_write_halfword:{index}")

    def synchronize_cache(self, *, success: bool, restoring: bool = False) -> None:
        expected_phase = PatchPhase.RESTORING if restoring else PatchPhase.PATCHING
        written = self._restore_halves if restoring else self._patch_halves
        if self.phase is not expected_phase or written != {0, 1}:
            raise PatchModelError("cache_sync_before_both_halfwords")
        self._cache_sync_ok = success is True
        self.events.append("model_cache_sync:success" if success else "model_cache_sync:failure")
        if not success:
            self.phase = PatchPhase.UNKNOWN

    def finish_patch(self) -> None:
        if self.phase is not PatchPhase.PATCHING or not self._cache_sync_ok:
            raise PatchModelError("patch_not_cache_synchronized")
        if self.current_bytes != self.plan.replacement_bytes:
            self.phase = PatchPhase.UNKNOWN
            raise PatchModelError("replacement_readback_mismatch")
        self.permission = "RX"
        self.events.extend(("model_permission:RW->RX", "model_readback:replacement"))
        self.phase = PatchPhase.PATCHED_MODEL_ONLY

    def interrupt(self) -> None:
        if self.phase in (PatchPhase.STOCK, PatchPhase.RESTORED_MODEL_ONLY, PatchPhase.UNKNOWN):
            raise PatchModelError("no_patch_transition_to_interrupt")
        self.events.append(f"model_interruption:{self.phase.value}")
        self.phase = PatchPhase.INTERRUPTED
        self._cache_sync_ok = False

    def begin_restore(self) -> bool:
        """Start restoration only from byte states generated by this model.

        Returns False for an already-restored state. Any foreign bytes fail
        closed and are never overwritten.
        """
        current = self.current_bytes
        if current == self.plan.stock_bytes and self.permission == "RX":
            self.phase = PatchPhase.RESTORED_MODEL_ONLY
            self.events.append("model_restore:idempotent_noop")
            return False
        if current not in self.plan.possible_halfword_states():
            raise PatchModelError("restore_refuses_foreign_bytes")
        if self.permission not in ("RX", "RW"):
            self.phase = PatchPhase.UNKNOWN
            raise PatchModelError("restore_permission_unknown")
        if self.permission == "RX":
            self.permission = "RW"
            self.events.append("model_permission:RX->RW_restore")
        self.phase = PatchPhase.RESTORING
        self._restore_halves.clear()
        self._cache_sync_ok = False
        return True

    def write_restore_halfword(self, index: int) -> None:
        if self.phase is not PatchPhase.RESTORING or self.permission != "RW" or index not in (0, 1):
            raise PatchModelError("restore_halfword_transition_invalid")
        if index in self._restore_halves:
            raise PatchModelError("restore_halfword_already_written")
        start = index * 2
        self.code[start:start + 2] = self.plan.stock_bytes[start:start + 2]
        self._restore_halves.add(index)
        self.events.append(f"model_restore_halfword:{index}")

    def finish_restore(self) -> None:
        if self.phase is not PatchPhase.RESTORING or not self._cache_sync_ok:
            raise PatchModelError("restore_not_cache_synchronized")
        if self._restore_halves != {0, 1} or self.current_bytes != self.plan.stock_bytes:
            self.phase = PatchPhase.UNKNOWN
            raise PatchModelError("restore_readback_mismatch")
        self.permission = "RX"
        self.events.extend(("model_permission:RW->RX_restore", "model_readback:stock"))
        self.phase = PatchPhase.RESTORED_MODEL_ONLY

    def authorize_executable_experiment(self) -> None:
        raise PatchModelError("host_model_never_authorizes_executable_experiment")

    def ordered_event_check(self, *, restoring: bool = False) -> bool:
        """Check the abstract permission/write/cache/permission/readback order."""
        prefix = "model_restore_halfword:" if restoring else "model_write_halfword:"
        start_event = "model_permission:RX->RW_restore" if restoring else "model_permission:RX->RW"
        end_event = "model_permission:RW->RX_restore" if restoring else "model_permission:RW->RX"
        readback = "model_readback:stock" if restoring else "model_readback:replacement"
        try:
            start = self.events.index(start_event)
        except ValueError:
            # A partial patch can leave the modeled page RW before restore starts.
            if restoring and "model_permission:RX->RW" in self.events:
                start = self.events.index("model_permission:RX->RW")
            else:
                return False
        try:
            writes = [i for i, e in enumerate(self.events) if e.startswith(prefix)]
            sync = self.events.index("model_cache_sync:success", start)
            end = self.events.index(end_event, sync)
            verify = self.events.index(readback, end)
        except ValueError:
            return False
        return len(writes) >= 2 and start < min(writes) < max(writes) < sync < end < verify
