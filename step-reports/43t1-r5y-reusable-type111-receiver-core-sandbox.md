# 43T1-R5Y — reusable Type111 receiver-core sandbox

## Start and scope

- Starting branch: `main`; starting HEAD: `66cceab1bc7f2ce255f462d691324d340dc9d239`.
- Starting worktree: five modified current/safety/index files and six untracked R3 draft files. They were preserved and excluded from R5Y staging.
- Implementation HEAD: `a88d67960cb692c9058662b1757c73529133e80b` (pushed to `main`). Final HEAD is the later report-only commit containing this verification record; resolve it with `git log` because a commit cannot contain its own hash.
- Worktree at R5Y implementation commit: unrelated R3/R5C drafts and edits remained unstaged. R5C subsequently committed those independently as `07621b1c8c08a7e15c12037bd17427b6767c035c`; the worktree was clean before this report-only update.
- Honda contacted: **NO**. ADB used: **NO**. Runtime reads: **0**. Runtime writes: **0**. Vehicle connected: **NO**. APK installed: **NO**. `jmcs` modified: **NO**. `jmcs` used: **NO**. Type111 used on Honda: **NO**. HondaHack runtime used: **NO**.

## R5X baseline and R5Y objective

[R5X](43t1-r5x-theoretical-jmcs-type111-patch-sandbox.md) supplied a single-module, 16-test theoretical patch model. R5Y makes a reusable **MODEL_ONLY · HOST_ONLY · NOT_DEPLOYABLE · NOT_HONDA_BINARY · NOT_REAL_CARPLAY · NOT_MFI · NO_REAL_JMCS_PATCH** core with typed seams and repeatable host tests. The R5X module and tests remain intact for compatibility. R5Y does not build a Honda adapter, patch, receiver, auth, socket, decoder, Android window, or device tool. The purpose is to avoid rebuilding symbolic session/child ownership if future Honda-specific evidence ever arrives.

## Package architecture and stable API

The [package architecture](../research/runtime/r5y-sandbox-package-architecture.md) separates frozen values/serializer, symbolic adapter Protocols and mocks, orchestration/cleanup/faults, and pure replay. The [public API](../research/runtime/r5y-public-sandbox-api.md) includes `ReceiverSession`, `SessionGeneration`, Setup request/response/transaction, descriptors and stream state, `ListenerHandle`, `SecurityContext`, symbolic media/decoded/display frames, `CleanupResult`, `ResourceSnapshot`, `ReceiverError`, and `ReceiverCore`. No target-specific import is used.

The [state machine](../research/runtime/r5y-receiver-state-machine.md) defines ten `MODEL_ONLY_STATE` states and a tested legal-transition table. The [Setup engine](../research/runtime/r5y-setup-transaction-engine.md) snapshots a parent-owned Type110 model, requires explicit child enable, prepares model-owned resources, commits a frozen response or aborts/cleans the child. The [preservation oracle](../research/runtime/r5y-type110-preservation-oracle.md) checks object identity, descriptor identity, synthetic serialized primary response, session ID, lifecycle and parent teardown ownership across success and failure cases. This cannot prove stock Honda runtime coexistence.

## Symbolic components and ownership

The [future adapter contract](../research/runtime/r5y-future-adapter-contract.md) lists receiver entry, Setup request/response, identity, listener, security, decoder, display and lifecycle seams with input/output/ownership/failure/evidence requirements. `HondaReceiverAdapter` is only a documentation concept; no executable Honda adapter exists. Listener handles track a mock port label, accepted/closed state and exact generation, with no socket. The [security boundary](../research/runtime/r5y-security-provider-boundary.md) uses marker-only contexts, no keys/cipher/authentication. The media pipeline maps `frame-N` to `clear-frame-N` to `decoded-clear-frame-N` and a symbolic [display sink](../research/runtime/r5y-display-sink-contract.md), with ordered sequence and generation checks. There are no real media bytes or pixels.

The [cleanup manager](../research/runtime/r5y-resource-ownership-and-cleanup.md) registers each partial child immediately, then stops symbolic media, clears/closes display, closes decoder, destroys mock security, closes listener, removes child, and closes the generation. Cleanup is exact-generation and idempotent; stale teardown cannot touch a newer generation. `ResourceSnapshot` counts open model sessions, streams, listeners, security contexts, decoders, sinks and pending transactions; after complete teardown the secondary counts are zero.

## Faults, fixtures, reconnect, serializer and trace

