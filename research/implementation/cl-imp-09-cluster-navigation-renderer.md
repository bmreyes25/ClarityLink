# CL-IMP-09 — Cluster navigation renderer

## Implementation

- Extended the API17 hosted Content View to render the decoder's owned RGBA frame with its crop and quarter-turn rotation metadata. Aspect-fit sizing uses the active safe rectangle and rotates about its center.
- Added `RendererViewport`, an immutable, bounded, synthetic-only geometry contract. Its 800×480 logical canvas supports one safe rectangle and up to 32 protected rectangles. The allowed safe rectangle scales inward at fractional sizes while excluded protected rectangles scale outward; protected rectangles are subtracted from the Canvas clip. The type rejects any provenance other than `SYNTHETIC_TEST_ONLY`.
- Wired the viewport through `Display1OutputBackend` into the existing Presentation-hosted Content View. It reuses the existing decoder frame ownership, 4 MiB bound, generation checks, one-frame replacement, warning preemption, and borrowed Surface lifecycle.
- Added an emulator probe with a cropped, rotated, two-color synthetic frame. It checks the drawn pixel bounds, crop selection, safe-area clipping, protected-region exclusion, fractional-scale rounding, positive stale-generation rejection, warning clearing, and acceptance of a fresh frame after resume.
- Updated the API17 runner to require both renderer evidence markers in the normal and crash-recovery runs. The lab APK remains emulator-only; the disabled candidate remains disabled and production Honda integration remains false.

## Validation evidence

- `tools/compile_android_api17_java.sh`: passed against API17.
- `tools/build_cl_imp_03_apks.sh`: passed; lab APK SHA-256 `b8cbe434c053529f475f9a7be2a3122d1a8dc6bbd7a3a0c9b3c4d96704282e63`; disabled candidate SHA-256 `3b702a19adf6f58a3818813fcaa7e4f445dafbcf7b9f6ed6cae8d45c8f4d4599`.
- `tools/run_cl_imp_03_emulator.sh`: passed on the isolated Android 4.2.2/API17 x86 emulator, including Presentation drawing, synthetic geometry/clipping and fractional scaling, positive stale-generation rejection, warning preemption/resume, separate-process IPC, display removal, crash cleanup, and emulator-only package removal.
- Focused display contract tests: 8 passed. Full offline suite: 1,411 passed, 14 skipped. Repository health and `git diff --check` passed.

## Limits and follow-up

- Pixel inspection and Canvas drawing establish only behavior in this synthetic API17 laboratory view. They do not establish Android physical display scanout, Honda Display 1 admission, instrument-cluster dimensions, safe-area geometry, or warning arbitration.
- No real Type111 video, iPhone, Honda session, vehicle, or production host interface was used. The synthetic 800×480 geometry is not a vehicle profile.
- The renderer accepts decoded CPU RGBA frames. CL-IMP-10 still needs to connect the runtime pipeline with explicit ownership and fail-safe teardown; CL-IMP-11 will exercise the end-to-end dual-display lab demonstration.
