"""Hypothesis-only model for the CL-T4C observed warning sequence.

This module models visible states, not Honda's implementation. Each mechanism
variant intentionally produces the same observable video sequence so tests do
not claim to distinguish View replacement, Android overlay, or meter composition.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Mechanism(str, Enum):
    HONDA_VIEW_REPLACEMENT = "honda_view_replacement"
    HONDA_INTERRUPT_OVERLAY = "honda_interrupt_overlay"
    GAUGE_MODULE_COMPOSITION = "gauge_module_composition"


class Phase(str, Enum):
    CASTING_VISIBLE = "casting_visible"
    WARNING_ACTIVE = "warning_active"
    CASTING_RESTORED = "casting_restored"
    DISPLAY_REMOVED = "display_removed"
    HOST_FAILED = "host_failed"


@dataclass(frozen=True)
class Snapshot:
    mechanism: Mechanism
    phase: Phase
    cast_view_attached: bool
    cast_view_visible: bool
    warning_visible: bool
    production_admission_enabled: bool = False


class PreemptionModel:
    """Small deterministic model; no Android or vehicle display calls."""

    def __init__(self, mechanism: Mechanism):
        self.mechanism = mechanism
        self.phase = Phase.CASTING_VISIBLE
        self.attached = True
        self.warning_active = False

    def activate_warning(self) -> Snapshot:
        if self.phase in (Phase.DISPLAY_REMOVED, Phase.HOST_FAILED):
            return self.snapshot()
        self.warning_active = True
        self.phase = Phase.WARNING_ACTIVE
        if self.mechanism is Mechanism.HONDA_VIEW_REPLACEMENT:
            self.attached = False
        return self.snapshot()

    def dismiss_warning(self) -> Snapshot:
        if self.phase in (Phase.DISPLAY_REMOVED, Phase.HOST_FAILED):
            return self.snapshot()
        self.warning_active = False
        self.attached = True
        self.phase = Phase.CASTING_RESTORED
        return self.snapshot()

    def remove_display(self) -> Snapshot:
        self.attached = False
        self.warning_active = False
        self.phase = Phase.DISPLAY_REMOVED
        return self.snapshot()

    def fail_host(self) -> Snapshot:
        self.attached = False
        self.warning_active = False
        self.phase = Phase.HOST_FAILED
        return self.snapshot()

    def snapshot(self) -> Snapshot:
        return Snapshot(
            mechanism=self.mechanism,
            phase=self.phase,
            cast_view_attached=self.attached,
            cast_view_visible=self.attached and not self.warning_active,
            warning_visible=self.warning_active,
        )