`FailurePoint`/`FaultInjector` provide named one-shot faults at session creation, validation, response creation, listener/security/decoder/display setup, commit, first/midstream frame, decoder/display processing, teardown and duplicate teardown. Tests cover partial initialization, primary survival and resource counts. The 16 invented [R5Y fixtures](../tests/fixtures/r5y/normal_stream.json) include primary-only, secondary success/disable/failures, stale/future frames, duplicate teardown, reconnect and rapid reconnect. A 100-cycle host test checks no lingering secondary ownership after each generation; it is not a vehicle soak test.

The canonical `serialize_setup` output is tagged `SYNTHETIC_MODEL_SERIALIZER` and `NOT_CARPLAY_WIRE_FORMAT`. `ModelEvent` provides deterministic, sanitized trace entries. The [replay tool](../tools/r5y_replay.py) accepts only JSON fixtures under the R5Y fixture directory and returns final state, events, resource counts, primary-preservation result and cleanup results. The package replay function itself has no file I/O. The [scoped firewall](../tools/check_r5y_sandbox_boundary.py) checks sandbox imports/calls/path literals, symlinks and deployable-looking extensions; it is integrated into repository health. It is a static guard plus human review, not a proof against every dynamic bypass.

## Evidence, safety and decision

The [evidence gap registry](../research/runtime/r5y-honda-evidence-gap-registry.md) keeps every Honda-specific adapter dependency `UNKNOWN`. The [future integration playbook](../research/runtime/r5y-future-integration-playbook.md) starts with lawful artifact provenance, evidence classification and a host fake before any separate review. The [readiness matrix](../research/runtime/r5y-reusable-sandbox-readiness-matrix.md) uses `READY` strictly for the host model. The [proof boundary](../research/runtime/r5y-what-this-proves-and-does-not-prove.md) says what the tests establish and lists target unknowns. The [failure matrix](../docs/safety/runtime-failure-matrix.md) extends R5X controls for adapter overclaim, serializer confusion, host-cycle overclaim, firewall bypass, stale-generation destruction, partial leaks and primary corruption.

R5B, the newest artifact milestone, found no lawful analyzable descendant receiver payload. R3C still controls `jmcs`/Type111 runtime NO-GO. R4D Display 1 admission remains unproven. R5Y changes no Honda evidence level and authorizes no runtime or vehicle action.

## ECC findings and verification

Manual @ECC security-review and Python-testing guidance covered provenance, explicit enable, generation ownership, rollback, sanitized errors/events, mock-only data, staged scope, artifact extensions, reconnect and fail-clear. No independent ECC reviewer/service sign-off is claimed. No findings were suppressed.

- Focused R5Y tests: `.venv/bin/python -m pytest -q tests/sandbox/test_receiver_core.py tests/sandbox/test_r5y_replay_and_boundary.py` — **95 passed**; all sandbox tests including R5X — **111 passed**.
- Full suite: `PYTHON=.venv/bin/python ./tools/run_tests.sh` — **811 passed, 3 skipped**; 3 standard-library self-locator checks and configured simulator JavaScript checks passed.
- Repository health: `.venv/bin/python tools/check_repo_health.py` — passed with 0 curated broken links and 0 forbidden tracked extensions; 14 new R5Y documents/report were separately checked for relative links with 0 missing.
- Sandbox boundary check: `.venv/bin/python tools/check_r5y_sandbox_boundary.py` — passed.
- Fixture replay and resource-leak checks: all 16 fixture CLI replays passed; 100 sequential generations and every named setup/media fault path returned zero secondary counts after teardown.
- `git diff --check`: passed.
- Hosted [Offline CI](https://github.com/bmreyes25/ClarityLink/actions/runs/37220621374) on exact pushed implementation HEAD `a88d67960cb692c9058662b1757c73529133e80b`: **passed**.
- Hosted [CodeQL](https://github.com/bmreyes25/ClarityLink/actions/runs/37220621371) on that same implementation HEAD: **passed** across all five configured language/workflow jobs. The C/C++ job reported its existing full-database fallback annotation; it completed successfully. Neither result reuses an R5X/R5B run.
- Hosted verification of the final report-only HEAD: pending at the time this report was written; the exact result is recorded in the final task response.

## Decision and next milestone

**R5Y decision:** `R5Y_REUSABLE_RECEIVER_CORE_COMPLETE` for the host-only objective, with implementation commit hosted verification passed.

**Project recommendation:** `GO_FOR_R5B_HONDA_DESCENDANT_ARTIFACT_RESEARCH`, meaning continued lawful public artifact/provenance work under R5B's unresolved evidence gate, not a rerun of completed R5B triage or any vehicle action. If no lawful analyzable payload appears, keep Type111 runtime parked. No car experiment, ADB, APK, patch, real negotiation/listener, callback replacement, preload, HondaHack/Xposed, framebuffer, CAN or USB work is authorized.
