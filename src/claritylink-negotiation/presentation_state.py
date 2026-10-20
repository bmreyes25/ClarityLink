"""Synthetic Type111 presentation/control state, separate from stream transport.

This is a host-side acceptance model for externally observed control concepts.
It sends no messages and does not assert Honda support or wire compatibility.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Mapping


MAP_CONTEXT = "maps:/car/instrumentcluster/map"
INSTRUCTION_CONTEXT = "maps:/car/instrumentcluster/instructioncard"


@dataclass
class PresentationState:
    generation: int
    active: bool = True
    ui_suggestion: str | None = None
    selected_context: str | None = None
    visible: bool = False
    view_area: object | None = None
    safe_area: object | None = None
    refresh_count: int = 0
    display_width: int = 800
    display_height: int = 480
    supported_contexts: frozenset[str] = field(
        default_factory=lambda: frozenset((MAP_CONTEXT, INSTRUCTION_CONTEXT)))
    navigation_provider: str | None = None
    navigation_active: bool = False
    instruction_active: bool = False
    presentation_generation: int = 0
    decoder_generation: int = 0
    video_config: tuple[int, int] | None = None

    def __post_init__(self) -> None:
        if isinstance(self.generation, bool) or not isinstance(self.generation, int) or self.generation <= 0:
            raise ValueError("positive_transport_generation_required")
        if (not 1 <= self.display_width <= 4096 or not 1 <= self.display_height <= 4096 or
                not self.supported_contexts or not self.supported_contexts.issubset(
                    frozenset((MAP_CONTEXT, INSTRUCTION_CONTEXT)))):
            raise ValueError("invalid_synthetic_display_profile")

    @property
    def eligible_contexts(self) -> tuple[str, ...]:
        if not self.active or not self.navigation_active or self.navigation_provider not in ("maps", "waze"):
            return ()
        candidates = [MAP_CONTEXT] if MAP_CONTEXT in self.supported_contexts else []
        if self.instruction_active and INSTRUCTION_CONTEXT in self.supported_contexts:
            candidates.append(INSTRUCTION_CONTEXT)
        return tuple(candidates)

    def set_navigation(self, provider: str | None, *, active: bool,
                       instruction_active: bool = False) -> None:
        """Update UI candidates without replacing the Type111 transport."""
        if not self.active:
            raise ValueError("transport_generation_not_active")
        if active and provider not in ("maps", "waze"):
            raise ValueError("unsupported_navigation_provider")
        self.navigation_provider = provider if active else None
        self.navigation_active = bool(active)
        self.instruction_active = bool(active and instruction_active)
        if self.ui_suggestion not in self.eligible_contexts:
            if self.ui_suggestion is not None or self.selected_context is not None or self.visible:
                self.ui_suggestion = None
                self.selected_context = None
                self.visible = False
                self.presentation_generation += 1

    def control(self, command: str, *, value: object | None = None) -> None:
        if not self.active:
            raise ValueError("transport_generation_not_active")
        if command == "suggestUI":
            if not isinstance(value, str) or value not in self.eligible_contexts:
                raise ValueError("ui_context_not_eligible")
            self.ui_suggestion = value
            # Suggesting a view never transfers visible presentation ownership.
        elif command == "showUI":
            if self.ui_suggestion is None or self.ui_suggestion not in self.eligible_contexts:
                raise ValueError("no_eligible_ui_suggestion")
            if not self.visible or self.selected_context != self.ui_suggestion:
                self.selected_context = self.ui_suggestion
                self.visible = True
                self.presentation_generation += 1
        elif command == "stopUI":
            if self.visible or self.selected_context is not None or self.ui_suggestion is not None:
                self.visible = False
                self.selected_context = None
                self.ui_suggestion = None
                self.presentation_generation += 1
        elif command == "forceKeyFrame":
            self.refresh_count += 1
        elif command == "ViewArea":
            rect = _rect(value, self.display_width, self.display_height, "invalid_view_area")
            if self.safe_area is not None and not _contains(rect, self.safe_area):
                raise ValueError("safe_area_outside_view_area")
            self.view_area = rect
            self.presentation_generation += 1
        elif command == "SafeArea":
            rect = _rect(value, self.display_width, self.display_height, "invalid_safe_area")
            if self.view_area is not None and not _contains(self.view_area, rect):
                raise ValueError("safe_area_outside_view_area")
            self.safe_area = rect
            self.presentation_generation += 1
        else:
            raise ValueError("unsupported_synthetic_presentation_command")

    def update_video_config(self, width: int, height: int) -> int:
        """A codec change advances decoder generation, not transport generation."""
        if not self.active:
            raise ValueError("transport_generation_not_active")
        if (isinstance(width, bool) or isinstance(height, bool) or not isinstance(width, int) or
                not isinstance(height, int) or not 1 <= width <= 3840 or not 1 <= height <= 2160):
            raise ValueError("invalid_video_config")
        config = (width, height)
        if config != self.video_config:
            self.video_config = config
            self.decoder_generation += 1
        return self.decoder_generation

    def transport_restart_required(self, event: str) -> bool:
        """Only modeled transport lifecycle events retire this stream generation."""
        if event not in {"new_setup", "stream_id_changed", "socket_death", "teardown"}:
            return False
        self.active = False
        self.visible = False
        self.selected_context = None
        self.ui_suggestion = None
        self.presentation_generation += 1
        return True


def _rect(value: object, width: int, height: int, error: str) -> dict[str, int]:
    if not isinstance(value, Mapping) or set(value) != {"x", "y", "w", "h"}:
        raise ValueError(error)
    x, y, w, h = (value.get(key) for key in ("x", "y", "w", "h"))
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (x, y, w, h)):
        raise ValueError(error)
    if x < 0 or y < 0 or w <= 0 or h <= 0 or x + w > width or y + h > height:
        raise ValueError(error)
    return {"x": x, "y": y, "w": w, "h": h}


def _contains(outer: Mapping[str, int], inner: Mapping[str, int]) -> bool:
    return (inner["x"] >= outer["x"] and inner["y"] >= outer["y"] and
            inner["x"] + inner["w"] <= outer["x"] + outer["w"] and
            inner["y"] + inner["h"] <= outer["y"] + outer["h"])
