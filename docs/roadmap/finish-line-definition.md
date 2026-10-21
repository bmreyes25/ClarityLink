# CL-MASTER-01 finish-line definition

The project objective is a **demonstrated, measurable, reversible** 2018 Honda Clarity integration in which factory CarPlay remains normal on the center display while a genuine secondary Type111 navigation stream appears in the cluster Navigation area. This is the product target, not a statement that the target is feasible or authorized.

`safeForHonda()` remains `false`. No finish-line item is passed by inference, a synthetic model, a third-party receiver, or static analysis alone.

## Final acceptance contract

| ID | Required outcome | Evidence needed to mark PASS |
|---|---|---|
| F1 | One legitimate authenticated CarPlay session supports both streams. | Approved, versioned receiver contract and authorized observation showing session identity, independent stream identity, authentication ownership, and revocation. No bypass or Honda credentials. |
| F2 | Factory Type110 continues normal center-display UI, touch, audio, and navigation behavior. | Synchronized before/during/after evidence on the target; no regression under approved faults. |
| F3 | A genuine Type111 stream is accepted, configured, and delivered. | Authorized phone-to-receiver observation with Type111 SETUP, authoritative VideoConfig, and actual frames; lab fixtures do not count. |
| F4 | Type111 lifecycle and generation ownership are independent and correct. | Stream-specific stop/restart, stale-generation rejection, owner death, and reconnect evidence while Type110 stays active. |
| F5 | Frames reach the instrument-cluster Navigation area through a permitted, reviewed integration boundary. | Documented authorization and target evidence for the host-owned frame sink, caller, format, and lifecycle. Private Binder reachability or injection is not a supported contract. |
| F6 | Rendering respects Navigation-page selection and physical geometry. | Verified physical safe area, transform, page ownership, and behavior across page changes. |
| F7 | Factory instruments and warnings retain priority. | Reviewed warning-priority contract and approved evidence showing warning preemption without masking instruments. Do not deliberately induce unsafe warnings. |
| F8 | Disconnect, failure, app exit, process death, and reconnect do not leave stale or obstructive content. | Required failure matrix on the actual approved integration, with frame freshness and restoration receipts. |
| F9 | Factory behavior is restored reliably. | Repeatable host-owned withdrawal and restoration evidence with no persistent modification. |
| F10 | Performance and resource gates pass. | Predeclared frame-rate, latency, drop, CPU/memory, queue, thermal, and soak limits measured on the target path. |
| F11 | The integration has independent vehicle-safety review. | Recorded review by a qualified, independent reviewer covering hazards, warnings, rollback, test conditions, and stop criteria. AI review is not safety approval. |
| F12 | Rollback and verification are reproducible. | Versioned procedure, preconditions, bounded recovery steps, and successful authorized rollback receipt. |
| F13 | Public-safe development history is on GitHub. | Merged, reviewed public docs and source history; private evidence inventory and backup/recovery proof are separately retained without exposing confidential contents. |

## Non-equivalent evidence

These results are useful but cannot satisfy F1–F13 on their own: synthetic Type111 SETUP or video, a second Android display, HondaHack casting, an emulator lifecycle test, a separate receiver, a third-party report, static decompilation, or multiple network connections. Two independent receivers do not prove that one iPhone session can be shared.

## Current conclusion

As of 2026-10-21, CL-R4/R7 have API17 laboratory acceptance and PR #52 has a merged CL-R12-F smoke result, but the full CL-R12-F performance/reliability criteria remain partial. New CL-HH-06, CL-SYS-01A, CL-HH-07, CL-R13-A and CL-IF-01 reports remain on open PR branches pending review; none establishes supported Honda Type111 handoff or cluster frame admission. Technical and safety finish-line acceptance F1–F12 is **NOT PASSED**. F13 is the separate public documentation/publication requirement and remains **INCOMPLETE** until applicable reviewed history is merged and private evidence backup/recovery is verified. See [current status](../status/current.md), the [evidence ledger](../status/evidence-ledger.md), and [integration readiness](../status/integration-readiness.md).
