# 43T1 RAM-only attachment/detach state machine — offline model

**Decision: `RAM_ATTACHMENT_MODEL_READY` for the synthetic state model only.** Source: `src/claritylink-honda/prep2_runtime.py`; tests in `tests/prep2/`. No target writer or Honda runtime attachment backend exists.

## Exact gates and compare-before-write

The model gates on the whole `jmcs` SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`, `ELF32/ARM/little-endian/EABI5/Thumb`, stock callsite bytes `fe f7 d1 ff`, BL target `0x289f60`, continuation `0x28afbe`, caller-context SHA-256 `edec335f1cd6f9d0d053a0d2b4a05f515c25e1a1524fccca2c4c0ebd610273df`, and prologue SHA-256 `be9f272a09201f326e42c27962609add81149bbe1adb9e843bb8b8ff685d7878`. Any mismatch aborts before simulated write.

Before attach the current bytes must equal the exact stock four bytes. Before detach they must equal the exact four-byte synthetic token `CLAB`, which is deliberately not an ARM instruction or vehicle patch. Any foreign or partial form aborts without restoration writes. The model injects writable-protection and read-only-restoration failures, records instruction-cache synchronization events, and never reports stock restoration when protection or byte verification fails.

States cover disabled, identity and callsite checks, preparation, attachment active/verified, bounded test, detach, restore compare, stock bytes restored, independent verification, reboot requirement, post-reboot verification, and abort/failure. A lease expiry requests bounded detach. Resource cleanup is ordered by project ownership: stop Type111 work, retire generation, close accepted FD, close listener, join worker, disable bridge. A failed step leaves its and later resources visibly active; stock is not claimed.

The model contains no ADB, ptrace, process-memory, debugger, APK, startup, system, data, block-device, or deployment backend. “RAM-only” remains a design invariant; actual Honda memory permissions, cache behavior, runtime mechanism, crash behavior, and reboot evidence are `HONDA_UNKNOWN`.
