"""OFFLINE_PROJECT_IMPLEMENTATION of ClarityLink child ownership/lifecycle.

No Honda memory is read and no Honda code is executed. Session identities are
opaque hashable tokens; every state lookup also requires a generation.
"""

from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from enum import Enum, auto
from threading import RLock
from time import monotonic
from typing import Any, Callable, Hashable, Iterable, Protocol


class ChildPhase(Enum):
    PREPARING = auto()
    PREPARED = auto()
    ACTIVE = auto()
    STOPPING = auto()
    STOPPED = auto()


class ResourceOwner(Enum):
    PREPARE_TRANSACTION = auto()
    REGISTRY = auto()
    NONE = auto()


class ResourceHandle(Protocol):
    """A project-owned resource with deterministic, idempotence-tested close."""

    def close(self) -> None: ...


@dataclass(frozen=True, order=True)
class ProjectSessionKey:
    session_identity: Hashable
    generation: int

    def __post_init__(self) -> None:
        hash(self.session_identity)
        if isinstance(self.generation, bool) or not isinstance(self.generation, int) or self.generation < 1:
            raise ValueError("generation must be a positive integer")


@dataclass
class ProjectChildState:
    key: ProjectSessionKey
    phase: ChildPhase = ChildPhase.PREPARING
    resource_owner: ResourceOwner = ResourceOwner.PREPARE_TRANSACTION
    resources: list[ResourceHandle] = field(default_factory=list)
    cleanup_started: bool = False
    cleanup_completed: bool = False
    failures: list[str] = field(default_factory=list)
    _lock: RLock = field(default_factory=RLock, repr=False, compare=False)

    def add_resource(self, resource: ResourceHandle) -> bool:
        """Transfer ownership if preparing; close immediately after stop starts."""
        close_now = False
        with self._lock:
            if self.phase is ChildPhase.PREPARING and not self.cleanup_started:
                if any(existing is resource for existing in self.resources):
                    raise ValueError("resource already owned by child")
                self.resources.append(resource)
                return True
            close_now = True
        if close_now:
            _safe_close(resource, self.failures)
        return False

    def finish_prepare(self) -> bool:
        with self._lock:
            if self.phase is not ChildPhase.PREPARING or self.cleanup_started:
                return False
            self.phase = ChildPhase.PREPARED
            return True

    def mark_active(self) -> bool:
        with self._lock:
            if self.phase is not ChildPhase.PREPARED or self.cleanup_started:
                return False
            self.phase = ChildPhase.ACTIVE
            self.resource_owner = ResourceOwner.REGISTRY
            return True

    def stop(self) -> bool:
        """Detach resources under lock; destroy them with no registry/state lock."""
        with self._lock:
            if self.cleanup_started or self.phase in (ChildPhase.STOPPING, ChildPhase.STOPPED):
                return False
            self.cleanup_started = True
            self.phase = ChildPhase.STOPPING
            self.resource_owner = ResourceOwner.NONE
            resources, self.resources = self.resources, []
        for resource in reversed(resources):
            _safe_close(resource, self.failures)
        with self._lock:
            self.phase = ChildPhase.STOPPED
            self.cleanup_completed = True
        return True


def _safe_close(resource: ResourceHandle, failures: list[str]) -> None:
    try:
        resource.close()
    except Exception as exc:  # project cleanup errors never replace stock results
        failures.append(f"{type(resource).__name__}.close: {type(exc).__name__}: {exc}")


@dataclass(frozen=True)
class RequestObservation:
    command: str
    stream_types: frozenset[int] | None
    malformed: bool
    unchanged_after_stock: bool | None


