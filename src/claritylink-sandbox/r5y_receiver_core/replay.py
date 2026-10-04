"""Pure replay of invented R5Y steps. No file, network or device access."""

from __future__ import annotations

from typing import Any, Mapping

from .core import FailurePoint, FaultInjector, ReceiverCore
from .model import MediaFrame, ReceiverError, ReceiverState, SessionGeneration, SetupRequest


def _generation(step: Mapping[str, Any]) -> SessionGeneration:
    return SessionGeneration(step["generation"])


def _faults(step: Mapping[str, Any]) -> FaultInjector:
    raw = step.get("fault")
    if raw is None:
        return FaultInjector()
    try:
        return FaultInjector(FailurePoint(raw))
    except ValueError:
        raise ReceiverError("unknown_fixture_fault") from None


def replay_document(document: Mapping[str, Any]) -> dict[str, Any]:
    if document.get("evidence") != "MODEL_ONLY" or not isinstance(document.get("steps"), list):
        raise ReceiverError("synthetic_fixture_required")
    core = ReceiverCore()
    errors: list[str] = []
    cleanup: list[dict[str, Any]] = []
    for step in document["steps"]:
        if not isinstance(step, dict):
            raise ReceiverError("invalid_fixture_step")
        op = step.get("op")
        try:
            key = _generation(step)
            faults = _faults(step)
            if op == "create":
                core.create_session(step["session_id"], key, faults=faults)
            elif op == "setup":
                session = core.sessions[key]
                request = SetupRequest(
                    session.session_id, key, session.primary.descriptor,
                    request_secondary=step.get("secondary", False),
                    enable_secondary=step.get("enabled", False),
                )
                core.setup(request, faults=faults)
            elif op == "start":
                core.start_streaming(key)
            elif op == "frame":
                core.send_frame(MediaFrame(key, step["sequence"], step["symbol"]), faults=faults)
            elif op == "clear":
                core.clear_display(key, step["reason"])
            elif op == "teardown":
                result = core.teardown(key, faults=faults)
                cleanup.append({"generation": key.value, "performed": result.performed,
                                "errors": list(result.errors)})
            else:
                raise ReceiverError("unknown_fixture_operation")
        except (ReceiverError, KeyError, TypeError) as exc:
            errors.append(exc.code if isinstance(exc, ReceiverError) else "invalid_fixture_shape")
    state = core.sessions[core.current].state.value if core.current else ReceiverState.IDLE.value
    snapshot = core.resource_snapshot()
    return {
        "evidence": "MODEL_ONLY", "final_state": state,
        "events": [vars(event) for event in core.events],
        "resources": vars(snapshot),
        "primary_preserved": all(core.primary_intact(key) for key, session in core.sessions.items()
                                 if session.primary_snapshot is not None),
        "cleanup": cleanup, "errors": errors,
    }
