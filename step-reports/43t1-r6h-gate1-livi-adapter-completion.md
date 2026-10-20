# 43T1-R6H — LIVI control delegation and real Mac auth Gate 1

**Starting HEAD:** `25f4a34743997ee0bc19e8d9b3a8d6af87282dc2`. **Branch:** `architecture/r6h-livi-adapter-completion`.

## Outcome

The upstream source confirms the narrow ownership seam in `CpStack.attachSocket`, and ClarityLink now has a bounded private Unix socket server implementing the agreed protocol. An isolated LIVI patch adds a delegate interface, pre-stock dispatch interception, exactly-once serialization, and RTSP header/body bounds. The software sub-gate is complete: the isolated LIVI patch implements the Node client, authenticated-state emission, per-session app wiring and ClarityLink bridge/provider. CPC200 was not detected, so no authority or iPhone testing was possible. Gate 1 remains hardware-gated; do not advance to Gate 2.

- LIVI: `f-io/LIVI` commit `dcb78854c59ba621f4d327910dc275da386496b4`, GPL-3.0-or-later.
- Local CPC200-CCPA: absent from filtered USB inventory. No provisioning or authentication commands.
- Delegation: source patch plus dispatch oracle verified on host; no real runtime session occurred.
- ClarityLink socket-to-ReceiverSession /info and Type110 SETUP tests: passed with synthetic LIVI frames. Python full suite: 886 passed, 14 skipped. Provider 100-cycle lifecycle and 100 Unix socket reconnect cycles: passed (synthetic only). LIVI typecheck: passed; 20 delegate/Node bridge/parser tests passed. Full LIVI CpStack tests: unavailable because `livi_crypto.node` was absent after `--ignore-scripts` install and Cargo is not installed.
- Real auth, real iPhone, `/info`, SETUP, Type110/111: not reached.
- No Honda, ADB, vehicle, or restricted identity use.

## ECC review

Applied ECC security-review, API-design and Python-patterns guidance to same-UID socket ownership, private directory/socket permissions, strict frame schema and size limits, plist structure bounds, request/generation correlation, explicit synthetic-vs-real provider labels, secret stripping, error redaction, timeout/close handling, and single-response routing. Spec/code-quality review confirmed the Node/Python framing match, all-SETUP exclusive routing, single serializer/writer, fail-closed auth ordering, and socket cleanup. Full CpStack suite remains unavailable without Cargo/native crypto, so report this validation limit. License boundary documented; patch remains separate and upstream source was not vendored.

## Decisions

Delegation: `R6H_DELEGATE_IMPLEMENTED`. Bridge: `R6H_REAL_BRIDGE_IMPLEMENTED`. Hardware: `R6H_HARDWARE_ABSENT`. Authority: `R6H_AUTHORITY_NOT_TESTED`. Real iPhone: not reached; `BELOW_G1_T0`. Gate result: `GATE1_SOFTWARE_READY_HARDWARE_REQUIRED`. Next: `GO_FOR_GATE1_HARDWARE_AUTHORITY_BRINGUP`.