class ProjectSessionRegistry:
    """Thread-safe registry for project-only resources, never Honda-owned state."""

    def __init__(self, *, lease_seconds: float = 300.0, clock: Callable[[], float] = monotonic) -> None:
        if lease_seconds <= 0:
            raise ValueError("lease_seconds must be positive")
        self._lock = RLock()
        self._lease_seconds = lease_seconds
        self._clock = clock
        self._lease_deadline: dict[ProjectSessionKey, float] = {}
        self._children: dict[ProjectSessionKey, ProjectChildState] = {}
        self._latest_generation: dict[Hashable, int] = {}
        self._last_prepared_generation: dict[Hashable, int] = {}
        self._active_key: dict[Hashable, ProjectSessionKey] = {}
        self.diagnostics: list[str] = []
        self.observations: list[RequestObservation] = []

    def next_key(self, session_identity: Hashable) -> ProjectSessionKey:
        hash(session_identity)
        with self._lock:
            generation = self._latest_generation.get(session_identity, 0) + 1
            self._latest_generation[session_identity] = generation
            stale = tuple(
                key for key in self._children
                if key.session_identity == session_identity and key.generation < generation
            )
        for key in stale:
            self.stop_child(key, "superseded by newer generation")
        return ProjectSessionKey(session_identity, generation)

    def prepare_child(
        self,
        key: ProjectSessionKey,
        resource_factory: Callable[[], Iterable[ResourceHandle]],
    ) -> "PreparedChildTransaction":
        """Reserve a generation and acquire project resources without activation."""
        with self._lock:
            latest = self._latest_generation.get(key.session_identity, 0)
            if key.generation > latest:
                self._latest_generation[key.session_identity] = key.generation
            elif key.generation < latest:
                raise ValueError("stale project session generation")
            if key.generation <= self._last_prepared_generation.get(key.session_identity, 0):
                raise ValueError("project session generation was already used")
            child = ProjectChildState(key)
            self._children[key] = child
            self._lease_deadline[key] = self._clock() + self._lease_seconds
            self._last_prepared_generation[key.session_identity] = key.generation

        try:
            for resource in resource_factory():
                child.add_resource(resource)
            if not child.finish_prepare():
                raise RuntimeError("child stopped during preparation")
        except Exception:
            self.rollback_child(key)
            raise
        return PreparedChildTransaction(self, key)

    def prepare_after_stock_setup(
        self,
        key: ProjectSessionKey,
        resource_factory: Callable[[], Iterable[ResourceHandle]],
    ) -> "PreparedChildTransaction":
        """Future callout contract; no Honda address or runtime binding is implied."""
        return self.prepare_child(key, resource_factory)

    def child(self, key: ProjectSessionKey) -> ProjectChildState | None:
        with self._lock:
            return self._children.get(key)

    def active_key(self, session_identity: Hashable) -> ProjectSessionKey | None:
        with self._lock:
            return self._active_key.get(session_identity)

    def _detach(self, key: ProjectSessionKey) -> ProjectChildState | None:
        with self._lock:
            child = self._children.pop(key, None)
            self._lease_deadline.pop(key, None)
            if self._active_key.get(key.session_identity) == key:
                self._active_key.pop(key.session_identity, None)
            return child

    def renew_lease(self, key: ProjectSessionKey) -> bool:
        """Renew only the exact current generation after project-owned activity."""
        with self._lock:
            if key.generation != self._latest_generation.get(key.session_identity):
                return False
            child = self._children.get(key)
            if child is None or child.phase not in (ChildPhase.PREPARED, ChildPhase.ACTIVE):
                return False
            self._lease_deadline[key] = self._clock() + self._lease_seconds
            return True

    def reap_expired(self, *, now: float | None = None) -> tuple[ProjectSessionKey, ...]:
        """Stop expired exact generations; stale cleanup cannot touch replacements."""
        current = self._clock() if now is None else now
        with self._lock:
            expired = tuple(key for key, deadline in self._lease_deadline.items() if deadline <= current)
        for key in expired:
            self.stop_child(key, "generation lease expired")
        return expired

    def stop_child(self, key: ProjectSessionKey, reason: str) -> None:
        child = self._detach(key)
        if child is None:
            return
        child.stop()
        if child.failures:
            self.diagnostics.extend(f"{key}: {failure}" for failure in child.failures)
        self.diagnostics.append(f"stopped {key}: {reason}")

    def rollback_child(self, key: ProjectSessionKey) -> None:
        self.stop_child(key, "rollback")

    def project_transport_failed(self, key: ProjectSessionKey, reason: str) -> None:
        self.stop_child(key, f"transport failure: {reason}")

    def record_ui_event(self, key: ProjectSessionKey, command: str) -> bool:
        if command not in {"suggestUI", "showUI", "stopUI", "modesChanged", "requestUI"}:
            return False
        with self._lock:
            child = self._children.get(key)
        if child is not None:
            self.diagnostics.append(f"UI/control event {command} for {key}; transport retained")
        return child is not None

    def platform_control(
        self,
        key: ProjectSessionKey,
        command: str,
        params: Any,
        stock_platform_control: Callable[[str, Any], Any],
    ) -> Any:
        """Call stock once with the same request, then perform project cleanup."""
        stream_types: frozenset[int] | None = None
        malformed = False
        snapshot: Any = None
        can_compare = False
        if command == "tearDownStreams":
            try:
                snapshot = deepcopy(params)
                can_compare = True
                stream_types = _stream_types(params)
            except Exception as exc:
                malformed = True
                self.diagnostics.append(f"request inspection failed for {key}: {type(exc).__name__}")

        result: Any = None
        try:
            result = stock_platform_control(command, params)
        finally:
            unchanged = None
            if can_compare:
                try:
                    unchanged = params == snapshot
                except Exception:
                    unchanged = None
            self.observations.append(RequestObservation(command, stream_types, malformed, unchanged))
            if command == "tearDownStreams" and not malformed and stream_types is not None and 111 in stream_types:
                # Honda remains authoritative; cleanup follows its one stock call.
                try:
                    self.stop_child(key, "Type111 tearDownStreams")
                except Exception as exc:
                    self.diagnostics.append(f"child cleanup failed for {key}: {type(exc).__name__}")
        return result

    def platform_finalize(
        self,
        key: ProjectSessionKey,
        stock_platform_finalize: Callable[[], Any],
    ) -> Any:
        """Atomically detach/clean project state, then invoke stock exactly once."""
        try:
            self.stop_child(key, "PlatformFinalize")
        except Exception as exc:
            self.diagnostics.append(f"finalize child cleanup failed for {key}: {type(exc).__name__}")
        return stock_platform_finalize()


