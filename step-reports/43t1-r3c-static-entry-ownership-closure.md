# 43T1-R3C expanded — static non-replacement entry/ownership closure

## Start state and boundaries

- Starting branch: `main`; starting HEAD and `origin/main`: `f28bc66fe623273ba2c1ebfa60b677d74e34ca52`.
- Final research/evidence HEAD: `1f939ce87e030ca9d217528ca8b5b93c68ae0658`. Worktree contained pre-existing modified `EVIDENCE_INDEX.md`, `NEXT_ACTION.md`, `PROJECT_STATE.md`, `docs/safety/runtime-failure-matrix.md`, and `step-reports/README.md`, plus six untracked R3 draft files. Those draft files remain uncommitted; task-owned hunks in shared state files were staged separately. No reset, restore, clean, or stash was used.
- Honda contacted: **NO**. ADB used: **NO**. Runtime reads: **0**. Runtime writes: **0**. Vehicle connected: **NO**. RAM attachment: **NO**. Live listener: **NO**. Type111 negotiation: **NO**.
- This expanded R3C addresses the additional targets in the work order. The narrower already-committed R3C session-addressability report at `375e3ce` remains historical rather than being silently overwritten.

## Evidence and candidate closure

The source set includes R2/R3A/R3B, the earlier R3C session/registration/identity notes, Honda static Setup/response/finalizer/Type110/stream and device-registry traces, decoded Binder/service sources/manifests, launch/dependency notes, and preserved ELF artifacts. Directly inspected 350 Honda `.so` files plus `jmcs` with `llvm-objdump` dynamic headers/symbols/relocations; focused disassembly of `libcarplay_proxy.so` confirms its callback copy, second-register rejection, trampoline calls, and unregister behavior. The key files and claims are indexed in the [extension matrix](../research/runtime/43t1-r3c-extension-path-matrix.md), [proxy audit](../research/runtime/43t1-r3c-libcarplay-proxy-interface-audit.md), [service audit](../research/runtime/43t1-r3c-honda-service-boundary-audit.md), [stream dispatch audit](../research/runtime/43t1-r3c-stream-dispatch-extension-audit.md), and [process map](../research/runtime/43t1-r3c-process-and-entry-map.md).

External sources checked: pinned xcertplay `17c92439413638dfd1d7f91d7e1c2e7358398762`, MHI2 `c2f811f1a5c84dae3a62f4cf9b4a9e65fc3f7b3c`, and AOSP Bionic `android-4.2_r1` `dlfcn.c`; see [comparators](../research/runtime/43t1-r3c-external-architecture-comparators.md). They remain `EXTERNAL_PRIOR_ART` or `AOSP_API17_DOCUMENTED`, not Honda proof.

Best internal **research lead** is Honda's `AirPlayReceiverSessionRef`, visible to Honda Setup and finalizer. It is not an executable extension candidate: no additive observer sees both, pointer generation is unknown, and project entry would require prohibited replacement/interposition. The real cross-module proxy PLT boundary is a singleton media callback registration, not Setup interception. Binder callbacks carry app/display state without native Setup payload or AirPlay session identity. Generic screen registration appends objects but stock advertisement selects index 0; unknown Type111 receives no Setup response and is skipped by recovered teardown. No existing optional loader path for a project module is evidenced. Rejected paths and risk ratings are in the matrix.

**Independent cleanup:** a future project must own candidate graph, listener, accepted socket, worker, generation, correlation, rollback, security, decoder, and lease. EOF/error/failure/worker exit/lease can bound project resources only after a real same-session entry exists. None does. Honda finalizer and unknown-Type111 teardown cannot own these resources; process termination alone does not prove vehicle restoration. Type110 remains Honda-owned; displacement by proxy/delegate replacement is unacceptable. The inline patch remains rejected under R2. Model-code gate: **`DO_NOT_BUILD_MODEL`**; no model added.

## Decision and next milestone

**R3C decision:** `R3C_NO_SAFE_RUNTIME_EXTENSION_PATH_FOUND`.

**Project recommendation:** `ABANDON_RUNTIME_INTERPOSITION_UNTIL_NEW_EVIDENCE`.

Next milestone: offline architecture pivot or acquisition of a new preserved Honda artifact establishing an additive pre-serializer entry with stable session identity and project-owned cleanup. No live-Honda GO decision follows. See the [ADR](../research/adr/43t1-r3c-entry-and-ownership-architecture.md).

## ECC review

Manual @ECC-guided review covered provenance, session identity/reuse, proxy and delegate ownership, actual dynamic caller/relocation proof, absent launch configuration, Binder identity mismatch, Type110 preservation, independent cleanup, lifecycle coverage, external prior-art boundaries, authorization wording, and chronology. Security findings are captured in the [failure matrix](../docs/safety/runtime-failure-matrix.md). **Manual @ECC-guided review completed; no independent ECC reviewer/service sign-off occurred.**

## Verification

- Focused tests: `.venv/bin/python -m py_compile tools/check_repo_health.py` passed; the milestone-aware repository-health check passed.
- Full `PYTHON=.venv/bin/python ./tools/run_tests.sh`: **674 passed, 3 skipped**; self-locator **3 passed**; configured simulator checks passed. Capture-backed scripts were skipped because private fixtures are not CI inputs.
- `.venv/bin/python tools/check_repo_health.py`: **passed**, 478 Markdown files, 118 indexed milestone/support reports, 0 curated broken links, 0 forbidden tracked extensions. `git diff --check`: **passed**.
- Hosted Offline CI: **passed** on exact pushed evidence HEAD `1f939ce` ([run 37174275022](https://github.com/bmreyes25/ClarityLink/actions/runs/37174275022)); its repository-health and offline-suite jobs passed.
- Hosted CodeQL: **passed** on exact pushed evidence HEAD `1f939ce` across C/C++, Python, Actions, JavaScript/TypeScript, and Java/Kotlin ([run 37174274999](https://github.com/bmreyes25/ClarityLink/actions/runs/37174274999)). No finding was suppressed for R3C.
