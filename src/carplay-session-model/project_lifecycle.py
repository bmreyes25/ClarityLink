"""Synthetic ClarityLink child lifecycle adapter contract; not Honda code."""

from dataclasses import dataclass, field
from threading import RLock
from typing import Any, Callable


@dataclass
class ChildState:
    generation: int
    resources: list[Any] = field(default_factory=list)
    stopped: bool = False
    releases: int = 0


class ProjectSessionRegistry:
    def __init__(self, release: Callable[[Any], None] | None = None):
        self._lock = RLock()
        self._children: dict[tuple[int, int], ChildState] = {}
        self._release = release or (lambda _: None)

    def register(self, session: int, generation: int, child: ChildState) -> None:
        with self._lock:
            self._children[(session, generation)] = child

    def child_stop(self, session: int, generation: int) -> None:
        with self._lock:
            child = self._children.get((session, generation))
            if child is None or child.stopped:
                return
            child.stopped = True
            resources, child.resources = child.resources, []
            child.releases += len(resources)
            del self._children[(session, generation)]
        for resource in resources:
            try:
                self._release(resource)
            except Exception:
                # Cleanup must fail open so stock Honda cleanup can continue.
                pass

    def platform_control(self, session: int, generation: int, command: str,
                         request: Any, stock: Callable[..., int], **kwargs: Any) -> int:
        if command == "tearDownStreams":
            try:
                types = _stream_types(request)
                if types is None or 111 in types:
                    self.child_stop(session, generation)
            except Exception:
                pass
        return stock(session, command, request, **kwargs)

    def platform_finalize(self, session: int, generation: int,
                           stock: Callable[[int], int]) -> int:
        self.child_stop(session, generation)
        return stock(session)


def _stream_types(request: Any) -> set[int] | None:
    if not isinstance(request, dict) or "streams" not in request:
        return None
    streams = request["streams"]
    if not isinstance(streams, list):
        raise ValueError("malformed streams")
    result = set()
    for item in streams:
        if not isinstance(item, dict):
            raise ValueError("malformed stream entry")
        kind = item.get("type")
        if isinstance(kind, int) and not isinstance(kind, bool):
            result.add(kind)
    return result
