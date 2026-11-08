# CL-54B Native `/info` Prototype — Offline Checkpoint

Date: 2026-11-08
Task: `CL-54B-NATIVE-TYPE111`
Branch: `codex/cl-54b-native-type111`
Base: PR #152 head `15f3ea007902cdf28c10bc8eb26d1a64d543d421`

## Execution plan and state

- **Git/Studio:** The older CL-54B worktree remains clean at unpublished commit `a1c15a104a2b41f5d277ac38c790280f4939c7f0`. PR #152 is open at the task base; PR #151 is also open. This prototype uses its own registered Studio worktree and explicit scope. No vehicle, startup files, or archived receiver bytes were modified.
- **Publication blocker:** The existing publisher requires a task-owned commit based on the fetched PR #152 head. The older CL-54B commit is not eligible for publication from that task. The postflight hook reported that task postflight could not be read. Neither issue is bypassed here.
- **Baseline failures:** On the exact CL-54 parent, the protected Honda controller/source-lock/evidence family reproduced `56 failed, 129 passed`; the campaign runner collection also fails because its stored `collector.py` digest differs from the checked-in file. These are baseline source-lock failures, not evidence of a regression from this native prototype. No protected locks were changed.
- **Integration choice:** Continue toward a private modified copy of Honda `jmcs` (Option A), as it is the only identified route that can reach direct same-ELF calls without relying on unavailable preload interception. No safe patch site or receiver-integrated patch has yet been established. The current artifact is a callback-driven native component, not an ELF patch.
- **First three checkpoints:** (1) clone-on-augment native descriptor builder and conformance harness; (2) map the real Honda Control SETUP negotiation contract and only enable Type111 when ready; (3) add a separate Type111 dispatcher transaction with stock 100/101/110 passthrough and rollback.
- **Beta acceptance:** Reproducible API17/ARMv7 build, exact receiver provenance, verified native integration, Type110 regressions, two-display advertisement, real feature negotiation, independent authenticated Type111 lifecycle, safe Display 1 frame admission, teardown/failure tests, private artifact manifest, recovery and independent review. None of the vehicle readiness gates is established.
- **First code change:** Add an ABI-neutral C adapter that clones the display array, retains original entries, adds only a separately identified Type111 candidate, and leaves the Honda factory object untouched for fallback.

## Implementation and executable evidence

Added `src/claritylink-jmcs/native/info_augmentation.{c,h}`. It uses explicit CF/CFLite callback bindings, creates a separate array, preserves factory descriptor references, and adds a distinct candidate containing only `type=111` and a canonical lowercase UUID. Honda’s original numeric primary UUID and descriptor remain untouched. The UUID, field schema, and candidate are an external-prior-art experiment; Honda/iPhone acceptance is unproven. Geometry, safe areas, input configuration, and features are deliberately omitted rather than guessed.

The caller receives an owned augmented array and must serialize it; on any error it can retain and serialize the unchanged stock array. The production Honda `CFArrayAppendValue` wrapper is void-returning, so the adapter cannot detect or recover from a process-level allocation failure inside that call. The adapter requires callbacks that recognize only verified retaining-table identities. The Honda-specific identity binding is not implemented or validated. Host tests verify array retention of dictionary descriptors and use mutable CFData to verify dictionary child retention; CoreFoundation retain counts can be immortal for tagged values. The ARM callback model is synthetic.

Executed checks:

- Native harness suite: **3 passed, 0 skipped** with `CL_NATIVE_REQUIRE_TARGET=1`; host CoreFoundation binary-plist/ownership/failure harness, API17 ARMv7/Thumb object checks, and linked ARM execution under Unicorn with synthetic CF callbacks. The ARM ELF32 test returned success with no undefined symbols or dynamic relocations. This does not execute Android CFLite or Honda `jmcs`.
- Negotiation/type-dispatch regressions: **72 passed, 21 subtests passed**.
- `clang --analyze`: clean.
- AddressSanitizer + UndefinedBehaviorSanitizer host run: clean (`detect_leaks=0` because the host CoreFoundation runtime can retain process globals).
- `git diff --check`: clean.
- CMake/CTest: host CF target and explicit non-macOS skip are defined, but CMake is unavailable here. Required-mode pytest is the authoritative API17/ARM check; CTest alone does not exercise the ARM path.
- Full Honda source-lock suite: not rerun on this candidate; exact base reproduction remains 56 failed / 129 passed plus the separately observed collector hash collection failure.

