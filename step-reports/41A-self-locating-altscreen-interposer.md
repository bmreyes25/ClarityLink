# Step 41A — self-locating AltScreen interposer

**Status: DESIGN ADVANCED; exact API17 linker proof and Honda load seam remain open. Offline only.** Repository base `28b9bd4`. No ADB, vehicle, `su`, ptrace, process memory API, executable firmware, patch, injection, key persistence, or Type111 enablement.

## Decision

External privileged `/proc/<jmcs>/maps` is **OBSOLETE AS PREREQUISITE** to an architecture that is already loaded in jmcs: the process can in principle resolve its own mappings through a supported dynamic-linker API or `/proc/self/maps`. Exact Android 4.2 ARM `dladdr` availability has not been independently pinned in this pass, so self-location is **CONDITIONAL**, not deployment-ready. The load seam is a separate and currently unproven issue.

Honda exact target evidence identifies `jmcs` as ARM32 little-endian EABI5 `ET_DYN`, API 17, SHA-256 `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`; `libcarplay_proxy.so` SHA-256 `dc8bc5c19cf32a8e7edcc14c1d80e78bb96ca6ccc434229349c74590136bef66`. Existing static analysis establishes one main display descriptor, `/info` as phone-facing, Type110 setup/response and security flow, Type111 unhandled dispatch, and local/internal callsite boundaries. Historical process bases are not used.

## Research and implementation

Added dependency, ELF, linker, self-location, load-seam, Apple capability-generation, Honda `/info`, Type111, correlation, hook-plan, and MHI2 lessons notes under `research/runtime/` and `research/carplay/`. Added host-only `src/claritylink-hook/self_locator.py` plus synthetic cases under `tests/hook/`. The parser has byte/entry caps, exact pathname matching, mapping-offset selection, executable permission checks, malformed-line rejection, and overflow checks. The validator reports exact hash/prologue/mode/mapping outcomes and fails closed. It does not parse real ELF files, read procfs, inspect target memory, change permissions, or install hooks.

Apple WWDC19 documents multiple H.264 instrument-cluster streams in iOS 13 and R15 vehicle-system support; WWDC23 expands ViewArea/SafeArea concepts. Honda is not proven R15-capable. Honda's old `/info` `displays[]` and numeric `features` are distinct from modern Setup `FeatureKey` tokens. No modern `altScreen` token is recommended without Honda/iPhone-generation proof.

Public MHI2 material supports stock-first response augmentation, secondary-only ownership, exact-target guardrails, and isolated listener lifecycle as architectural lessons. These are prior-art claims, not Honda evidence. Git repository commit/date provenance was not pinned for every requested repository; avoid treating mutable `main` pages as immutable citations.

## Decision gate

```text
HONDA JMCS ELF TYPE: ARM32 little-endian EABI5 ET_DYN (PIE-style)
JMCS LOAD BIAS STATICALLY MODELABLE: YES
ANDROID 4.2 ARM DLADDR: UNKNOWN (not verified against android-4.2_r1 tagged ARM exports)
ANDROID 4.2 ARM DL_ITERATE_PHDR: UNKNOWN (do not depend on it)
JMCS CAN SELF-LOCATE: CONDITIONAL
CARPLAY MODULE CAN SELF-LOCATE: CONDITIONAL
/PROC/SELF/MAPS FALLBACK: VIABLE (design-level; target access untested)
EXTERNAL /PROC/<JMCS>/MAPS REQUIRED: NO
LIBCARPLAY_PROXY NATURAL SEAM: PARTIAL (linked callback boundary; no loader/plugin API proven)
BEST LOAD SEAM: NO SUITABLE LOAD SEAM PROVEN
LOAD SEAM PROVEN: NO
HONDA SETUP INTERPOSABLE: PROLOGUE/call-site favored; symbol path unproven
HONDA CAPABILITY BUILDER INTERPOSABLE: PROLOGUE/call-site favored; symbol path unproven
HONDA CARPLAY GENERATION: UNKNOWN (legacy /info confirmed; R15 support not)
HONDA /INFO DISPLAY ARRAY: YES
SECOND DISPLAY STRUCTURALLY REPRESENTABLE: UNKNOWN (array shape yes; Honda builder emits one)
MODERN ALTSCREEN TOKEN REQUIRED: UNKNOWN
TYPE111 REQUEST PATH STATICALLY UNDERSTOOD: PARTIAL
TYPE111 RESPONSE SHAPE STATICALLY UNDERSTOOD: PARTIAL
DISPLAY-STREAM CORRELATION: UNKNOWN
STOCK PRIMARY CAN REMAIN UNTOUCHED: YES by proposed separation; unproven in execution
STEP 40F: OBSOLETE AS PREREQUISITE
SELF-LOCATING INTERPOSER MODEL: NOT READY (API17 locator and load seam not proven)
NEGOTIATION-ONLY IMPLEMENTATION: NOT READY
LIVE VEHICLE TEST: NOT READY
TYPE111: DISABLED
BIGGEST BLOCKER: no Honda-supported mechanism is proven to load ClarityLink inside jmcs
NEXT ACTION: pin android-4.2_r1 ARM libdl exports and inspect archived Honda libdl/linker symbols, then resume static search for a stock jmcs load seam
```

## Future first experiment

Do not run in this milestone. A later separately approved parked negotiation experiment should leave Type110 stock, augment only after exact compatibility checks, observe whether iPhone requests Type111, return a bounded listener port only when schema/security/correlation are proven, and stop on any validation failure. No cluster rendering or CAN writes.

## Validation

Synthetic hook tests and existing Honda runtime safety tests are run for this report. `git diff --check` is required. This implementation is a host model only and does not confer live-hook or deployment readiness.
