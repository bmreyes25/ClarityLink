"""Evidence-backed candidate points and fingerprints from the exact jmcs ELF."""
from dataclasses import dataclass

JMCS_SHA256="cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232"
JMCS_TEXT_SHA256="ca4abfd2f2c1f5f7fe88b4b0bde9e920d22b454f2a699b7de1f4984c901278eb"
JMCS_FILE_SIZE=13_406_720
JMCS_ELF_CLASS=32
JMCS_ENDIAN="little"
JMCS_MACHINE=40
JMCS_TYPE=3
JMCS_BUILD_ID=None

@dataclass(frozen=True)
class HookFingerprint:
    name: str
    static_va: int
    isa: str
    expected_bytes: bytes
    role: str
    patch_site: bool
    def __post_init__(self):
        if self.isa not in ("Thumb","ARM"): raise ValueError("unsupported ISA fingerprint")
        alignment=2 if self.isa=="Thumb" else 4
        if self.static_va & (alignment-1): raise ValueError("misaligned static instruction address")
        if self.patch_site:
            if self.isa!="Thumb" or len(self.expected_bytes)!=4:
                raise ValueError("selected call-site candidates must be 32-bit Thumb instructions")
            first=int.from_bytes(self.expected_bytes[:2],"little")
            second=int.from_bytes(self.expected_bytes[2:],"little")
            if first&0xF800!=0xF000 or second&0xD000!=0xD000:
                raise ValueError("selected patch site is not a Thumb BL instruction")

CANDIDATE_FINGERPRINTS=(
    HookFingerprint("AirPlayCopyServerInfo call return window",0x28A158,"Thumb",bytes.fromhex("f8 f7 bc fd"),"phone-facing info result in r0",True),
    HookFingerprint("AirPlayReceiverSessionSetup call",0x28AF72,"Thumb",bytes.fromhex("fa f7 b5 fa"),"stock Setup call in _connectionHandleMessage",True),
)
FUNCTION_ENTRY_PROLOGUES=(
    HookFingerprint("AirPlayReceiverSessionSetup",0x2854E0,"Thumb",bytes.fromhex("2d e9 f0 4f 00 26 9e 4d c1 b0"),"entry; literal load in initial instruction window",False),
    HookFingerprint("AirPlayCopyServerInfo",0x282CD4,"Thumb",bytes.fromhex("2d e9 f0 4f ad f5 86 5d df f8 bc 67"),"entry; PC-relative literal loads",False),
    HookFingerprint("_connectionHandleMessage",0x28A30C,"Thumb",bytes.fromhex("df f8 8c 24 2d e9 f0 4f 04 46 df f8 88 04"),"entry; PC-relative literal load before frame setup",False),
    HookFingerprint("_requestSendPlistResponse",0x289F60,"Thumb",bytes.fromhex("f7 b5 1e 46 d0 f8 c8 50 14 46 05 f5 00 50"),"serializer entry; generic response path",False),
    HookFingerprint("AirPlayReceiverSessionTearDown",0x2852EC,"Thumb",bytes.fromhex("2d e9 f0 4f 04 46 6d 48 9a 46 8d b0"),"session teardown entry; PC-relative literal load",False),
    HookFingerprint("AirPlayReceiverSessionStart",0x286398,"Thumb",bytes.fromhex("2d e9 f0 4f cb b0 f8 4c 05 46 88 46"),"session start entry; PC-relative literal load",False),
    HookFingerprint("AirPlayReceiverSessionScreen_CopyDisplaysInfo",0x287AE0,"Thumb",bytes.fromhex("00 20 86 4a 86 4b 2d e9 f0 47"),"descriptor builder entry; literal loads before push",False),
    HookFingerprint("_requestProcessInfo",0x28A018,"Thumb",bytes.fromhex("2d e9 f0 4f 06 46 d0 f8 08 a0 91 b0 90 48"),"entry; literal load within initial patch window",False),
    HookFingerprint("AirPlayReceiverSessionScreen_Setup",0x287D5C,"Thumb",bytes.fromhex("0a 4b 13 b5 7b 44"),"entry begins PC-relative literal load and add",False),
    HookFingerprint("AirPlayReceiverSessionScreen_ProcessFrames",0x287D8C,"Thumb",bytes.fromhex("2d e9 f0 4f 2d ed 02 8b 93 46 86 4d"),"media-data path; not a Display-B control hook",False),
    HookFingerprint("AirPlayReceiverSessionScreen_StartSession",0x2883A8,"Thumb",bytes.fromhex("25 a3 d3 e9 00 23 2d e9 f0 41"),"entry begins ADR plus PC-relative LDRD",False),
)
