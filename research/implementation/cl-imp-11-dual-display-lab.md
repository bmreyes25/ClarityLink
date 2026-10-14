# CL-IMP-11 dual-display laboratory demonstration — 2026-10-13

## Result

The host laboratory run passes with two distinct, simultaneous synthetic H.264 streams. Type110 continues to render to the Display 0 simulator while Type111 is decoded by FFmpeg and passed through the existing ClarityLink synthetic safe-area renderer and Display 1 mock backend. The saved HTML opens the two distinct PNG outputs side by side. This is a model-only demonstration: it is not a factory CarPlay session, genuine iPhone authentication, Honda Display 1 admission, or physical scanout.

## Exercised behavior

- Separate Type110 and Type111 listeners and stream ownership within `DualDisplayRuntime`.
- Mock stock-first Type111 SETUP delegation; mock primary ownership remains active. No Honda interface is asserted.
- Real H.264 fixture decoding, separate frame content, and one-frame renderer retention.
- Warning preemption clears secondary renderer state, drops frames during the warning, then resumes after clearing.
- Malformed Type111 media withdraws only the secondary stream; Type110 keeps producing frames. A stale secondary snapshot is not written as post-failure live output.
- Session generation advances from 1 to 2 and listeners, workers, session resources, and mock delegation are closed/revoked.
- Output path checks reject symbolic-link traversal and replace only this demonstration's known artifacts; unrelated files are preserved.

## Validation

- Focused acceptance tests: 3 passed.
- Configured offline regression: 1,421 passed, 14 skipped; self-locator smoke and JavaScript simulator checks passed.
- API17 lab and disabled-candidate APK build: passed. Lab APK SHA-256 `b8cbe434c053529f475f9a7be2a3122d1a8dc6bbd7a3a0c9b3c4d96704282e63`; disabled candidate APK SHA-256 `3b702a19adf6f58a3818813fcaa7e4f445dafbcf7b9f6ed6cae8d45c8f4d4599`. These are existing CL-IMP-03 artifacts; CL-IMP-11 does not change Android code.
- API17 emulator execution: not run. The isolated launcher stopped before emulator creation because no Java runtime is installed (`Unable to locate a Java Runtime`).
- Repository health and `git diff --check`: passed after removing generated Python bytecode.
- ECC security checklist review: no blocking issue identified. Review covered bounded fixture/frame inputs, FFmpeg invocation without a shell and with a timeout, strict decoded output size, symlink-safe artifact cleanup, synthetic-only session and renderer boundaries, and cleanup on primary/secondary runtime paths. This was an in-session checklist review, not an independent reviewer attestation.

## Laboratory artifacts

Generated under ignored `build/cl-imp-11/` and not committed as source: `index.html`, `report.json`, and generation-specific PNGs. SHA-256 values:
- `display0-type110-gen1-initial.png`: `232a7860d319238734397f803a8d485b94c063cd5e61fdf2db9050fed8262e04`
- `display0-type110-gen1-postfault.png`: `232a7860d319238734397f803a8d485b94c063cd5e61fdf2db9050fed8262e04`
- `display0-type110-gen2-initial.png`: `232a7860d319238734397f803a8d485b94c063cd5e61fdf2db9050fed8262e04`
- `display1-type111-gen1-initial.png`: `ddb652c70c527a535dd3584652e1d0724076de45e79e829dba8e152bfed0aa99`
- `display1-type111-gen1-resumed.png`: `ddb652c70c527a535dd3584652e1d0724076de45e79e829dba8e152bfed0aa99`
- `display1-type111-gen2-initial.png`: `ddb652c70c527a535dd3584652e1d0724076de45e79e829dba8e152bfed0aa99`
- `index.html`: `00f602d0b80b9ae96237cee851f6b775301f71d1debae24fd19a147cd4023f9e`
- `report.json`: `5361d41d1b69c0e023bba8ee61e96aebc10c427ce1590c49e178814b3e310e5a`

## External compatibility boundaries

Honda production integration remains disabled. No Honda operation, stock-process modification, installation, or live-iPhone session occurred. Authentic Type111 authentication, real Honda stock-session delegation, Honda cluster admission and geometry, warning arbitration, and physical scanout remain unproven.
