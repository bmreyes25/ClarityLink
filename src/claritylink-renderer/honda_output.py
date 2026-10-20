"""Fail-closed Honda Display 1 boundary.

The lab renderer contract is implemented elsewhere. No authorized Honda API
for admitting arbitrary decoded frames has been established, so this adapter
cannot be enabled or turned into a live sink by caller-supplied metadata.
"""
from __future__ import annotations


class HondaDisplayEvidenceRequired(RuntimeError):
    """Raised when a missing Honda-owned display contract blocks an operation."""

    code = "EVIDENCE_REQUIRED_HONDA_DISPLAY_ADMISSION_API"
    missing_contract = (
        "authorized frame or View admission API",
        "owner/session identity and loss notification",
        "Navigation presentation eligibility and warning precedence",
        "factory Navigation safe-area coordinates and pixel format",
        "frame withdrawal and original-presentation restoration procedure",
    )

    def __init__(self, operation: str) -> None:
        self.operation = operation
        super().__init__(self.code)


class HondaDisplay1OutputAdapter:
    """Disabled adapter placeholder; it has no Honda service or device handle."""

    enabled = False

    def attach(self, *_: object, **__: object) -> None:
        raise HondaDisplayEvidenceRequired("attach")

    def submit(self, *_: object, **__: object) -> None:
        raise HondaDisplayEvidenceRequired("submit")

    def clear(self) -> None:
        # No Honda frame could have been admitted by this inert adapter.
        return None

    def close(self) -> None:
        # No Honda resource or presentation state is owned here.
        return None
