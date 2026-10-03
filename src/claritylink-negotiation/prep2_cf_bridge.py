"""Clean-room, failure-injected CF-style response bridge model (not Honda ABI)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any


class CFError(RuntimeError):
    pass


class CFType(str, Enum):
    DICTIONARY = "dictionary"
    ARRAY = "array"
    NUMBER = "number"
    STRING = "string"


MAX_CF_STREAMS = 8


class FakeCF:
    """Small retain/release runtime for synthetic ownership and failure tests."""
    def __init__(self, fail_at: str | None = None) -> None:
        self.fail_at = fail_at
        self.calls: dict[str, int] = {}
        self.objects: dict[int, CFObject] = {}
        self.next_id = 1

    def _new(self, kind: CFType, value: Any, operation: str) -> "CFObject":
        count = self.calls.get(operation, 0) + 1
        self.calls[operation] = count
        if self.fail_at == operation or self.fail_at == f"{operation}:{count}":
            raise CFError(f"{operation}_failed")
        obj = CFObject(self, self.next_id, kind, value)
        self.next_id += 1
        self.objects[obj.identity] = obj
        return obj

    def dictionary(self, entries: dict[str, "CFObject"] | None = None) -> "CFObject":
        return self._new(CFType.DICTIONARY, {}, "dictionary_create")._init_dictionary(entries or {})

    def array(self, values: list["CFObject"] | None = None) -> "CFObject":
        return self._new(CFType.ARRAY, [], "array_create")._init_array(values or [])

    def number(self, value: int) -> "CFObject":
        return self._new(CFType.NUMBER, value, "number_create")

    def string(self, value: str) -> "CFObject":
        return self._new(CFType.STRING, value, "string_create")

    def mutable_array_clone(self, obj: "CFObject") -> "CFObject":
        """Use only the modeled CreateMutable + AppendValue capability pair."""
        obj._check()
        if obj.kind is not CFType.ARRAY: raise CFError("copy_wrong_type")
        cloned = self.array()
        try:
            for value in obj.value:
                cloned.append(value)
            return cloned
        except Exception:
            self.release(cloned)
            raise

    def release(self, obj: "CFObject") -> None:
        if not obj.alive:
            raise CFError("double_release")
        obj.refs -= 1
        if obj.refs < 0:
            raise CFError("over_release")
        if obj.refs == 0:
            obj.alive = False
            values = list(obj.value.values()) if obj.kind is CFType.DICTIONARY else (list(obj.value) if obj.kind is CFType.ARRAY else [])
            for child in values:
                self.release(child)


class CFObject:
    __slots__ = ("runtime", "identity", "kind", "value", "refs", "alive")

    def __init__(self, runtime: FakeCF, identity: int, kind: CFType, value: Any) -> None:
        self.runtime, self.identity, self.kind, self.value = runtime, identity, kind, value
        self.refs, self.alive = 1, True

    def _check(self) -> None:
        if not self.alive:
            raise CFError("use_after_release")

    def retain(self) -> "CFObject":
        self._check(); self.refs += 1
        return self

    def _init_dictionary(self, entries: dict[str, "CFObject"]) -> "CFObject":
        for key, value in entries.items():
            self.value[key] = value.retain()
        return self

    def _init_array(self, values: list["CFObject"]) -> "CFObject":
        for value in values:
            self.value.append(value.retain())
        return self

    def get(self, key: str) -> "CFObject | None":
        self._check()
        if self.kind is not CFType.DICTIONARY: raise CFError("wrong_type")
        return self.value.get(key)

    def set(self, key: str, value: "CFObject", operation: str = "dictionary_set") -> None:
        self._check(); value._check()
        if self.kind is not CFType.DICTIONARY: raise CFError("wrong_type")
        self.runtime.calls[operation] = self.runtime.calls.get(operation, 0) + 1
        count = self.runtime.calls[operation]
        if self.runtime.fail_at == operation or self.runtime.fail_at == f"{operation}:{count}":
            raise CFError(f"{operation}_failed")
        old = self.value.get(key)
        self.value[key] = value.retain()
        if old is not None: self.runtime.release(old)

    def append(self, value: "CFObject") -> None:
        self._check(); value._check()
        if self.kind is not CFType.ARRAY: raise CFError("wrong_type")
        self.runtime.calls["array_append"] = self.runtime.calls.get("array_append", 0) + 1
        count = self.runtime.calls["array_append"]
        if self.runtime.fail_at in ("array_append", f"array_append:{count}"):
            raise CFError("array_append_failed")
        self.value.append(value.retain())


class Ownership(str, Enum):
    BORROWED_RESPONSE = "BORROWED_RESPONSE"
    BORROWED_STREAMS = "BORROWED_STREAMS"
    PROJECT_TYPE = "PROJECT_TYPE"
    PROJECT_PORT = "PROJECT_PORT"
    PROJECT_ENTRY = "PROJECT_ENTRY"
    PROJECT_ARRAY_COPY = "PROJECT_ARRAY_COPY"


@dataclass
class BridgeTxn:
    response: CFObject | None          # synchronous borrowed pointer
    original_streams: CFObject | None   # synchronous borrowed pointer
    candidate_array: CFObject | None
    entry: CFObject | None
    owns_array: bool = True
    owns_entry: bool = True
    owns_original_streams: bool = True
    committed: bool = False
    finished: bool = False


def prepare_type111(runtime: FakeCF, response: CFObject, port: int) -> BridgeTxn:
    """Build all project values off-graph; no Honda object changes occur here."""
    if not isinstance(response, CFObject): raise CFError("response_null_or_invalid")
    response._check()
    if response.kind is not CFType.DICTIONARY: raise CFError("response_wrong_type")
    if isinstance(port, bool) or not isinstance(port, int) or not 1 <= port <= 65535:
        raise CFError("port_invalid")
    streams = response.get("streams")
    if streams is None or streams.kind is not CFType.ARRAY:
        raise CFError("streams_missing_or_wrong_type")
    if len(streams.value) >= MAX_CF_STREAMS: raise CFError("stream_limit")
    if any(item.kind is CFType.DICTIONARY and
           (item.get("type") is not None and item.get("type").value == 111)
           for item in streams.value):
        raise CFError("duplicate_type111")

    made: list[CFObject] = []
    try:
        # A temporary retain keeps the old array alive only through this synchronous
        # replacement/serializer transaction, so rollback can restore that exact object.
        original_hold = streams.retain(); made.append(original_hold)
        typ = runtime.number(111); made.append(typ)
        data_port = runtime.number(port); made.append(data_port)
        entry = runtime.dictionary({"type": typ, "dataPort": data_port}); made.append(entry)
        candidate = runtime.mutable_array_clone(streams); made.append(candidate)
        candidate.append(entry)
        # Drop creator refs to entry fields. The entry retains both.
        runtime.release(typ); runtime.release(data_port)
        return BridgeTxn(response, streams, candidate, entry, owns_original_streams=True)
    except Exception:
        for obj in reversed(made):
            if obj.alive:
                runtime.release(obj)
        raise


def commit_type111(txn: BridgeTxn) -> None:
    if txn.finished or txn.committed or txn.response is None or txn.candidate_array is None:
        raise CFError("transaction_not_prepared")
    # Single graph mutation, after every allocation and append succeeded.
    txn.response.set("streams", txn.candidate_array)
    txn.committed = True


def finish_type111(runtime: FakeCF, txn: BridgeTxn, *, serializer_ok: bool) -> None:
    if txn.finished: raise CFError("transaction_already_finished")
    failure: Exception | None = None
    response, original, candidate, entry = (
        txn.response, txn.original_streams, txn.candidate_array, txn.entry)
    try:
        if not serializer_ok and txn.committed:
            # Restore only this bridge's streams replacement; never rebuild response.
            if response is None or original is None or candidate is None:
                raise CFError("transaction_ownership_missing")
            current = response.get("streams")
            if current is not candidate: raise CFError("response_changed_during_transaction")
            response.set("streams", original)
    except Exception as exc:
        failure = exc
    finally:
        if txn.owns_array and candidate is not None and candidate.alive:
            runtime.release(candidate); txn.owns_array = False
        if txn.owns_entry and entry is not None and entry.alive:
            runtime.release(entry); txn.owns_entry = False
        if txn.owns_original_streams and original is not None and original.alive:
            runtime.release(original); txn.owns_original_streams = False
        txn.finished = True
        # Break all model references at transaction end; do not extend the
        # borrowed graph or project objects beyond this synchronous boundary.
        txn.response = txn.original_streams = txn.candidate_array = txn.entry = None
    if failure is not None: raise failure
