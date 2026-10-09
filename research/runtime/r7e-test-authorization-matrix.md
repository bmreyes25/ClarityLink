# R7E test authorization matrix

All tests are `NOT_AUTHORIZED`. Plan readiness never authorizes execution.

| Test | Prerequisites | Risk | Honda read/write class | Required evidence | Rollback ready | Current readiness |
|---|---|---:|---|---|---|---|
| A0-R environment inventory | Frozen R7E3 collector/manifest; unique verified target; separate A0-R authorization | Tier 1 | Read-only inventory | UID/GID, path metadata, mounts, visible SELinux, operator-observed state | No target mutation; stop on anomalies | `READY_FOR_EXPLICIT_USER_A0R_AUTHORIZATION`; not authorized |
| A0-W temporary write/delete | Reviewed A0-R result showing destination exists, ordinary UID-2000 shell/platform, no known noexec blocker, and write/delete still unknown; exact marker plan; separate A0-W authorization | Tier 2 | One inert file create/read/delete; NO execution | Exact path, bytes, ownership/mode, deletion/absence | Exact marker only; no wildcard | `BLOCKED_BY_A0_R_RESULT` |
| A executable acceptance | A0-R reviewed; A0-W separately completed if needed; known mount/policy blockers screened; exact state, commands, rollback, and explicit Test A authorization | Tier 2 | Temporary file/process and execution | Artifact SHA/ABI/deps, bounded self-test; actual exec outcome measured by A | Not ready until exact remove/absence/process-disposition capability established | `BLOCKED_BY_A0` |
| B enumeration | Separately authorized A pass | Tier 1 | Read-only inventory | ID/type/dimensions/refresh/validity from target | Process stop and stock observation described | `BLOCKED_BY_PRIOR_TEST` |
| C Presentation | Separately authorized A and B pass | Tier 3 | Temporary display state | Separate context/show/Surface state diagnostics | Dismiss/release/stock checks described | `BLOCKED_BY_PRIOR_TEST` |
| D one frame | Separately authorized A/B/C pass; reviewed frame | Tier 3 | Temporary visible output | Human observation, timestamps, logs, resources | Clear/dismiss/release/stock checks described | `BLOCKED_BY_PRIOR_TEST` |
| E warning coexistence | Separately authorized A–D; evidence-backed benign condition | Tier 3 | Temporary display observation | Before/during/after warning visibility evidence | Stop/clear/restore checks described | `BLOCKED_BY_EVIDENCE` |
| F restoration | Exact preceding test and separate authorization | Tier 3 | Resource teardown; temporary-file removal | Process/resources/files absent; stock UI/cluster/warning/audio observations | Partial pending exact commands and target data | `PLAN_PARTIAL` |
| G performance | Separately authorized A–F passes | Tier 3 | Bounded target load | CPU/memory/drop/latency/UI/thermal observations | Described; exact staged bounds future | `BLOCKED_BY_PRIOR_TEST` |
| H real CarPlay/auth | Lawful authority, session ownership, real protocol/security and full safety evidence | Tier 4 | USB/iAP2/auth/network/session | Genuine MFi, real iPhone `/info`/SETUP, Type110/111 security/framing | Not established | `AUTHORITY_REQUIRED` |

## Command and write audit

R7E2 executed **zero** Honda/ADB/vehicle commands. A0-R approval does not approve A0-W or Test A; A0-W approval does not approve Test A. Every future command must appear in its individually reviewed plan with literal values and read/write/process/path/privilege audit. No wildcard cleanup, root, or ambiguous target selector.

R6D's no-supported-factory-session-handoff finding is retained; no plan assumes stock `jmcs` hands an authenticated session to ClarityLink. CPC200 is not a dependency for A–G.


## R7E1 status correction

All tests remain `NOT_AUTHORIZED`. A0-R is prepared for separate Tier 1 authorization. A0-W is conditional; Test A remains `BLOCKED_BY_A0`. `EXEC_PERMISSION_IS_TEST_A_MEASUREMENT`; `SPECIFIC_SAFE_POWER_STATE_SUFFICIENT`. B–D remain blocked by prior tests and Honda admission evidence. E remains evidence blocked; F partial; G keeps 14.405 FPS emulator `PERFORMANCE_UNRESOLVED`; H `AUTHORITY_REQUIRED`.

## R7E4 research-backed refinement (offline only)

The prior manifest SHA-256 `5b73badc219e87ef41eebb154ed4875c0c3ec2e3b19c61f2f2dc5209f3ff963e` is `SUPERSEDED_BEFORE_AUTHORIZATION`; no authorization was granted under it. The normalized manifest at [r7e3-a0r-plan-manifest.json](r7e3-a0r-plan-manifest.json) now carries plan version `R7E4-A0R-COMMAND-SET-1` and SHA-256 `962b25fca36dabde11f2406da1e5d898a0fe5c3a49f78f2bd00f292910442004`. Its six added A0-R commands are fixed `ls -l` metadata reads for `/system/bin/toolbox`, `rm`, `ps`, `kill`, `md5`, and `chmod`; none executes those tools. Missing tool entries are recorded as `<TOOL>_UNAVAILABLE` and remain informational for A0-R; missing `rm`, `ps`, or `kill` also records a separate future-plan review blocker, while missing optional `md5` or unnecessary-by-default `chmod` does not block A0-R. `SELINUX_STATE_UNAVAILABLE` is informational and is never interpreted as disabled or permissive. `/data` `noexec` remains a hard blocker.

For future Test A, require host artifact mode `0755` before transfer, then verify the remote mode with `ls -l`; if the target executable bit is absent, stop without automatic `chmod`. SHA-256 remains the canonical identity; MD5 is optional transport consistency only. A0-W is proposed as one unique inert `0644` marker pushed through ADB sync, read-only inspected and optionally MD5-compared, then removed by exact path with a proven `rm`; it remains separately unauthorized and must not auto-run. See [R7E4 Android 4.2.2 research](r7e4-android42-target-path-research.md).
