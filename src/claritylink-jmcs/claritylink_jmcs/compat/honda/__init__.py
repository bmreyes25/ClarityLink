"""Static-evidence Honda field models; no binary ABI or vehicle adapter."""

from .setup import HondaStaticType110Adapter, EvidenceRequired
from .display_boundary import DisplayEvidenceGap, HondaDisplayBoundaryGate

__all__ = [
    "HondaStaticType110Adapter",
    "EvidenceRequired",
    "DisplayEvidenceGap",
    "HondaDisplayBoundaryGate",
]
