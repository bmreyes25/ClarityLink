# Step 43A — Honda `/info` Type111 differential audit

**Date:** 2026-09-30
**Scope:** offline source-pinned xcertplay review and static Honda ELF evidence reconciliation. No vehicle/runtime testing, ADB, firmware change, jmcs modification, or Type111 implementation.

## Result

Verified xcertplay at commit `de9647f4bdfb1be356bed4cac0519400473712a6`. Its `/info` builder conditionally emits a cluster descriptor with `type=111` and a configured UUID distinct from the main `type=110` UUID; shared display-entry construction emits geometry, FPS, features, input-device, view-area, and safe-area fields, with `initialURL` conditional. The exact source locations and table are in [Honda `/info` differential](../research/carplay/honda-info-type111-differential.md).

Honda's matching jmcs ELF SHA-256 is `cbc7ba881648fb8ffdfcc4c1100a028345c37134a2ae3b9dff7d76572851c232`. The corrected Step 32 static path confirms the descriptor array reaches the phone-facing binary-plist `/info` response. Honda builds one descriptor by calling `ScreenCopyMain()` once. It inserts `edid`, `features`, `maxFPS`, pixel/physical dimensions, and numeric `uuid`; no second descriptor or role/type key was recovered in that builder.

### Honda field results

- `HONDA_CONFIRMED`: `uuid`, `maxFPS`, `widthPixels`, `heightPixels`, `widthPhysical`, `heightPhysical`, `features`, `edid`.
- `HONDA_INDIRECT_CANDIDATE`: descriptor `type`, because Honda uses literal `type` and numeric 110/111 stream dispatch elsewhere, but no display-role insertion was recovered in `/info`.
- `HONDA_ABSENT_LITERAL` within the inspected builder/exact-string scope: `primaryInputDevice`, `viewAreas`, `initialViewArea`, `initialURL`, `safeArea`.
- `HONDA_INDIRECT_CANDIDATE`: `forceKeyFrame`, because a matching literal and `AirPlayReceiverSessionForceKeyFrame` symbol exist but no second-screen association is recovered.
- UI control: `suggestUI`, `showUI`, `stopUI`, `SecondDisplayMode`, `ViewArea`, `ViewAreaChanged`, and modern feature-token literals are absent from the exact jmcs strings inspected. Generic platform/session control exists; semantics remain unknown.
- `HONDA_UNKNOWN`: whether any xcertplay field is required by Honda/iOS for Type111, the meaning and value provenance of Honda's numeric UUID/features, and any implicit/generated equivalents.

The bounded minimum second-display proposal is explicitly a `HYPOTHESIS`, not code or an implementation specification. Preserve the stock main descriptor; a candidate second entry would need distinct display identity and configured geometry, but no exact required Honda field set is established. A UUID is only presentation/capability identity by analogy with xcertplay; no UUID-to-streamConnectionID link is known.

Older topical notes [Honda server info](../research/carplay/honda-server-info.md) and [capability send path](../research/carplay/honda-display-capability-send-path.md) contained Step 31 conclusions later superseded by Step 32. Their current summaries have been corrected; the original Step 31 report remains historical and is superseded explicitly by Step 32.

## Verification

- Pinned xcertplay raw source inspected at the exact revision; field locations checked.
- Honda source notes reconciled with the exact hash-matched local ELF and exact string scan; no Honda executable run.
- Canonical offline suite via `PATH=/tmp/claritylink-docs-venv/bin:$PATH ./tools/run_tests.sh`: 224 passed, 4 skipped; self-locator smoke 3 passed; simulator JavaScript contract checks passed; configured git whitespace validation passed. The first invocation without the existing venv failed immediately because the system Python lacks pytest; no global package was installed.
- `git diff --check`: passed.

## Decision

```text
XCERTPLAY FIELD SET: COMPLETE
HONDA /INFO FIELD AUDIT: COMPLETE (literal/descriptor scope; indirect semantics remain open)
IMPLEMENTATION READY: NO
LIVE TEST READY: NO
JMCS INTEGRATION READY: NO
EXTERNALDISPLAY LIVE RENDER READY: NO
LD_PRELOAD: PARKED
```

**Next:** trace Honda `ScreenCopyMain()` properties and the existing display-array builder's string/CFDictionary references around `AirPlayReceiverSessionScreen_CopyDisplaysInfo` (`0x287ae0`) to determine whether another descriptor source or role field exists. Keep unknowns explicit.
