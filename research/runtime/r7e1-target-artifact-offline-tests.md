# R7E1 offline artifact tests

- API17 Android 4.2.2 isolated x86 emulator: `R7E1_API17_X86_RUNTIME_PASS cycles=100 api=17 release=4.2.2 abi=x86`.
- Separate APK: `R7E1_API17_DISPLAY_APK_PASS default=no-output enumeration=pass presentation=emulator-only single-frame=one-shot`. Default launch emitted status-only and no enumeration/admission/frame event. Synthetic emulator display enumerated; Presentation preflight created/released a surface without posting a frame; one-frame mode posted one frame and cleared/released it. Emulator-only overlay display setting was deleted during teardown.
- Native modes/invalid modes/100 cycles run in the API17 emulator; each cycle reports `RESOURCE_COUNTS final=0`. ARMv7 itself is build-confirmed, not runtime-confirmed. The emulator is x86, and its runtime evidence is classified separately.
- Host C build with `-fsanitize=address,undefined` passed mode tests and 100 self-test cycles. TSan was not run: the implementation is single-threaded and creates no threads or shared state, so TSan adds no meaningful coverage.
- Canonical repository runner with neighboring project venv: 902 passed, 15 skipped; self-locator 3/3 passed; configured simulator checks passed. `git diff --check` passed at the tested source state.

No Honda, physical Android device, vehicle, iPhone, MFi, or live CarPlay execution occurred. These tests establish offline software behavior only.
