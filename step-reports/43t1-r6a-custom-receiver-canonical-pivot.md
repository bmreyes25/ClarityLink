# 43T1-R6A — custom receiver canonical pivot

Date: 2026-10-04. Starting main: `a0b8037fe5a4ded25bdbe0bbcc0d01c419dce64b` (R5D through PR #3). R5Z source: `08a17ee520963720b5ed4ba5f286882c2a9c3edf` / implementation `5d3bd6d`. Branch/worktree: `architecture/r6-custom-receiver` / `../clarity-r6-custom-receiver`.

## Integration and final native decision

R6 was created from clean main, then R5Z merged with an explicit merge commit (`b63b9a7`), retaining both histories. `step-reports/README.md` combined R5D and R5Z entries. `tools/step43t0d0_collector.py` kept main's newer linked-worktree/packed-ref fallback. CI and CodeQL push triggers changed from R5Z's experimental branch to the R6 branch, while PR-to-main behavior remains. Canonical state kept R5D until the explicit R6 update; R5D research was not overwritten.

The [bounded Honda substrate audit](../research/runtime/r6a-honda-receiver-substrate-audit.md) finds no complete same-session additive Type111 path covering Setup request, pre-serialization response, stock Type110, listener, security, media and teardown ownership. Native decision: **R6A_NATIVE_ADDITIVE_PATH_NOT_FOUND**. The sole public MELCO `MRC_EU_SW_v12_4.zip` / `1.F197.70` check found no original publisher package/hash/manifest; R5D provenance remains metadata. No further generic firmware hunt is recommended. USB, iAP2, MFi, audio, controls, Display0, Display1 and lifecycle findings are in the audit and [reuse matrix](../research/runtime/r6a-receiver-reuse-replace-matrix.md).

## Architecture and receiver promotion

Architecture decision: **R6A_CUSTOM_RECEIVER_PRIMARY** ([ADR](../research/adr/r6-custom-receiver-primary-architecture.md)). R3C stock interposition stays parked. R5Z source is maintained as the host reference with original experimental limitations retained ([promotion audit](../research/runtime/r6a-r5z-code-promotion-audit.md)). Implementation decision: **R6A_RECEIVER_PARTIAL**. The desired one-session Type110+Type111 architecture is modeled but not yet authenticated or iPhone-connected. Honda execution is not authorized.

`/info`: R6 adds prior-art display dictionaries, view/safe area, physical dimensions, UUIDs, Type111 initialURL and modes; full identity/audio/HID is incomplete ([field ledger](../research/runtime/r6a-type111-info-negotiation.md)). Type110 Setup and response: synthetic host transaction and known Honda static entry shape. Type111 Setup and response: synthetic host transaction with both ordering cases and distinct IDs/ports; no real iPhone acceptance. Secondary listener: localhost tested. Security: explicit profiles and generated-key ChaCha AEAD; no lawful session key handoff or real Type111 vector ([closure](../research/runtime/r6a-type111-security-closure.md)). Framing: explicit Type110 and PlayPort-derived current-iOS host profile; legacy Type111 remains fail-closed ([ledger](../research/runtime/r6a-type111-screenstream-framing.md)). Decoder: generated Annex-B FFmpeg path, bounded AVCC conversion and SPS/PPS extraction; real current-iOS VideoConfig unknown. Host window: Tk renderer implemented but not verified with a real phone or visible GUI in CI. Teardown/reconnect: synthetic independent cleanup, stale generation and 100 cycles. A torn-down secondary response reference and duplicate Type110 request were fixed.

Real iPhone SETUP, listener connection, encrypted Type111, H264 frame and host display **not observed on this receiver**. Highest continuously successful integration tier: **T1 generated clear media**. Highest R6 level: **R6_L1**. R6-L2 requires full /info and authenticated Setup. The immediate target remains R6-L7, with authentication and current-iOS media evidence as gates. [Readiness matrix](../research/runtime/r6a-custom-receiver-readiness.md) lists every subsystem.

## Port and platform strategy

Python remains the host reference; [language ADR](../research/adr/r6-receiver-language-and-portability.md) selects a future native C/C++ API17/ARMv7 implementation with shared sanitized fixtures. [Port plan](../research/runtime/r6a-api17-armv7-port-plan.md) is offline only; no native receiver build or Honda adapter was implemented. [Authentication](../research/runtime/r6a-authentication-strategy.md), [audio/control](../research/runtime/r6a-audio-control-strategy.md) and [replacement contract](../research/runtime/r6a-jmcs-replacement-contract.md) identify target blockers. No Honda adapter is claimed usable.

## Verification and next decision

Focused promotion tests: 11 passed. R5Z regression and full offline suite: 845 passed, 14 skipped; self-locator and JS checks passed. The 100-cycle test is included. Repository health and whitespace checks were rerun after this report. Offline CI and CodeQL on final HEAD are pending push/host completion; their prior R5Z checks do not count for R6. No private capture, firmware, VIN, MAC, key, certificate or restricted material was added.

Decision tuple: **R6A_NATIVE_ADDITIVE_PATH_NOT_FOUND / R6A_CUSTOM_RECEIVER_PRIMARY / R6A_RECEIVER_PARTIAL / R6_L1**. Exactly one next recommendation: **GO_FOR_R6B_AUTHENTICATION_SUBSTRATE**. This is the prerequisite to a lawful real-iPhone Setup attempt; then finish full /info and current-iOS security/framing against the same session. Do not default to firmware research. No Honda was contacted, no ADB was used, no vehicle was connected, and no receiver was run on Honda.