class PreparedChildTransaction:
    """Owns the prepare-to-active boundary; caller selects the future commit point."""

    def __init__(self, registry: ProjectSessionRegistry, key: ProjectSessionKey):
        self.registry = registry
        self.key = key
        self.response_ready = False
        self.finished = False

    def mark_response_ready(self) -> None:
        child = self.registry.child(self.key)
        if self.finished or child is None or child.phase is not ChildPhase.PREPARED:
            raise RuntimeError("project child is no longer prepared")
        self.response_ready = True

    def observe_serializer_result(self, return_code: int, status_out: int) -> bool:
        """Apply Honda's recovered local-success predicate to a synthetic twin."""
        if return_code != 0xC8 or status_out != 0:
            return False
        self.mark_response_ready()
        return True

    def commit_after_response_commit(self) -> bool:
        """Caller invokes only once the future response transaction has committed."""
        if self.finished or not self.response_ready:
            raise RuntimeError("response transaction is not ready for commit")
        stale = False
        with self.registry._lock:
            child = self.registry._children.get(self.key)
            active = self.registry._active_key.get(self.key.session_identity)
            if active is not None and active.generation > self.key.generation:
                stale = True
            elif child is None or not child.mark_active():
                self.finished = True
                return False
            else:
                self.registry._active_key[self.key.session_identity] = self.key
        if stale:
            self.finished = True
            self.registry.rollback_child(self.key)
            return False
        self.finished = True
        return True

    def rollback_before_response_commit(self) -> None:
        if self.finished:
            return
        self.finished = True
        self.registry.rollback_child(self.key)


def _stream_types(params: Any) -> frozenset[int] | None:
    """Return None when whole-session/missing-list semantics are unresolved."""
    if not isinstance(params, dict) or "streams" not in params:
        return None
    streams = params["streams"]
    if not isinstance(streams, list):
        raise ValueError("streams must be a list")
    result: set[int] = set()
    for entry in streams:
        if not isinstance(entry, dict):
            raise ValueError("stream entry must be a mapping")
        stream_type = entry.get("type")
        if isinstance(stream_type, bool) or not isinstance(stream_type, int):
            raise ValueError("stream type must be an integer")
        result.add(stream_type)
    return frozenset(result)
