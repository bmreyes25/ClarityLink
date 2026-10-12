"""Offline-only Phase R/C decision rehearsal; no ADB or filesystem writes."""
from __future__ import annotations

from dataclasses import dataclass

from tools import r7e6_test_a_collector as test_a


@dataclass
class SimulatedRecovery:
    phase_r_result: str
    exact_path: str = test_a.REMOTE
    target_identity_confirmed: bool = True
    current_process_safety_independently_reviewed: bool = False
    phase_c_separately_authorized: bool = False
    material_concern: bool = False
    file_present: bool = False
    removals: int = 0

    def run(self) -> str:
        if self.exact_path != test_a.REMOTE or not self.target_identity_confirmed:
            return "RECOVERY_STOP_TARGET_OR_PATH_IDENTITY_UNKNOWN"
        if self.phase_r_result == "EXACT_PATH_ABSENT":
            return "PHASE_R_EXACT_PATH_ABSENT_NO_CLEANUP"
        if self.phase_r_result != "EXPECTED_REGULAR_FILE_PRESENT":
            return "RECOVERY_STOP_UNEXPECTED_OR_UNKNOWN_STATE"
        if (not self.current_process_safety_independently_reviewed
                or self.material_concern):
            return "PHASE_C_NO_GO"
        if not self.phase_c_separately_authorized:
            return "PHASE_C_AWAITING_SEPARATE_AUTHORIZATION"
        if not self.file_present:
            return "PHASE_C_NO_GO_STATE_CHANGED"
        self.removals += 1
        self.file_present = False
        return "PHASE_C_SIMULATED_EXACT_REMOVAL_AND_ABSENCE"
