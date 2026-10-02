"""Synthetic separation of Type111 transport and presentation state.

Offline model only. No Honda control messages are sent or interpreted here.
"""
from dataclasses import dataclass


@dataclass
class PresentationState:
    generation: int
    active: bool = True
    ui_suggestion: str | None = None
    visible: bool = False
    view_area: object | None = None
    safe_area: object | None = None
    refresh_count: int = 0

    def control(self, command: str, *, value: object | None = None) -> None:
        if not self.active:
            raise ValueError("transport generation is not active")
        if command == "suggestUI":
            self.ui_suggestion = str(value) if value is not None else None
        elif command == "showUI":
            self.visible = True
        elif command == "stopUI":
            self.visible = False
        elif command == "forceKeyFrame":
            self.refresh_count += 1
        elif command == "ViewArea":
            self.view_area = value
        elif command == "SafeArea":
            self.safe_area = value
        else:
            raise ValueError("unsupported synthetic presentation command")

    def transport_restart_required(self, event: str) -> bool:
        """Only transport/session faults produce a new generation."""
        if event not in {"new_setup", "stream_id_changed", "socket_death", "teardown"}:
            return False
        self.active = False
        return True
