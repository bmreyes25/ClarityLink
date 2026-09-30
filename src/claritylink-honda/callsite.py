"""Build mock call-site patch descriptions from exact Thumb BL fingerprints."""

from dataclasses import dataclass

from mock_hooks import HookPatch
from thumb_call import ThumbEncodingError, decode_thumb_bl, encode_thumb_bl


@dataclass(frozen=True)
class StaticCallSite:
    name: str
    static_address: int
    expected_bytes: bytes
    stock_target: int

    def patch_for(self, runtime_address: int, redirect_target: int) -> HookPatch:
        """Validate recorded stock bytes/target and return a four-byte patch model."""
        try:
            static = decode_thumb_bl(self.static_address, self.expected_bytes)
        except ThumbEncodingError as exc:
            raise ValueError(f"{self.name}: invalid recorded Thumb call") from exc
        if static.target != self.stock_target:
            raise ValueError(f"{self.name}: stock call target does not match the fingerprint")
        try:
            decoded = decode_thumb_bl(runtime_address, self.expected_bytes)
        except ThumbEncodingError as exc:
            raise ValueError(f"{self.name}: invalid runtime callsite address") from exc
        # Relocation by load-bias affects both caller and callee equally.
        load_bias = runtime_address - self.static_address
        if load_bias < 0 or load_bias > 0xFFFF_FFFF:
            raise ValueError(f"{self.name}: invalid load bias")
        runtime_stock_target = self.stock_target + load_bias
        if not 0 <= runtime_stock_target <= 0xFFFF_FFFF:
            raise ValueError(f"{self.name}: runtime stock target overflows")
        if decoded.target != runtime_stock_target:
            raise ValueError(f"{self.name}: stock call target does not match the fingerprint")
        replacement = encode_thumb_bl(runtime_address, redirect_target)
        return HookPatch(self.name, runtime_address, self.expected_bytes, replacement)


HONDA_CALLSITES = (
    StaticCallSite("AirPlayCopyServerInfo", 0x28A158, bytes.fromhex("f8 f7 bc fd"), 0x282CD4),
    StaticCallSite("AirPlayReceiverSessionSetup", 0x28AF72, bytes.fromhex("fa f7 b5 fa"), 0x2854E0),
)
