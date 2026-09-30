"""Non-proprietary exact fingerprints for the archived Honda build."""
from self_locator import TargetDescriptor

FIRMWARE_ID = "MY16ADA 1.F1A2.45"
JMCS_SHA256 = "cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232"
JMCS_PATH = "/system/bin/jmcs"

# These are internal Thumb callsites, not approved live patch plans.
INFO_CALLSITE = TargetDescriptor(JMCS_PATH, JMCS_SHA256, 0x28A158,
                                 bytes.fromhex("f8 f7 bc fd"), "thumb", 4)
SETUP_CALLSITE = TargetDescriptor(JMCS_PATH, JMCS_SHA256, 0x28AF72,
                                  bytes.fromhex("fa f7 b5 fa"), "thumb", 4)
