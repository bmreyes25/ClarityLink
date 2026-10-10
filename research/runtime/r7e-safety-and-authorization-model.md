# R7E safety and authorization model

**Scope:** planning only. R7E does not authorize or perform any Honda, vehicle, ADB, physical Android, iPhone, MFi, USB/iAP2, display, or CarPlay action.

## Evidence boundary

The controlling rules distinguish `MODEL_ONLY`, `DOCUMENTED_ANDROID`, `HONDA_STATIC`, `HONDA_READ_ONLY_OBSERVED`, and `HONDA_PROTOTYPE_OBSERVED`. R7D emulator measurements remain model/host evidence. Preserved Honda artifacts establish only what those artifacts show. No Honda behavior is promoted to PASS here.

R7D's `14.405 FPS` is retained as an emulator/software limitation against the requested 30 FPS. It is neither Honda performance evidence nor a blocker to a first one-frame compatibility check.

## Risk tiers and authorization

| Tier | Scope | Examples | Gate |
|---|---|---|---|
| 0 | Host/offline | Build, static audit, synthetic tests | R7E preparation |
| 1 | Honda read-only | Project-owned inventory diagnostics | Separate exact-plan authorization |
| 2 | Temporary process/file | Temporary executable acceptance | Separate Test A authorization |
| 3 | Display state | Presentation, Surface, one frame, warnings, teardown/performance | Each test separately authorized after its predecessor |
| 4 | Real session/auth | USB/iAP2/MFi/CarPlay | Blocked pending lawful authority and complete receiver/session/security evidence; separate review and authorization |

R7E2 adds `A0-R` as separately authorized Tier 1 read-only inventory and `A0-W` as separately authorized Tier 2 one-marker write/delete, only if A0-R requires it. Neither authorizes Test A. Test A execution is separately authorized Tier 2. `EXEC_PERMISSION_IS_TEST_A_MEASUREMENT`: successful executable mapping is the result, provided A0-R reveals no known mount/policy blocker. `SPECIFIC_SAFE_POWER_STATE_SUFFICIENT`: require a separately approved operator-observed state, stationary/parked vehicle, fully booted head unit, normal cluster/no warnings, unique target and immediate stop capability; proving a theoretical minimum is unnecessary.

R7E3 freezes A0-R in the host-side collector and hash-pinned manifest. The default is `NOT_AUTHORIZED`; the explicit runtime flag is a conscious local gate only and never represents user authorization. No collector path can enter A0-W or Test A.

An authorization applies only to the named test and exact artifact, commands, state, and rollback. Test A approval does not approve B–H. Enumeration does not approve Presentation admission. Admission does not approve rendering.

## Global stop and rollback boundary

Stop immediately on reboot/boot loop, frozen or unstable UI, warning disappearance/change, cluster corruption, center-display loss, unexpected audio loss, process persistence, unexpected privilege request, unplanned file mutation, failed cleanup, or any divergence from the authorized plan. Terminate only the planned project process, close its owned resources, remove only its verified temporary artifact, capture sanitized diagnostics, and verify normal center UI, cluster, warning, and audio behavior. Do not improvise or reboot unless a separate plan authorizes it.

Vehicle tests, if separately approved later, must be stationary, parked in a controlled location, never moving, with an operator able to terminate the test. Driver must not rely on test content. READY state is not presumed necessary.

## ECC review record

| Review area | Finding / risk | Correction or control | Verification |
|---|---|---|---|
| R7D→R7E evidence transition | Emulator behavior could be mistaken for Honda proof | Explicit evidence labels and unknown matrix retained | Cross-checked entry gate, unresolved matrix, R7D report |
| Command/write boundary | Artifact, destination, and runtime power state are not established | No exact vehicle command is asserted; unknowns block Test A | Per-plan write audit; no command executed |
| Privilege/temp files | Root and `/data/local/tmp` availability are unproven | Least privilege; destination marked evidence-required; no install/system writes | Dependency audit and Test A plan |
| Process/display lifecycle | Project-owned teardown does not prove factory restoration | Require counters, close, UI/cluster/warning/audio checks; restoration evidence bounded | Test F plan |
| Warnings/safe area | Warning layer, safe region, crop and z-order remain unknown | Do not render or infer safe geometry; benign warning candidate must be supported by later evidence | Test C–E plans and static evidence |
| Artifact defaults | No R7E diagnostic artifact was built; behavior cannot be validated | Full target artifact gate remains blocked | Build prerequisite absent; no artifact claimed |
| Performance | 14.405 FPS may be overinterpreted | Preserve as emulator-only; step rates only after earlier tests pass | Performance plan |
| Real CarPlay | No lawful MFi authority, complete session handoff, or production Type110/111 security/framing | Test H blocked; CPC200 not mandatory for A–G; no stock-jmcs handoff assumed | R6D/R6E and unresolved matrix |
| Test A circular prerequisite | Successful execution is the Test A objective | Exec permission is a measurement; preflight screens known blockers | `r7e2-prerequisite-circularity-review.md` |
| A0 separation | Read-only could be conflated with write or execute | A0-R Tier 1, A0-W Tier 2 conditional, Test A Tier 2 execution | A0 plans and matrix |

## Decision

This is preparation only. Every test remains `NOT_AUTHORIZED`. Because the target diagnostic artifact is unavailable, Test A is blocked and the R7E full-pass criteria are not met.

## R7E4 research-backed refinement (offline only)

The prior manifest SHA-256 `5b73badc219e87ef41eebb154ed4875c0c3ec2e3b19c61f2f2dc5209f3ff963e` is `SUPERSEDED_BEFORE_AUTHORIZATION`; no authorization was granted under it. The normalized manifest at [r7e3-a0r-plan-manifest.json](r7e3-a0r-plan-manifest.json) now carries plan version `R7E4-A0R-COMMAND-SET-1` and SHA-256 `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`. Its six added A0-R commands are fixed `ls -l` metadata reads for `/system/bin/toolbox`, `rm`, `ps`, `kill`, `md5`, and `chmod`; none executes those tools. Missing tool entries are recorded as `<TOOL>_UNAVAILABLE` and remain informational for A0-R; missing `rm`, `ps`, or `kill` also records a separate future-plan review blocker, while missing optional `md5` or unnecessary-by-default `chmod` does not block A0-R. `SELINUX_STATE_UNAVAILABLE` is informational and is never interpreted as disabled or permissive. `/data` `noexec` remains a hard blocker.

For future Test A, require host artifact mode `0755` before transfer, then verify the remote mode with `ls -l`; if the target executable bit is absent, stop without automatic `chmod`. SHA-256 remains the canonical identity; MD5 is optional transport consistency only. A0-W is proposed as one unique inert `0644` marker pushed through ADB sync, read-only inspected and optionally MD5-compared, then removed by exact path with a proven `rm`; it remains separately unauthorized and must not auto-run. See [R7E4 Android 4.2.2 research](r7e4-android42-target-path-research.md).