Reproduction commands in the configured macOS/NDK environment:

```sh
ANDROID_NDK_HOME="/path/to/android-ndk-r23c" CL_NATIVE_REQUIRE_TARGET=1 python -m pytest -q tests/jmcs/native
python -m pytest -q tests/negotiation/test_thumb_setup_shim.py tests/native/test_native_setup_txn_host.py tests/negotiation/test_type111_setup_contract.py tests/negotiation/test_setup_contract.py tests/jmcs/test_stream_dispatch.py
clang --analyze -Wall -Wextra -Werror -std=c11 src/claritylink-jmcs/native/info_augmentation.c
ASAN_OPTIONS=detect_leaks=0 clang -fsanitize=address,undefined -g -Wall -Wextra -Werror -UNDEBUG -std=c11 tests/jmcs/native/test_info_augmentation.c src/claritylink-jmcs/native/info_augmentation.c -framework CoreFoundation -o /tmp/cl54b-native-asan
ASAN_OPTIONS=detect_leaks=0 /tmp/cl54b-native-asan
git diff --check
python3 tools/check_public_safety.py --staged
```

No Control SETUP acceptance, Type111 listener, authenticated transport, real iPhone negotiation, decoder handoff, or cluster rendering was executed. No successful Type111 SETUP is claimed.

## Control, security, native integration, recovery

Advertisement and Control SETUP remain separate gates. Evidence from prior Honda and external-project analyses distinguishes `/info` display descriptors, negotiated Control SETUP features, and per-stream Type111 SETUP. Honda’s actual capability agreement and persistence into stream dispatch are not yet established. Type111 remains disabled until both an evidenced negotiation contract and a ready authorized transport exist.

The intended receiver path remains stock 100/101 and 110, with a project-owned 111 handler only after establishing parent-session association, stream identity, receiver-owned protected transport, generation/replay handling, listener and decoder ownership, teardown, and rollback. Honda Type110 authentication is not evidence that its state can be reused for Type111.

A private modified receiver is the leading integration direction; ordinary preload cannot intercept the identified direct same-ELF calls. The real launch stanza, safe insertion site, exact patch, and ABI/Thumb preservation are unverified. A receiver replacement/fork is larger and riskier. No startup or vehicle recovery path is established. Independent recovery while the infotainment UI is unavailable remains a hard deployment gate.

## Review and next action

Read-only Claude and ECC `/code-review` approved the exact staged scope with no critical, high, or medium findings. The final ECC pass leaves six low comments: duplicate small pytest helper functions, the length/repeated cleanup in `create_candidate`, version-sensitive readelf checks, reliance on the documented input-immutability contract, limited direct retention-count observability for tagged CF values, and CTest not executing ARM. Those limits are recorded and do not alter the fail-closed result. Honda callback-table identity remains unbound and is an explicit integration prerequisite. This is a code review, not vehicle-safety certification.

The required-mode native and affected regression suites passed, analyzer/sanitizer checks were clean, and public-safety scan passed all eight scoped files. The repository task guard can read postflight and confirms exact scope; the desktop hook separately reported its postflight source unavailable. No bypass was used. Next: publish through the scoped publisher against PR #152, verify remote SHA and PR, then begin a separate Control SETUP evidence-to-code checkpoint without guessed Honda feature fields.

Classification supported by this checkpoint: **`CL54B_NATIVE_EXTENSION_APPROACH_IDENTIFIED`** (conditional Option A) and an **offline native ABI-shape prototype executed with synthetic callbacks**. It does not qualify as a Honda-native or in-car beta.
