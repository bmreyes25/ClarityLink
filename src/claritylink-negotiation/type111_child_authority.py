"""Parent-owned authority for a single Type111 child stream (CL-HONDA-111-01).

Original, offline, synthetic-only model of the consumer side of the receiver
contract in ``docs/development/cl-honda-111-01-receiver-architecture.md``
(section 5). It states, once and testably, what any provider of a Type111 child
stream must satisfy; it does not implement a provider, a key derivation, an
authentication step, or any Honda call.

Rules (do not relax):
  * The ``ParentAuthority`` stands in for the factory-owned authenticated
    session. It is constructed ``synthetic=True`` only. A non-synthetic parent
    cannot be built: no attestation of a real Honda session exists, so the
    request fails closed rather than pretending.
  * A child holds an opaque capability. It carries no key, master material,
    session secret or socket, and its representation is redacted.
  * A grant opens at most one child. Parent loss, ``close`` and ``revoke``
    all end the child; none of them can be undone.
  * At most one Type111 child is live at a time and stream identities are never
    reused while live. Stream generations are lifetime-monotonic on the parent.
  * Nothing here reads or writes Type110 state. A child cannot name it.
  * Revocation callbacks are contained and run exactly once.
"""
from __future__ import annotations

import threading
from dataclasses import dataclass
from enum import Enum
from typing import Callable

MAX_REVOKE_CALLBACKS = 16


class AuthorityError(RuntimeError):
    def __init__(self, code: str) -> None:
        self.code = code
        super().__init__(code)


class ParentState(str, Enum):
    ACTIVE = "ACTIVE"
    LOST = "LOST"


class ChildState(str, Enum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    REVOKED = "REVOKED"


def _valid_u64(value: object) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and 1 <= value < (1 << 64)


@dataclass(frozen=True)
class ChildIdentity:
    parent_id: int
    parent_generation: int
    stream_connection_id: int
    stream_generation: int


class ChildGrant:
    """Single-use, non-serializable permission to open one child."""

    __slots__ = ("_identity", "_consumed", "_parent")

    def __init__(self, parent: "ParentAuthority", identity: ChildIdentity) -> None:
        self._parent = parent
        self._identity = identity
        self._consumed = False

    @property
    def identity(self) -> ChildIdentity:
        return self._identity

    def __repr__(self) -> str:
        return "ChildGrant(<redacted>)"

    def __reduce__(self):
        raise TypeError("ChildGrant is not serializable")


class Type111Child:
    """An open child stream. Holds identity and lifecycle only."""

    def __init__(self, parent: "ParentAuthority", identity: ChildIdentity) -> None:
        self._parent = parent
        self._identity = identity
        self._state = ChildState.OPEN
        self._callbacks: list[Callable[[str], None]] = []
        self._lock = threading.RLock()

    @property
    def identity(self) -> ChildIdentity:
        return self._identity

    @property
    def state(self) -> ChildState:
        return self._state

    @property
    def live(self) -> bool:
        with self._lock:
            return (self._state is ChildState.OPEN
                    and self._parent.state is ParentState.ACTIVE
                    and self._parent.generation == self._identity.parent_generation)

    def __repr__(self) -> str:
        return f"Type111Child(state={self._state.value}, <redacted>)"

    def __reduce__(self):
        raise TypeError("Type111Child is not serializable")

    def add_end_callback(self, callback: Callable[[str], None]) -> None:
        """Run ``callback(reason)`` once when the child ends for any reason.
        A child that has already ended runs it immediately."""
        run_now = None
        with self._lock:
            if self._state is not ChildState.OPEN:
                run_now = self._state.value
            else:
                if len(self._callbacks) >= MAX_REVOKE_CALLBACKS:
                    raise AuthorityError("too_many_end_callbacks")
                self._callbacks.append(callback)
        if run_now is not None:
            self._run(callback, run_now)

    def close(self) -> None:
        self._end(ChildState.CLOSED, "closed")

    def _revoke(self, reason: str) -> None:
        self._end(ChildState.REVOKED, reason)

    def _end(self, state: ChildState, reason: str) -> None:
        with self._lock:
            if self._state is not ChildState.OPEN:
                return
            self._state = state
            callbacks, self._callbacks = self._callbacks, []
        self._parent._child_ended(self)
        for callback in callbacks:
            self._run(callback, reason)

    @staticmethod
    def _run(callback: Callable[[str], None], reason: str) -> None:
        try:
            callback(reason)
        except Exception:
            # Containment: one consumer's failure must not stop teardown.
            pass


class ParentAuthority:
    """Synthetic stand-in for the factory-owned authenticated parent."""

    def __init__(self, *, parent_id: int = 1, generation: int = 1, synthetic: bool = True) -> None:
        if synthetic is not True:
            # No attestation of a real Honda parent exists; never pretend.
            raise AuthorityError("attestation_unavailable")
        for value in (parent_id, generation):
            if isinstance(value, bool) or not isinstance(value, int) or value < 1:
                raise AuthorityError("invalid_parent_identity")
        self._parent_id = parent_id
        self._generation = generation
        self._state = ParentState.ACTIVE
        self._stream_generation = 0
        self._live: Type111Child | None = None
        self._pending: ChildGrant | None = None
        self._lock = threading.RLock()

    @property
    def synthetic(self) -> bool:
        return True

    @property
    def state(self) -> ParentState:
        return self._state

    @property
    def generation(self) -> int:
        return self._generation

    @property
    def live_child(self) -> Type111Child | None:
        return self._live

    def __repr__(self) -> str:
        return f"ParentAuthority(state={self._state.value}, synthetic=True)"

    def grant_child(self, stream_connection_id: int) -> ChildGrant:
        """Issue one single-use grant. Denies on parent loss, a live child, an
        outstanding unopened grant, or an invalid identity."""
        with self._lock:
            if self._state is not ParentState.ACTIVE:
                raise AuthorityError("parent_lost")
            if not _valid_u64(stream_connection_id):
                raise AuthorityError("invalid_stream_connection_id")
            if self._live is not None and self._live.live:
                raise AuthorityError("child_already_live")
            if self._pending is not None and not self._pending._consumed:
                raise AuthorityError("grant_outstanding")
            self._stream_generation += 1
            grant = ChildGrant(self, ChildIdentity(
                self._parent_id, self._generation, stream_connection_id, self._stream_generation))
            self._pending = grant
            return grant

    def open_child(self, grant: ChildGrant) -> Type111Child:
        with self._lock:
            if not isinstance(grant, ChildGrant) or grant._parent is not self:
                raise AuthorityError("foreign_grant")
            if grant._consumed:
                raise AuthorityError("grant_consumed")
            if self._state is not ParentState.ACTIVE:
                raise AuthorityError("parent_lost")
            if grant._identity.parent_generation != self._generation:
                raise AuthorityError("stale_parent_generation")
            if self._pending is not grant:
                raise AuthorityError("grant_superseded")
            grant._consumed = True
            self._pending = None
            child = Type111Child(self, grant._identity)
            self._live = child
            return child

    def lose(self) -> None:
        """The authenticated parent is gone. Every child is revoked, permanently."""
        with self._lock:
            if self._state is ParentState.LOST:
                return
            self._state = ParentState.LOST
            self._pending = None
            child = self._live
        if child is not None:
            child._revoke("parent_lost")

    def _child_ended(self, child: Type111Child) -> None:
        with self._lock:
            if self._live is child:
                self._live = None
