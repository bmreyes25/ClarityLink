# Vehicle authorization boundaries — R7E7I-VP

## No authority in this milestone

This repository change authorizes no vehicle visit, Honda ADB, command, target write, target execution, cleanup, process enumeration, Phase S/C, Test A/B, APK install, window, display render, CarPlay session, or iPhone operation. A test marked plan-ready is only eligible for independent review. Earlier single-use authorizations are expired/consumed and never transfer to this plan.

Every future test needs its own new single-use user authorization naming the exact scope, date/session, current PR HEAD, artifact and manifest hashes where applicable, exact intended serial if ADB is involved, operator preconditions, command or observation list, evidence path policy, timeout, stop conditions, and explicit excluded actions. No test auto-advances to another test. Stop, preserve evidence, and obtain a new review after any anomaly.

## Inert V0 passive-observation authorization template

This is a template only. It grants no authority until the user sends a new message that fills every field and approves the reviewed scope. It allows observation and optional camera photographs/video only; no ADB, settings, session connection changes, warnings, test patterns, or device changes.

```text
CLARITYLINK R7E7I-VP — SINGLE-USE V0 PASSIVE BASELINE

I authorize one parked, passive visual baseline observation only.
Repository/PR/HEAD: [exact values]
Observation template SHA-256: [exact reviewed hash]
Date/session: [specific session]
Vehicle identity confirmation: [operator statement, stored privately]

I confirm the vehicle is stationary in a safe parked location, parking
brake is appropriate, ventilation is adequate if READY, center display
and cluster are normal, and no unexpected warnings are present. No driving
or operation while recording. I will not change settings or initiate,
disconnect, reconnect, or alter CarPlay. If no session is already active,
that condition will simply be recorded.

Scope: record only visible normal center-display/cluster state, navigation
page availability, and obvious displayed boundaries as measured or visually
estimated with uncertainty. Optional camera media will be minimal, unedited,
hash recorded, and stored privately. Do not photograph people, addresses,
or personal navigation details. No screen recording, ADB, diagnostic, write,
execution, warning induction, overlay, power cycle, or battery operation.

Stop immediately on any warning, abnormal display/cluster, movement,
distraction, privacy concern, or unexpected state. End after this one
baseline and review it before any other session. This does not authorize V1–V8.
```

## ADB observation authorization gate

V1, V2, V5 or any future ADB observation needs a separate authorization bound to the final frozen collector/manifest hashes and exact serial. Require stationary/safely parked vehicle; normal center and cluster; no unexpected warnings; known power state; existing stable connection; one command issuer; no manual concurrent ADB; private evidence storage; no command outside the exact manifest; and command-specific timeout and stop rules. Do not discover serials by issuing a new target scan outside the frozen procedure. ADB package identity is not permission.

V1 is currently blocked by clock attestation. V2 is blocked by unproven completeness/relaunch safety. V5 is deferred for shared-ADB review. V3 is a separate write authorization, unavailable until all cleanup gates pass. V4, V6/V7 and V8 require their own later decisions. No cleanup authorization can include Test A; no read-only authorization can imply writes.

## Vehicle operating constraints

Stationary and safely parked; appropriate parking brake; ventilation if READY; never drive while observing or operating controls; normal instrument visibility before and after; no deliberate warnings; no reboot or power cycling to prove termination; no 12V disconnection; no head-unit replacement/reflash; no root, `su`, ptrace, kill, broad sweep, or stock software modification; no shared/concurrent ADB; no retry/fallback; immediate stop on unexpected behavior; maintain an explicit restoration/stop plan for every future change. V0 requires no restoration because it makes no change.

## Evidence privacy and interpretation

Keep raw future vehicle media/evidence outside Git in a private directory, restrict permissions, record hashes and provenance, redact serials/PII in any review copy, and preserve failures unchanged. Separate measured values from estimates and operator reports. Photos do not prove compositor z-order or safe regions; `dumpsys display` does not prove window admission; Phase S does not prove current absence; pathname unlink does not terminate a process; host/emulator tests do not prove Honda behavior.

## ECC review provenance

This plan uses ECC safety-guard and security-review guidance and was manually checked for least scope, explicit authority boundaries, input/reference integrity, and fail-closed stop conditions. No independent ECC reviewer submission endpoint is available in this task context. Label this work **MANUAL_ECC_GUIDED_REVIEW**, not independent sign-off. A separate reviewer should assess the final commit before any future physical test request.
