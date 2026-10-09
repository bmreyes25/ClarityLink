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
