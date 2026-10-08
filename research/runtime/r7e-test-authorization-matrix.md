# R7E test authorization matrix

All tests are `NOT_AUTHORIZED`. Plan readiness never authorizes execution.

| Test | Prerequisites | Risk | Honda read/write class | Required evidence | Rollback ready | Current readiness |
|---|---|---:|---|---|---|---|
| A executable acceptance | Diagnostic built/audited; destination and power state established; exact plan and explicit authorization | Tier 2 | Temporary file/process (`HONDA_TEMPORARY_WRITE` if transferred) | Artifact SHA/ABI/deps, bounded self-test, cleanup proof | Partial; exact commands/destination unknown | `BLOCKED_BY_EVIDENCE` |
| B enumeration | Separately authorized A pass | Tier 1 | Read-only inventory | ID/type/dimensions/refresh/validity from target | Process stop and stock observation described | `BLOCKED_BY_PRIOR_TEST` |
| C Presentation | Separately authorized A and B pass | Tier 3 | Temporary display state | Separate context/show/Surface state diagnostics | Dismiss/release/stock checks described | `BLOCKED_BY_PRIOR_TEST` |
| D one frame | Separately authorized A/B/C pass; reviewed frame | Tier 3 | Temporary visible output | Human observation, timestamps, logs, resources | Clear/dismiss/release/stock checks described | `BLOCKED_BY_PRIOR_TEST` |
| E warning coexistence | Separately authorized A–D; evidence-backed benign condition | Tier 3 | Temporary display observation | Before/during/after warning visibility evidence | Stop/clear/restore checks described | `BLOCKED_BY_EVIDENCE` |
| F restoration | Exact preceding test and separate authorization | Tier 3 | Resource teardown; temporary-file removal | Process/resources/files absent; stock UI/cluster/warning/audio observations | Partial pending exact commands and target data | `PLAN_PARTIAL` |
| G performance | Separately authorized A–F passes | Tier 3 | Bounded target load | CPU/memory/drop/latency/UI/thermal observations | Described; exact staged bounds future | `BLOCKED_BY_PRIOR_TEST` |
| H real CarPlay/auth | Lawful authority, session ownership, real protocol/security and full safety evidence | Tier 4 | USB/iAP2/auth/network/session | Genuine MFi, real iPhone `/info`/SETUP, Type110/111 security/framing | Not established | `AUTHORITY_REQUIRED` |

## Command and write audit

R7E executed **zero** Honda/ADB/vehicle commands. Every future command must appear in the individually reviewed test document with literal values and a per-command account of reads, writes, processes started/stopped, files created/modified/removed, display changes, listeners, and privilege. No exact target commands are prepared where artifact, destination, display ID, or environment values are unknown. No placeholders conceal writes. This makes A non-ready until the offline artifact and target-independent values exist.

R6D's no-supported-factory-session-handoff finding is retained; no plan assumes stock `jmcs` hands an authenticated session to ClarityLink. CPC200 is not a dependency for A–G.
