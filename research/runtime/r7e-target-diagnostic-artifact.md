# R7E target diagnostic artifact

**Status:** Superseded by R7E1. The offline artifact blocker is closed; Test A remains blocked on target-only evidence. See [R7E1 artifact architecture](r7e1-target-artifact-architecture.md), [manifest](r7e1-target-artifact-manifest.md), and [readiness decision](r7e1-test-a-readiness-decision.md).

## R7E1 update (2026-10-08)

The singular proposal has been replaced with split `TEST_A_NATIVE_DIAGNOSTIC` and `TEST_B_D_ANDROID_DIAGNOSTIC` artifacts. ARMv7/API17 CLI build, ELF/API17 import audit, static negative audit, offline mode checks, 100-cycle x86 API17 runtime, and separate emulator-only APK display checks passed. Build products remain ignored and are not committed. Target installation/execution is not authorized. The historical blocked status below records the original R7E state only.

## Intended contract

The proposed artifact is a minimal API17 / `armeabi-v7a` diagnostic for Tests A–F only. Required explicit modes: self-test, display enumeration, Presentation preflight, single-frame test, status, and shutdown. No-argument invocation must print usage/status and exit without persistence, rendering, listeners, authentication, MFi hardware, or CarPlay activity. It must not be a full receiver by default.

## Build and provenance

Required toolchain: Android NDK r23c 23.2.8568313, API17, ARMv7. `ANDROID_NDK_HOME` is unset in this environment; the R7B/R7C build scripts therefore cannot produce the required artifact. No existing R7B receiver library is substituted because it is not the requested fail-closed platform diagnostic, and its provenance does not establish the required modes/default behavior.

| Property | Result |
|---|---|
| Artifact path | None |
| SHA-256 | Not available |
| ELF/ABI/API | Not audited; required target is ELF32 ARM EABI5, `armeabi-v7a`, API17 |
| Imports / NEEDED | Not audited |
| Offline mode tests | Not run; no artifact |
| Static hooks/strings audit | Not run; no artifact |
| Honda execution | NONE |

## Required closure before Test A review

Build a project-owned diagnostic with fail-closed defaults, audit ELF/ABI/imports/dependencies/exports/test strings and emulator-only hooks, and run offline self-test, no-argument, invalid-mode, display enumeration, Presentation preflight, single-frame, shutdown, stale generation, and repeated start/stop checks. Record exact artifact hash and manifest. This remains offline work and does not authorize target execution.
