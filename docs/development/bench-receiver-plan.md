# CL-REC-01 — independent Type111 bench plan

## Purpose and evidence boundary

Determine whether a separately controlled Android receiver can negotiate and render an authentic secondary stream in one legitimate CarPlay session. A successful result demonstrates only that receiver, phone/software version, identity, and test setup; it does not establish Honda receiver or cluster behavior.

## Prerequisites

- Separate written approval for the exact live-iPhone bench session.
- Legally obtained, explicitly authorized authentication hardware/identity; no Honda credentials, key extraction, bypass, or remote unauthorized signing service.
- Source-pinned receiver version, license review, controlled network, data-retention plan, and diagnostic allowlist.
- A normal Type110 output and a separate Type111 view with independent stream ownership.

## Acceptance

Record source/device/iOS versions to the approved privacy level; one authenticated session; Type110 and Type111 requests; distinct connection identity; accepted VideoConfig; actual video frames on both outputs; Type111-only stop and restart while Type110 remains active; clean disconnect and resource teardown; and sanitized logs reviewed against the allowlist. Codec, security mode, and lifecycle are unknown until directly observed. Do not infer omitted fields.

If a separate authorization is not granted or legitimate authentication is unavailable, keep this campaign blocked and do no live iPhone work.
