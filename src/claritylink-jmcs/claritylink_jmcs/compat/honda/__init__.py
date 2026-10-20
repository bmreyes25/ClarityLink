"""Static-evidence Honda field models; no binary ABI or vehicle adapter."""

from .setup import HondaStaticType110Adapter, EvidenceRequired
from .hondahack_boundary import HondaHackEvidenceGap, HondaHackFrameAdmissionGate

__all__ = [
    "HondaStaticType110Adapter",
    "EvidenceRequired",
    "HondaHackEvidenceGap",
    "HondaHackFrameAdmissionGate",
]
